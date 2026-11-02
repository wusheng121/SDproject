package com.campus.market;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
public class MessageApi {
    private final MarketStore store;
    private final Tokens tokens;
    private final SellerMessages messages;

    public MessageApi(MarketStore store, Tokens tokens, SellerMessages messages) {
        this.store = store;
        this.tokens = tokens;
        this.messages = messages;
    }

    @GetMapping("/api/v1/messages/conversations")
    public Map<String, Object> list(HttpServletRequest request) {
        long userId = MarketStore.num(require(request).get("id"));
        return Map.of("data", messages.list(userId));
    }

    @PostMapping("/api/v1/messages/conversations")
    public Map<String, Object> open(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        long userId = MarketStore.num(require(request).get("id"));
        Map<String, Object> conversation = messages.open(userId, MarketStore.num(body.get("product_id")));
        return Map.of("data", conversation);
    }

    @GetMapping("/api/v1/messages/conversations/{id}")
    public Map<String, Object> thread(HttpServletRequest request, @PathVariable long id) {
        long userId = MarketStore.num(require(request).get("id"));
        return Map.of("data", messages.messages(userId, id));
    }

    @PostMapping("/api/v1/messages/conversations/{id}")
    public Map<String, Object> send(HttpServletRequest request, @PathVariable long id, @RequestBody Map<String, Object> body) {
        long userId = MarketStore.num(require(request).get("id"));
        return Map.of("data", messages.send(userId, id, MarketStore.str(body.get("content"))));
    }

    private Map<String, Object> require(HttpServletRequest request) {
        Long userId = tokens.userId(request);
        if (userId == null) {
            throw new ApiException("AUTH_REQUIRED", "未登录或会话已过期", 401);
        }
        Map<String, Object> user = store.findUser(userId);
        if (user == null || !MarketStore.flag(user.get("is_active"))) {
            throw new ApiException("AUTH_REQUIRED", "未登录或会话已过期", 401);
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("id", user.get("id"));
        data.put("username", user.get("username"));
        return data;
    }
}
