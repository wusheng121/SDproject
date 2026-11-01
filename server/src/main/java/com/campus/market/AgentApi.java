package com.campus.market;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
public class AgentApi {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private final JdbcTemplate jdbc;
    private final MarketStore store;
    private final CampusProperties properties;
    private final RestClient dataClient;

    public AgentApi(JdbcTemplate jdbc, MarketStore store, CampusProperties properties) {
        this.jdbc = jdbc;
        this.store = store;
        this.properties = properties;
        String root = properties.getDataUrl();
        if (root.endsWith("/")) {
            root = root.substring(0, root.length() - 1);
        }
        this.dataClient = RestClient.builder().baseUrl(root).build();
    }

    @GetMapping("/api/v1/agent/products")
    public Map<String, Object> products(HttpServletRequest request, @RequestParam(defaultValue = "1") int page, @RequestParam(name = "page_size", defaultValue = "20") int pageSize) {
        Map<String, Object> agent = requireKey(request, "product:view");
        page = Math.max(page, 1);
        pageSize = Math.min(Math.max(pageSize, 1), 100);
        List<Map<String, Object>> items = store.listProducts(null, null, null, null, null, "new", page, pageSize).stream()
                .map(row -> store.productView(row, false)).toList();
        audit(agent, "agent.products.query", "product", null);
        return paged(items, page, pageSize, store.countProducts(null, null, null, null, null));
    }

    @GetMapping("/api/v1/agent/recommendations")
    public Map<String, Object> recommendations(HttpServletRequest request, @RequestParam(name = "user_id", required = false) Long userId, @RequestParam(defaultValue = "6") int limit) {
        Map<String, Object> agent = requireKey(request, "recommendation:query");
        long target = userId == null ? MarketStore.num(agent.get("id")) : userId;
        audit(agent, "agent.recommendations.query", "recommendation", String.valueOf(target));
        return Map.of("data", recommend(target, limit));
    }

    @PostMapping("/api/v1/agent/skills")
    public ResponseEntity<Map<String, Object>> skill(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        String skill = MarketStore.str(body.get("skill"));
        Map<String, Object> params = body.get("params") instanceof Map<?, ?> raw ? stringMap(raw) : Map.of();
        String scope = "recommendation_query".equals(skill) ? "recommendation:query" : "product:view";
        Map<String, Object> agent = requireKey(request, scope);
        Map<String, Object> data = switch (skill) {
            case "product_query", "nl_filter" -> Map.of("skill", skill, "items", filterProducts(skill, params));
            case "recommendation_query" -> {
                Long userId = params.get("user_id") == null ? null : MarketStore.num(params.get("user_id"));
                int limit = params.get("limit") == null ? 6 : (int) MarketStore.num(params.get("limit"));
                long target = userId == null ? MarketStore.num(agent.get("id")) : userId;
                yield recommend(target, limit);
            }
            case "product_recognize" -> recognizeImage(params);
            default -> throw new ApiException("VALIDATION_ERROR", "未知的 skill", 422);
        };
        audit(agent, "agent.skill." + skill, "skill", skill);
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("code", 0);
        response.put("message", "ok");
        response.put("data", data);
        return ResponseEntity.ok(response);
    }

    private Map<String, Object> recognizeImage(Map<String, Object> params) {
        String image = MarketStore.str(params.get("image_base64"));
        if (image.isBlank()) {
            throw new ApiException("VALIDATION_ERROR", "请在 params.image_base64 提供图片", 422);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("image_base64", image);
        body.put("mime", params.get("mime") == null ? "image/jpeg" : String.valueOf(params.get("mime")));
        try {
            Map<?, ?> response = dataClient.post()
                    .uri("/api/ai/recognize-query")
                    .body(body)
                    .retrieve()
                    .body(Map.class);
            Object data = response == null ? null : response.get("data");
            Map<String, Object> result = data instanceof Map<?, ?> map ? stringMap(map) : new LinkedHashMap<>();
            result.put("skill", "product_recognize");
            result.put("read_only", true);
            return result;
        } catch (ApiException exc) {
            throw exc;
        } catch (Exception exc) {
            throw new ApiException("DATA_UNAVAILABLE", "识图服务暂时不可用", 503);
        }
    }

    private Map<String, Object> recommend(long userId, int limit) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("user_id", userId);
        body.put("limit", limit);
        Map<?, ?> response = dataClient.post()
                .uri("/api/recommendations/internal")
                .header("X-Internal-Token", properties.getJwtSecret())
                .body(body)
                .retrieve()
                .body(Map.class);
        Object data = response == null ? null : response.get("data");
        if (data instanceof Map<?, ?> map) {
            return stringMap(map);
        }
        return Map.of("items", List.of(), "strategy", "D", "strategy_name", "ALS矩阵分解 + 内容推荐");
    }

