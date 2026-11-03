package com.campus.market;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@RestController
public class AgentKeyApi {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final Set<String> ALLOWED_SCOPES = Set.of("product:view", "recommendation:query");
    private static final SecureRandom RANDOM = new SecureRandom();
    private final JdbcTemplate jdbc;
    private final AdminGuard guard;
    private final MarketStore store;

    public AgentKeyApi(JdbcTemplate jdbc, AdminGuard guard, MarketStore store) {
        this.jdbc = jdbc;
        this.guard = guard;
        this.store = store;
    }

    @GetMapping("/api/v1/users/me/api-keys")
    public Map<String, Object> mine(HttpServletRequest request) {
        Map<String, Object> user = guard.authenticated(request);
        return Map.of("data", list(MarketStore.num(user.get("id"))));
    }

    @PostMapping("/api/v1/users/me/api-keys")
    public ResponseEntity<Map<String, Object>> createMine(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        Map<String, Object> user = guard.authenticated(request);
        String type = MarketStore.str(user.get("user_type"));
        if (!"agent_service".equals(type) && !"admin".equals(type)) {
            throw new ApiException("AUTH_FORBIDDEN", "只有服务账号可以创建 API Key", 403);
        }
        return ResponseEntity.status(201).body(Map.of("data", create(user, MarketStore.num(user.get("id")), body)));
    }

    @DeleteMapping("/api/v1/users/me/api-keys/{id}")
    public Map<String, Object> revokeMine(HttpServletRequest request, @PathVariable long id) {
        Map<String, Object> user = guard.authenticated(request);
        revoke(MarketStore.num(user.get("id")), id, user);
        return Map.of("data", Map.of("revoked", true));
    }

