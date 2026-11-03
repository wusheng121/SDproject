package com.campus.market;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class AdminGuard {
    private final Tokens tokens;
    private final MarketStore store;

    public AdminGuard(Tokens tokens, MarketStore store) {
        this.tokens = tokens;
        this.store = store;
    }

    public Map<String, Object> authenticated(HttpServletRequest request) {
        Long userId = tokens.userId(request);
        if (userId == null) {
            throw new ApiException("AUTH_REQUIRED", "未登录或会话已过期", 401);
        }
        Map<String, Object> user = store.findUser(userId);
        if (user == null || !MarketStore.flag(user.get("is_active")) || user.get("deleted_at") != null) {
            throw new ApiException("AUTH_REQUIRED", "未登录或会话已过期", 401);
        }
        return user;
    }

    public Map<String, Object> require(HttpServletRequest request, String permission) {
        Map<String, Object> user = authenticated(request);
        if (!store.hasPermission(MarketStore.num(user.get("id")), permission)) {
            throw new ApiException("AUTH_FORBIDDEN", "没有执行该操作的权限", 403);
        }
        return user;
    }
}
