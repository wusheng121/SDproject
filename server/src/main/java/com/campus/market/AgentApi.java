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
    private static final List<String[]> CATEGORY_ALIASES = List.of(
            new String[]{"保温水杯", "保温杯"},
            new String[]{"保温杯", "保温杯"},
            new String[]{"水杯", "保温杯"},
            new String[]{"杯子", "保温杯"},
            new String[]{"水壶", "保温杯"},
            new String[]{"书籍", "书籍"},
            new String[]{"教材", "书籍"},
            new String[]{"课本", "书籍"},
            new String[]{"书", "书籍"},
            new String[]{"智能手机", "手机"},
            new String[]{"电话", "手机"},
            new String[]{"手机", "手机"},
            new String[]{"单车", "自行车"},
            new String[]{"山地车", "自行车"},
            new String[]{"自行车", "自行车"},
            new String[]{"运动鞋", "运动鞋"},
            new String[]{"跑鞋", "运动鞋"}
    );
    private final JdbcTemplate jdbc;
    private final MarketStore store;
    private final CampusProperties properties;
    private final SkillRegistry skills;
    private final AgentAuth agentAuth;
    private final RestClient dataClient;

    public AgentApi(JdbcTemplate jdbc, MarketStore store, CampusProperties properties,
                    SkillRegistry skills, AgentAuth agentAuth) {
        this.jdbc = jdbc;
        this.store = store;
        this.properties = properties;
        this.skills = skills;
        this.agentAuth = agentAuth;
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
        if (!skills.isPublished(skill)) {
            throw new ApiException("SKILL_DISABLED", "Skill 不存在或已禁用", 403);
        }
        Map<String, Object> data = executeSkill(skill, params, MarketStore.num(agent.get("id")));
        audit(agent, "agent.skill." + skill, "skill", skill);
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("code", 0);
        response.put("message", "ok");
        response.put("data", data);
        return ResponseEntity.ok(response);
    }

    public Map<String, Object> executeSkill(String skill, Map<String, Object> params, long actorId) {
        return switch (skill) {
            case "product_query", "nl_filter" -> Map.of("skill", skill, "items", filterProducts(skill, params));
            case "recommendation_query" -> {
                Long userId = params.get("user_id") == null ? null : MarketStore.num(params.get("user_id"));
                int limit = params.get("limit") == null ? 6 : (int) MarketStore.num(params.get("limit"));
                long target = userId == null ? actorId : userId;
                yield recommend(target, limit);
            }
            case "product_detail" -> productDetail(params);
            case "product_compare" -> compareProducts(params);
            case "product_advice" -> productAdvice(params);
            case "seller_questions" -> sellerQuestions(params);
            case "product_recognize" -> recognizeImage(params);
            default -> throw new ApiException("VALIDATION_ERROR", "未知的 skill", 422);
        };
    }

    private Map<String, Object> productDetail(Map<String, Object> params) {
        long productId = productId(params);
        Map<String, Object> row = store.product(productId);
        if (row == null) {
            throw new ApiException("NOT_FOUND", "商品不存在", 404);
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("skill", "product_detail");
        data.put("product", store.productView(row, true));
        data.put("reviews", reviews(productId));
        return data;
    }

    private Map<String, Object> productAdvice(Map<String, Object> params) {
        Map<String, Object> detail = productDetail(params);
        Map<String, Object> product = map(detail.get("product"));
        double price = number(product.get("price")) == null ? 0 : number(product.get("price"));
        int conditionScore = conditionScore(MarketStore.str(product.get("condition")));
        List<String> pros = new ArrayList<>();
        List<String> risks = new ArrayList<>();
        List<String> missing = new ArrayList<>();

        String productName = MarketStore.str(product.get("name"));
        if (!MarketStore.str(product.get("brand")).isBlank()) {
            pros.add("品牌信息明确：" + MarketStore.str(product.get("brand")));
        } else if (productName.isBlank()) {
            missing.add("品牌或具体型号未填写");
        }
        if (conditionScore >= 95) {
            pros.add("成色较好，适合对品相要求较高的买家");
        } else if (conditionScore > 0) {
            risks.add("成色为" + product.get("condition") + "，建议确认实际磨损");
        }
        if (!MarketStore.str(product.get("defect_description")).isBlank()) {
            risks.add("卖家填写了瑕疵：" + MarketStore.str(product.get("defect_description")));
        } else {
            missing.add("未填写瑕疵说明，建议向卖家确认");
        }
        if (!MarketStore.str(product.get("trade_method")).isBlank()) {
            pros.add("交易方式：" + MarketStore.str(product.get("trade_method")));
        } else {
            missing.add("交易方式未填写");
        }
        if (!MarketStore.str(product.get("trade_location")).isBlank()) {
            pros.add("交易地点：" + MarketStore.str(product.get("trade_location")));
        } else {
            missing.add("交易地点未填写");
        }
        if (price > 0) {
            risks.add("标价 ¥" + price + "，请结合同类成交价判断是否合理");
        }

        List<String> questions = questions(product);
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("skill", "product_advice");
        data.put("product_id", product.get("id"));
        data.put("summary", "这件商品发布信息" + (missing.isEmpty() ? "较完整" : "还有信息缺失") + "，建议先确认瑕疵、配件和交易方式。");
        data.put("pros", pros);
        data.put("risks", risks);
        data.put("missing", missing);
        data.put("questions", questions);
        data.put("script", script(questions));
        data.put("condition_score", conditionScore);
        return data;
    }

    private Map<String, Object> sellerQuestions(Map<String, Object> params) {
        Map<String, Object> advice = productAdvice(params);
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("skill", "seller_questions");
        data.put("product_id", advice.get("product_id"));
        data.put("questions", advice.get("questions"));
        data.put("script", advice.get("script"));
        return data;
    }

    private Map<String, Object> compareProducts(Map<String, Object> params) {
        List<Long> ids = new ArrayList<>();
        Object raw = params.get("product_ids");
        if (raw instanceof List<?> list) {
            for (Object item : list) {
                ids.add(MarketStore.num(item));
            }
        }
        if (ids.isEmpty() && params.get("product_id") != null) {
            ids.add(MarketStore.num(params.get("product_id")));
        }
        if (ids.isEmpty()) {
            throw new ApiException("VALIDATION_ERROR", "请提供 product_ids", 422);
        }
        List<Map<String, Object>> items = new ArrayList<>();
        for (Long id : ids.subList(0, Math.min(ids.size(), 5))) {
            Map<String, Object> detail = productDetail(Map.of("product_id", id));
            Map<String, Object> product = map(detail.get("product"));
            double price = number(product.get("price")) == null ? 0 : number(product.get("price"));
            int score = conditionScore(MarketStore.str(product.get("condition")));
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("product_id", product.get("id"));
            item.put("name", product.get("name"));
            item.put("price", price);
            item.put("condition", product.get("condition"));
            item.put("condition_score", score);
            item.put("value_score", price <= 0 ? 0 : Math.round(score / price * 10000.0) / 100.0);
            item.put("defect_description", product.get("defect_description"));
            item.put("brand", product.get("brand"));
            item.put("trade_method", product.get("trade_method"));
            items.add(item);
        }
        Map<String, Object> best = items.stream()
                .max((a, b) -> Double.compare(number(a.get("value_score")), number(b.get("value_score"))))
                .orElse(null);
        String recommendation = best == null ? "暂无可对比商品"
                : "当前候选中，" + best.get("name") + " 的成色/价格组合相对更优；仍建议确认瑕疵和配件。";
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("skill", "product_compare");
        data.put("items", items);
        data.put("best_value_product_id", best == null ? null : best.get("product_id"));
        data.put("recommendation", recommendation);
        return data;
    }

    private List<Map<String, Object>> reviews(long productId) {
        return jdbc.queryForList("""
                SELECT r.id, r.score, r.comment, r.created_at, u.username
                FROM reviews r LEFT JOIN users u ON u.id = r.user_id
                WHERE r.product_id = ? ORDER BY r.id DESC LIMIT 20
                """, productId);
    }

    private static long productId(Map<String, Object> params) {
        if (params.get("product_id") == null) {
            throw new ApiException("VALIDATION_ERROR", "请提供 product_id", 422);
        }
        return MarketStore.num(params.get("product_id"));
    }

    private static int conditionScore(String condition) {
        return switch (condition) {
            case "全新" -> 100;
            case "九五新" -> 95;
            case "九成新" -> 90;
            case "八成新" -> 80;
            case "七成新" -> 70;
            default -> 0;
        };
    }

    private static List<String> questions(Map<String, Object> product) {
        List<String> questions = new ArrayList<>();
        if (MarketStore.str(product.get("defect_description")).isBlank()) {
            questions.add("商品有没有明显的划痕、磕碰或其他瑕疵？可以拍一下细节吗？");
        }
        if (MarketStore.str(product.get("brand")).isBlank() && MarketStore.str(product.get("name")).isBlank()) {
            questions.add("具体品牌和型号是什么？");
        }
        if (MarketStore.str(product.get("trade_method")).isBlank()) {
            questions.add("支持当面验机/验货吗？");
        }
        questions.add("配件、包装和购买凭证是否齐全？");
        questions.add("有没有维修、换件或进水记录？");
        String category = MarketStore.str(product.get("categories"));
        if (category.contains("手机") || category.contains("平板") || category.contains("电脑")) {
            questions.add("电池健康度或实际续航大概是多少？");
        }
        return questions;
    }

    private static String script(List<String> questions) {
        if (questions.isEmpty()) {
            return "你好，我对这件商品感兴趣，方便确认一下具体情况吗？";
        }
        return "你好，我对这件商品感兴趣，想确认一下：" + String.join("；", questions.subList(0, Math.min(3, questions.size()))) + "。谢谢！";
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Object value) {
        return value instanceof Map<?, ?> raw ? (Map<String, Object>) raw : Map.of();
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
            category = resolveCategory(text, category);
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

    private String resolveCategory(String text, String explicit) {
        if (!explicit.isBlank()) {
            for (String[] pair : CATEGORY_ALIASES) {
                if (explicit.equals(pair[0])) {
                    return pair[1];
                }
            }
            return explicit;
        }
        for (String[] pair : CATEGORY_ALIASES) {
            if (text.contains(pair[0])) {
                return pair[1];
            }
        }
        return firstContained(text, store.allCategories());
    }

    private Map<String, Object> requireKey(HttpServletRequest request, String scope) {
        return agentAuth.require(request, scope);
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