    @GetMapping("/api/v1/admin/agent-users")
    public Map<String, Object> agentUsers(HttpServletRequest request) {
        guard.require(request, "user:manage");
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT u.id, u.username, u.email, u.is_active, u.created_at,
                       COUNT(k.id) AS active_keys
                FROM users u
                LEFT JOIN api_keys k ON k.user_id = u.id AND k.revoked_at IS NULL
                WHERE u.user_type = 'agent_service' AND u.deleted_at IS NULL
                GROUP BY u.id, u.username, u.email, u.is_active, u.created_at
                ORDER BY u.id
                """);
        return Map.of("data", rows);
    }

    @GetMapping("/api/v1/admin/agent-users/{userId}/api-keys")
    public Map<String, Object> agentKeys(HttpServletRequest request, @PathVariable long userId) {
        guard.require(request, "user:manage");
        target(userId);
        return Map.of("data", list(userId));
    }

    @PostMapping("/api/v1/admin/agent-users/{userId}/api-keys")
    public ResponseEntity<Map<String, Object>> createForAgent(HttpServletRequest request, @PathVariable long userId,
                                                             @RequestBody Map<String, Object> body) {
        Map<String, Object> actor = guard.require(request, "user:manage");
        Map<String, Object> user = target(userId);
        return ResponseEntity.status(201).body(Map.of("data", create(actor, userId, body, user)));
    }

    @DeleteMapping("/api/v1/admin/agent-users/{userId}/api-keys/{id}")
    public Map<String, Object> revokeForAgent(HttpServletRequest request, @PathVariable long userId,
                                              @PathVariable long id) {
        Map<String, Object> actor = guard.require(request, "user:manage");
        target(userId);
        revoke(userId, id, actor);
        return Map.of("data", Map.of("revoked", true));
    }

    private Map<String, Object> create(Map<String, Object> actor, long userId, Map<String, Object> body) {
        return create(actor, userId, body, null);
    }

    private Map<String, Object> create(Map<String, Object> actor, long userId, Map<String, Object> body,
                                       Map<String, Object> targetUser) {
        List<String> scopes = scopes(body.get("scopes"));
        String name = valueOr(body.get("name"), "default");
        int days = body.get("expires_in_days") == null ? 30
                : (int) MarketStore.num(body.get("expires_in_days"));
        if (days < 0 || days > 3650) {
            throw new ApiException("VALIDATION_ERROR", "expires_in_days 必须在 0-3650 之间", 422);
        }

        String raw;
        String prefix;
        for (int attempt = 0; attempt < 3; attempt++) {
            prefix = "cmk_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);
            byte[] secret = new byte[32];
            RANDOM.nextBytes(secret);
            raw = prefix + "." + Base64.getUrlEncoder().withoutPadding().encodeToString(secret);
            Integer exists = jdbc.queryForObject("SELECT COUNT(*) FROM api_keys WHERE key_prefix = ?",
                    Integer.class, prefix);
            if (exists == null || exists == 0) {
                String expiresAt = days == 0 ? null : LocalDateTime.now().plusDays(days).format(STAMP);
                jdbc.update("""
                        INSERT INTO api_keys (user_id, name, key_prefix, key_hash, scopes, expires_at, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, userId, name.substring(0, Math.min(name.length(), 100)), prefix,
                        Tokens.sha256(raw), String.join(",", scopes), expiresAt,
                        LocalDateTime.now().format(STAMP));
                Map<String, Object> data = new LinkedHashMap<>();
                data.put("id", jdbc.queryForObject("SELECT id FROM api_keys WHERE key_prefix = ?", Long.class, prefix));
                data.put("name", name);
                data.put("prefix", prefix);
                data.put("api_key", raw);
                data.put("scopes", scopes);
                data.put("expires_at", expiresAt);
                store.writeLog(actor, "api_key.create", "api_key", String.valueOf(data.get("id")));
                if (targetUser != null && !targetUser.get("id").equals(actor.get("id"))) {
                    store.writeLog(actor, "agent.api_key.create", "agent_user", String.valueOf(userId));
                }
                return data;
            }
        }
        throw new ApiException("API_KEY_CONFLICT", "API Key 生成失败，请重试", 500);
    }

    private void revoke(long userId, long id, Map<String, Object> actor) {
        int changed = jdbc.update(
                "UPDATE api_keys SET revoked_at = ? WHERE id = ? AND user_id = ? AND revoked_at IS NULL",
                LocalDateTime.now().format(STAMP), id, userId);
        if (changed == 0) {
            throw new ApiException("NOT_FOUND", "API Key 不存在或已吊销", 404);
        }
        store.writeLog(actor, "api_key.revoke", "api_key", String.valueOf(id));
    }

    private List<Map<String, Object>> list(long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, name, key_prefix, scopes, expires_at, last_used_at, created_at
                FROM api_keys
                WHERE user_id = ? AND revoked_at IS NULL
                ORDER BY id DESC
                """, userId);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            Map<String, Object> item = new LinkedHashMap<>(row);
            item.put("prefix", row.get("key_prefix"));
            item.remove("key_prefix");
            item.put("scopes", scopes(row.get("scopes")));
            result.add(item);
        }
        return result;
    }

    private Map<String, Object> target(long userId) {
        Map<String, Object> user = store.findUser(userId);
        if (user == null || !"agent_service".equals(MarketStore.str(user.get("user_type")))
                || !MarketStore.flag(user.get("is_active")) || user.get("deleted_at") != null) {
            throw new ApiException("NOT_FOUND", "Agent 服务账号不存在或已禁用", 404);
        }
        return user;
    }

    private static List<String> scopes(Object value) {
        List<String> result = new ArrayList<>();
        if (value instanceof List<?> list) {
            for (Object item : list) {
                String scope = MarketStore.str(item);
                if (!ALLOWED_SCOPES.contains(scope)) {
                    throw new ApiException("VALIDATION_ERROR", "包含不支持的 scope", 422);
                }
                if (!result.contains(scope)) {
                    result.add(scope);
                }
            }
        } else {
            String raw = MarketStore.str(value);
            if (!raw.isBlank()) {
                for (String item : raw.split(",")) {
                    String scope = item.trim();
                    if (!ALLOWED_SCOPES.contains(scope)) {
                        throw new ApiException("VALIDATION_ERROR", "包含不支持的 scope", 422);
                    }
                    if (!result.contains(scope)) {
                        result.add(scope);
                    }
                }
            }
        }
        return result.isEmpty() ? List.of("product:view", "recommendation:query") : result;
    }

    private static String valueOr(Object value, String fallback) {
        String text = MarketStore.str(value);
        return text.isBlank() ? fallback : text;
    }
}
