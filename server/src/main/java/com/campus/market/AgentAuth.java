package com.campus.market;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Component
public class AgentAuth {
    private final JdbcTemplate jdbc;
    private final MarketStore store;

    public AgentAuth(JdbcTemplate jdbc, MarketStore store) {
        this.jdbc = jdbc;
        this.store = store;
    }

    public Principal authenticate(HttpServletRequest request) {
        String raw = request.getHeader("X-API-Key");
        String authorization = request.getHeader("Authorization");
        if ((raw == null || raw.isBlank()) && authorization != null
                && authorization.regionMatches(true, 0, "Bearer ", 0, 7)) {
            raw = authorization.substring(7).trim();
        }
        if (raw == null || !raw.startsWith("cmk_") || !raw.contains(".")) {
            throw invalid();
        }

        String prefix = raw.substring(0, raw.indexOf('.'));
        List<Map<String, Object>> keys = jdbc.queryForList(
                "SELECT * FROM api_keys WHERE key_prefix = ? AND revoked_at IS NULL "
                        + "AND (expires_at IS NULL OR expires_at > NOW())", prefix);
        if (keys.isEmpty()) {
            throw invalid();
        }
        Map<String, Object> key = keys.get(0);
        String expected = String.valueOf(key.get("key_hash"));
        String actual = Tokens.sha256(raw);
        if (!MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8), actual.getBytes(StandardCharsets.UTF_8))) {
            throw invalid();
        }
        Map<String, Object> user = store.findUser(MarketStore.num(key.get("user_id")));
        if (user == null || !MarketStore.flag(user.get("is_active")) || user.get("deleted_at") != null) {
            throw invalid();
        }
        String userType = MarketStore.str(user.get("user_type"));
        if (!"agent_service".equals(userType) && !"admin".equals(userType)) {
            throw invalid();
        }

        jdbc.update("UPDATE api_keys SET last_used_at = ? WHERE id = ?",
                LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")),
                MarketStore.num(key.get("id")));
        return new Principal(user, key, scopes(key));
    }

    public Map<String, Object> require(HttpServletRequest request, String scope) {
        Principal principal = authenticate(request);
        requireScope(principal, scope);
        return principal.user();
    }

    public void requireScope(Principal principal, String scope) {
        if (scope != null && !scope.isBlank() && !principal.scopes().contains(scope)) {
            throw new ApiException("AUTH_FORBIDDEN", "API Key 缺少所需 scope", 403);
        }
    }

    private static Set<String> scopes(Map<String, Object> key) {
        String raw = key.get("scopes") == null ? "" : String.valueOf(key.get("scopes"));
        return Arrays.stream(raw.split(","))
                .map(String::trim)
                .filter(s -> !s.isBlank())
                .collect(Collectors.toSet());
    }

    private static ApiException invalid() {
        return new ApiException("AUTH_INVALID_API_KEY", "API Key 无效或权限不足", 401);
    }

    public record Principal(Map<String, Object> user, Map<String, Object> key, Set<String> scopes) {
    }
}
