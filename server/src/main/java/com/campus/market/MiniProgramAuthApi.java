package com.campus.market;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
public class MiniProgramAuthApi {
    private final MarketStore store;
    private final Tokens tokens;
    private final CaptchaService captcha;
    private final LoginRateLimiter limiter;

    public MiniProgramAuthApi(MarketStore store, Tokens tokens,
                              CaptchaService captcha, LoginRateLimiter limiter) {
        this.store = store;
        this.tokens = tokens;
        this.captcha = captcha;
        this.limiter = limiter;
    }

    @PostMapping("/api/v1/auth/miniprogram/login")
    public Map<String, Object> login(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        limiter.hit(request, "mini-login");
        captcha.check(MarketStore.str(body.get("captcha_id")), MarketStore.str(body.get("captcha_code")));
        String identifier = MarketStore.str(body.get("identifier"));
        String password = body.get("password") == null ? "" : String.valueOf(body.get("password"));
        if (identifier.isBlank() || password.isBlank()) {
            throw new ApiException("VALIDATION_ERROR", "账号和密码不能为空", 422);
        }
        Map<String, Object> user = store.findUser(identifier);
        if (user == null || !tokens.passwordMatches(password, String.valueOf(user.get("password_hash")))) {
            if (user != null) {
                store.recordLoginFailure(user);
            }
            throw new ApiException("AUTH_INVALID_CREDENTIALS", "用户名或密码错误", 401);
        }
        if (!MarketStore.flag(user.get("is_active")) || user.get("deleted_at") != null) {
            throw new ApiException("AUTH_ACCOUNT_DISABLED", "账号已被禁用", 403);
        }
        long userId = MarketStore.num(user.get("id"));
        List<String> roles = store.roles(userId);
        if (roles.contains("agent_service")) {
            throw new ApiException("AUTH_FORBIDDEN", "服务账号不能从小程序登录", 403);
        }
        if (!roles.contains("normal_user") && !roles.contains("admin")) {
            throw new ApiException("AUTH_FORBIDDEN", "账号没有可用的登录角色", 403);
        }
        String loginRole = roles.contains("admin") ? "admin" : "normal_user";
        store.setLoginRole(userId, loginRole);
        store.resetLogin(userId);
        String refresh = store.createSession(userId);
        return Map.of("data", session(user, loginRole, roles, refresh));
    }

    @PostMapping("/api/v1/auth/miniprogram/refresh")
    public Map<String, Object> refresh(@RequestBody Map<String, Object> body) {
        String raw = MarketStore.str(body.get("refresh_token"));
        Long userId = store.rotateSession(raw);
        if (userId == null) {
            throw new ApiException("AUTH_REFRESH_INVALID", "刷新令牌无效或已过期", 401);
        }
        Map<String, Object> user = store.findUser(userId);
        if (user == null || !MarketStore.flag(user.get("is_active")) || user.get("deleted_at") != null) {
            throw new ApiException("AUTH_ACCOUNT_DISABLED", "账号不可用", 403);
        }
        List<String> roles = store.roles(userId);
        String loginRole = roles.contains("admin") ? "admin" : "normal_user";
        String refresh = store.createSession(userId);
        return Map.of("data", session(user, loginRole, roles, refresh));
    }

    private Map<String, Object> session(Map<String, Object> user, String loginRole,
                                        List<String> roles, String refresh) {
        long userId = MarketStore.num(user.get("id"));
        List<String> permissions = store.permissions(userId);
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("access_token", tokens.accessToken(userId, loginRole, roles, permissions));
        data.put("refresh_token", refresh);
        data.put("token_type", "Bearer");
        data.put("expires_in", 900);
        data.put("user", store.userPublic(store.findUser(userId), true));
        return data;
    }
}