    private List<Map<String, Object>> filterProducts(String skill, Map<String, Object> params) {
        String text = MarketStore.str(params.get("text"));
        String category = MarketStore.str(params.get("category"));
        String condition = MarketStore.str(params.get("condition"));
        if ("nl_filter".equals(skill) && !text.isBlank()) {
            if (category.isBlank()) {
                category = firstContained(text, store.allCategories());
            }
            if (condition.isBlank()) {
                condition = firstContained(text, List.of("全新", "九五新", "九成新", "八成新", "七成新"));
            }
        }
        Double maxPrice = number(params.get("max_price"));
        if (maxPrice == null && text.contains("以内")) {
            maxPrice = leadingNumber(text);
        }
        List<Map<String, Object>> items = new ArrayList<>();
        for (Map<String, Object> row : store.listProducts(category, null, condition, number(params.get("min_price")), maxPrice, "new", 1, 20)) {
            items.add(store.productView(row, false));
        }
        return items;
    }

    private Map<String, Object> requireKey(HttpServletRequest request, String scope) {
        String raw = request.getHeader("X-API-Key");
        if (raw == null || !raw.startsWith("cmk_") || !raw.contains(".")) {
            throw new ApiException("AUTH_INVALID_API_KEY", "API Key 无效或权限不足", 401);
        }
        String prefix = raw.substring(0, raw.indexOf('.'));
        List<Map<String, Object>> keys = jdbc.queryForList(
                "SELECT * FROM api_keys WHERE key_prefix = ? AND revoked_at IS NULL", prefix);
        if (keys.isEmpty() || !Tokens.sha256(raw).equals(String.valueOf(keys.get(0).get("key_hash")))) {
            throw new ApiException("AUTH_INVALID_API_KEY", "API Key 无效或权限不足", 401);
        }
        Map<String, Object> key = keys.get(0);
        String scopes = key.get("scopes") == null ? "" : String.valueOf(key.get("scopes"));
        if (!List.of(scopes.split(",")).contains(scope)) {
            throw new ApiException("AUTH_INVALID_API_KEY", "API Key 无效或权限不足", 401);
        }
        Map<String, Object> user = store.findUser(MarketStore.num(key.get("user_id")));
        if (user == null || !MarketStore.flag(user.get("is_active"))) {
            throw new ApiException("AUTH_INVALID_API_KEY", "API Key 无效或权限不足", 401);
        }
        jdbc.update("UPDATE api_keys SET last_used_at = ? WHERE id = ?", LocalDateTime.now().format(STAMP), MarketStore.num(key.get("id")));
        return user;
    }

    private void audit(Map<String, Object> agent, String action, String type, String resourceId) {
        jdbc.update("""
                INSERT INTO operation_logs
                (actor_id, actor_snapshot, action, resource_type, resource_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                MarketStore.num(agent.get("id")), agent.get("username"), action, type, resourceId, LocalDateTime.now().format(STAMP));
    }

    private static Map<String, Object> paged(Object data, int page, int pageSize, int total) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("data", data);
        body.put("pagination", Map.of("page", page, "page_size", pageSize, "total", total));
        return body;
    }

    private static Map<String, Object> stringMap(Map<?, ?> raw) {
        Map<String, Object> data = new LinkedHashMap<>();
        raw.forEach((key, value) -> data.put(String.valueOf(key), value));
        return data;
    }

    private static String firstContained(String text, List<String> words) {
        for (String word : words) {
            if (!word.isBlank() && text.contains(word)) {
                return word;
            }
        }
        return "";
    }

    private static Double number(Object value) {
        if (value == null || String.valueOf(value).isBlank()) {
            return null;
        }
        return Double.parseDouble(String.valueOf(value));
    }

    private static Double leadingNumber(String text) {
        String[] parts = text.replaceAll("[^0-9.]", " ").trim().split(" ");
        if (parts.length == 0 || parts[0].isBlank()) {
            return null;
        }
        return Double.parseDouble(parts[0]);
    }
}
