package com.campus.market;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.EnableTransactionManagement;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@EnableTransactionManagement
public class CampusApi {
    private final MarketStore store;
    private final Tokens tokens;
    private final PhoneCipher phones;
    private final AccountMail mail;
    private final CatalogCache cache;
    private final CaptchaService captcha;
    private final LoginRateLimiter limiter;
    private final ProductEventPublisher events;
    private final ProductSearchIndex searchIndex;
    private final ProductImageStore images;

    public CampusApi(MarketStore store, Tokens tokens, PhoneCipher phones, AccountMail mail, CatalogCache cache, CaptchaService captcha, LoginRateLimiter limiter, ProductEventPublisher events, ProductSearchIndex searchIndex, ProductImageStore images) {
        this.store = store;
        this.tokens = tokens;
        this.phones = phones;
        this.mail = mail;
        this.cache = cache;
        this.captcha = captcha;
        this.limiter = limiter;
        this.events = events;
        this.searchIndex = searchIndex;
        this.images = images;
    }

    @GetMapping("/api/v1/auth/captcha")
    public Map<String, Object> captcha() {
        return Map.of("data", captcha.issue());
    }

    @PostMapping("/api/v1/auth/register")
    public ResponseEntity<Map<String, Object>> register(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        limiter.hit(request, "register");
        captcha.check(MarketStore.str(body.get("captcha_id")), MarketStore.str(body.get("captcha_code")));
        String username = MarketStore.str(body.get("username"));
        String email = MarketStore.str(body.get("email")).toLowerCase();
        String password = body.get("password") == null ? "" : String.valueOf(body.get("password"));
        if (username.length() < 3 || username.length() > 50 || username.indexOf('<') >= 0) {
            throw new ApiException("VALIDATION_ERROR", "用户名长度必须为 3-50 位，且不能包含 HTML 标签", 422);
        }
        if (!email.matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")) {
            throw new ApiException("VALIDATION_ERROR", "邮箱格式不正确", 422);
        }
        if (!validPassword(password)) {
            throw new ApiException("VALIDATION_ERROR", "密码至少 8 位，并包含字母和数字", 422);
        }
        String phone = phoneOrNull(body.get("phone"));
        String phoneHash = phones.hash(phone);
        if (store.findUser(username) != null || store.findUser(email) != null) {
            throw new ApiException("AUTH_ACCOUNT_EXISTS", "用户名或邮箱已存在", 409);
        }
        if (store.phoneTaken(phoneHash)) {
            throw new ApiException("AUTH_PHONE_EXISTS", "手机号已被使用", 409);
        }
        String requestedRole = MarketStore.str(body.get("login_role"));
        if ("admin".equals(requestedRole) || "agent_service".equals(requestedRole)) {
            throw new ApiException("AUTH_FORBIDDEN", "公开注册不能创建管理员或服务账号", 403);
        }
        long userId = store.register(username, email, tokens.hashPassword(password), phones.encrypt(phone), phoneHash);
        mail.sendVerification(email, store.issueEmailToken(userId));
        return ResponseEntity.status(201).body(Map.of("data", Map.of("user", store.userPublic(store.findUser(userId), false))));
    }

    @PostMapping("/api/v1/auth/verify-email")
    public Map<String, Object> verifyEmail(@RequestBody Map<String, Object> body) {
        if (!store.verifyEmail(MarketStore.str(body.get("token")))) {
            throw new ApiException("AUTH_TOKEN_INVALID", "验证链接无效或已过期", 400);
        }
        return Map.of("data", Map.of("verified", true));
    }

    @PostMapping("/api/v1/auth/resend-verification")
    public Map<String, Object> resendVerification(HttpServletRequest request) {
        Map<String, Object> user = require(request);
        if (user.get("email_verified_at") != null) {
            return Map.of("data", Map.of("sent", false, "message", "邮箱已验证"));
        }
        mail.sendVerification(String.valueOf(user.get("email")), store.issueEmailToken(MarketStore.num(user.get("id"))));
        return Map.of("data", Map.of("sent", true));
    }

    @PostMapping("/api/v1/auth/forgot-password")
    public Map<String, Object> forgotPassword(@RequestBody Map<String, Object> body) {
        String email = MarketStore.str(body.get("email")).toLowerCase();
        Map<String, Object> user = store.findUser(email);
        if (user != null && email.equals(String.valueOf(user.get("email_normalized")).toLowerCase()) && MarketStore.flag(user.get("is_active"))) {
            mail.sendPasswordReset(email, store.issueResetToken(MarketStore.num(user.get("id"))));
        }
        return Map.of("data", Map.of("sent", true));
    }

    @PostMapping("/api/v1/auth/reset-password")
    public Map<String, Object> resetPassword(@RequestBody Map<String, Object> body) {
        String password = body.get("new_password") == null ? "" : String.valueOf(body.get("new_password"));
        if (!validPassword(password)) {
            throw new ApiException("VALIDATION_ERROR", "密码至少 8 位，并包含字母和数字", 422);
        }
        if (!store.resetPassword(MarketStore.str(body.get("token")), tokens.hashPassword(password))) {
            throw new ApiException("AUTH_TOKEN_INVALID", "重置链接无效或已过期", 400);
        }
        return Map.of("data", Map.of("reset", true));
    }

    @PostMapping("/api/v1/auth/login")
    public ResponseEntity<Map<String, Object>> login(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        limiter.hit(request, "login");
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
            throw new ApiException("AUTH_FORBIDDEN", "助手账号只供外部接口使用，不能从网页登录", 403);
        }
        if (!roles.contains("normal_user") && !roles.contains("admin")) {
            throw new ApiException("AUTH_FORBIDDEN", "账号没有可用的登录角色", 403);
        }
        String loginRole = roles.contains("admin") ? "admin" : "normal_user";
        store.setLoginRole(userId, loginRole);
        store.resetLogin(userId);
        String refresh = store.createSession(userId);
        List<String> permissions = store.permissions(userId);
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("access_token", tokens.accessToken(userId, loginRole, roles, permissions));
        data.put("token_type", "Bearer");
        data.put("expires_in", 900);
        data.put("user", store.userPublic(store.findUser(userId), true));
        return ResponseEntity.ok().header(HttpHeaders.SET_COOKIE, Tokens.refreshCookie(refresh)).body(Map.of("data", data));
    }

    @PostMapping("/api/v1/auth/refresh")
    public ResponseEntity<Map<String, Object>> refresh(HttpServletRequest request) {
        Long userId = store.rotateSession(Tokens.readCookie(request, "cm_refresh"));
        if (userId == null) {
            throw new ApiException("AUTH_REFRESH_INVALID", "刷新令牌无效或已过期", 401);
        }
        String refresh = store.createSession(userId);
        Map<String, Object> user = store.findUser(userId);
        List<String> roles = store.roles(userId);
        String effectiveRole = roles.contains("admin") ? "admin" : "normal_user";
        List<String> permissions = store.permissions(userId);
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("access_token", tokens.accessToken(userId, effectiveRole, roles, permissions));
        data.put("token_type", "Bearer");
        data.put("expires_in", 900);
        data.put("user", store.userPublic(user, true));
        return ResponseEntity.ok().header(HttpHeaders.SET_COOKIE, Tokens.refreshCookie(refresh)).body(Map.of("data", data));
    }

    @PostMapping("/api/v1/auth/logout")
    public ResponseEntity<Map<String, Object>> logout(HttpServletRequest request) {
        store.revokeSession(Tokens.readCookie(request, "cm_refresh"));
        return ResponseEntity.ok()
                .header(HttpHeaders.SET_COOKIE, Tokens.clearRefreshCookie())
                .body(Map.of("data", Map.of("logged_out", true)));
    }

    @GetMapping("/api/v1/users/me")
    public Map<String, Object> me(HttpServletRequest request) {
        return Map.of("data", Map.of("user", store.userPublic(require(request), true)));
    }

    @PatchMapping("/api/v1/users/me")
    public Map<String, Object> updateMe(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        Map<String, Object> user = require(request);
        String username = null;
        if (body.containsKey("username")) {
            username = MarketStore.str(body.get("username"));
            if (username.length() < 3 || username.length() > 50 || username.indexOf('<') >= 0) {
                throw new ApiException("VALIDATION_ERROR", "用户名长度必须为 3-50 位，且不能包含 HTML 标签", 422);
            }
        }
        boolean changePhone = body.containsKey("phone");
        String phone = null;
        String phoneHash = null;
        if (changePhone) {
            phone = phoneOrNull(body.get("phone"));
            phoneHash = phones.hash(phone);
        }
        String email = null;
        if (body.containsKey("email")) {
            email = MarketStore.str(body.get("email")).toLowerCase();
            if (!email.matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$") || email.indexOf('<') >= 0) {
                throw new ApiException("VALIDATION_ERROR", "邮箱格式不正确", 422);
            }
        }
        long userId = MarketStore.num(user.get("id"));
        boolean emailChanged = store.updateProfile(userId, username, changePhone, phones.encrypt(phone), phoneHash, email);
        if (emailChanged) {
            mail.sendVerification(email, store.issueEmailToken(userId));
        }
        return Map.of("data", Map.of("user", store.userPublic(store.findUser(userId), true)));
    }

    @PostMapping("/api/v1/users/me/close")
    public ResponseEntity<Map<String, Object>> closeAccount(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        Map<String, Object> user = require(request);
        String password = body.get("password") == null ? "" : String.valueOf(body.get("password"));
        if (!tokens.passwordMatches(password, String.valueOf(user.get("password_hash")))) {
            throw new ApiException("VALIDATION_ERROR", "密码不正确", 422);
        }
        String type = String.valueOf(user.get("user_type"));
        if ("admin".equals(type) || "agent_service".equals(type)) {
            throw new ApiException("ACCOUNT_PROTECTED", "管理员和助手账号不能在这里注销", 409);
        }
        long userId = MarketStore.num(user.get("id"));
        List<Long> listingIds = store.closeAccount(userId);
        for (Long productId : listingIds) {
            events.publish(productId, "updated");
        }
        return ResponseEntity.ok()
                .header(HttpHeaders.SET_COOKIE, Tokens.clearRefreshCookie())
                .body(Map.of("data", Map.of("closed", true)));
    }

    @PostMapping("/api/v1/users/me/password")
    public Map<String, Object> changePassword(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        Map<String, Object> user = require(request);
        String current = body.get("current_password") == null ? "" : String.valueOf(body.get("current_password"));
        String newPassword = body.get("new_password") == null ? "" : String.valueOf(body.get("new_password"));
        if (!tokens.passwordMatches(current, String.valueOf(user.get("password_hash")))) {
            throw new ApiException("VALIDATION_ERROR", "当前密码不正确", 422);
        }
        if (!validPassword(newPassword)) {
            throw new ApiException("VALIDATION_ERROR", "新密码至少 8 位，且必须包含字母和数字", 422);
        }
        long userId = MarketStore.num(user.get("id"));
        store.changePassword(userId, tokens.hashPassword(newPassword));
        return Map.of("data", Map.of("updated", true, "must_change_password", false));
    }

    @GetMapping("/api/v1/users/me/preferences")
    public Map<String, Object> preferences(HttpServletRequest request) {
        Map<String, Object> user = require(request);
        List<String> categories = (List<String>) store.userPublic(user, false).get("preferred_categories");
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("preferred_categories", categories);
        data.put("has_preference", user.get("preferred_categories") != null);
        return Map.of("data", data);
    }

    @PutMapping("/api/v1/users/me/preferences")
    public Map<String, Object> savePreferences(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        Object raw = body.get("categories");
        if (!(raw instanceof List<?> categories)) {
            throw new ApiException("VALIDATION_ERROR", "categories 必须是数组", 422);
        }
        long userId = MarketStore.num(require(request).get("id"));
        store.savePreferences(userId, categories.stream().map(String::valueOf).toList());
        return Map.of("data", Map.of("preferred_categories", categories));
    }

    @GetMapping("/api/v1/users/me/stats")
    public Map<String, Object> stats(HttpServletRequest request) {
        return Map.of("data", store.stats(MarketStore.num(require(request).get("id"))));
    }

    @GetMapping("/api/categories")
    public Map<String, Object> categories(HttpServletRequest request) {
        return ok(Map.of("items", cache.read("categories", store::allCategories, request)));
    }

    @GetMapping("/api/products")
    public Map<String, Object> products(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(name = "page_size", defaultValue = "12") int pageSize,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String q,
            @RequestParam(name = "min_condition", required = false) String minCondition,
            @RequestParam(name = "min_price", required = false) Double minPrice,
            @RequestParam(name = "max_price", required = false) Double maxPrice,
            @RequestParam(defaultValue = "new") String sort) {
        page = Math.max(page, 1);
        pageSize = Math.min(Math.max(pageSize, 1), 50);
        List<Map<String, Object>> items = store.listProducts(category, q, minCondition, minPrice, maxPrice, sort, page, pageSize).stream()
                .map(row -> store.productView(row, false)).toList();
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("page", page);
        data.put("page_size", pageSize);
        data.put("total", store.countProducts(category, q, minCondition, minPrice, maxPrice));
        data.put("items", items);
        return ok(data);
    }

    @GetMapping("/api/products/search")
    public Map<String, Object> search(
            HttpServletRequest request,
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String category,
            @RequestParam(name = "min_condition", required = false) String minCondition,
            @RequestParam(name = "min_price", required = false) Double minPrice,
            @RequestParam(name = "max_price", required = false) Double maxPrice,
            @RequestParam(defaultValue = "new") String sort) {
        if ((q == null || q.isBlank()) && (category == null || category.isBlank()) && minPrice == null && maxPrice == null && (minCondition == null || minCondition.isBlank())) {
            return ok(Map.of("items", List.of(), "total", 0, "personalized", false));
        }
        List<Long> indexed = q == null || q.isBlank() ? null : searchIndex.findIds(q);
        List<Map<String, Object>> rows = indexed == null
                ? store.listProducts(category, q, minCondition, minPrice, maxPrice, sort, 1, 50)
                : store.listProductsByIds(indexed, category, minCondition, minPrice, maxPrice);
        Long userId = tokens.userId(request);
        boolean personal = userId != null && (sort == null || sort.isBlank() || "hot".equals(sort) || "personal".equals(sort));
        if (personal) {
            rows = store.rankForUser(userId, rows);
        }
        List<Map<String, Object>> items = rows.stream().map(row -> {
            Map<String, Object> item = store.productView(row, false);
            item.put("brand", row.get("brand"));
            item.put("condition", row.get("condition_level"));
            return item;
        }).toList();
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("items", items);
        data.put("total", items.size());
        data.put("personalized", personal);
        data.put("search_engine", indexed == null ? "mysql" : "elasticsearch");
        return ok(data);
    }

    @GetMapping("/api/products/{id}")
    public Map<String, Object> product(@PathVariable long id, HttpServletRequest request) {
        Object cached = cache.read("product:" + id, () -> {
            Map<String, Object> row = store.product(id);
            return row == null ? null : store.productView(row, true);
        }, request);
        if (!(cached instanceof Map<?, ?> raw)) {
            throw new ApiException("NOT_FOUND", "商品不存在", 404);
        }
        Map<String, Object> data = new LinkedHashMap<>();
        raw.forEach((key, value) -> data.put(String.valueOf(key), value));
        Long userId = tokens.userId(request);
        data.put("is_favorited", userId != null && store.favorited(userId, id));
        return ok(data);
    }

    @PostMapping("/api/products/images")
    public Map<String, Object> uploadProductImage(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        require(request);
        String url = images.save(MarketStore.str(body.get("image_base64")), MarketStore.str(body.get("mime")));
        return ok(Map.of("image_url", url));
    }

    @PostMapping("/api/products")
    public Map<String, Object> publish(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        long id = store.publish(MarketStore.num(require(request).get("id")), body);
        events.publish(id, "pending");
        return ok(Map.of("id", id, "status", "pending"));
    }

    @GetMapping("/api/v1/users/me/products")
    public Map<String, Object> myProducts(HttpServletRequest request) {
        long userId = MarketStore.num(require(request).get("id"));
        List<Map<String, Object>> items = store.myProducts(userId).stream()
                .map(row -> store.productView(row, true)).toList();
        return Map.of("data", Map.of("items", items));
    }

    @PutMapping("/api/products/{id}")
    public Map<String, Object> editProduct(HttpServletRequest request, @PathVariable long id, @RequestBody Map<String, Object> body) {
        Map<String, Object> product = store.updateOwnProduct(MarketStore.num(require(request).get("id")), id, body);
        dropProductCache(id);
        events.publish(id, String.valueOf(product.get("status")));
        return ok(Map.of("product", product));
    }

    @DeleteMapping("/api/products/{id}")
    public Map<String, Object> offlineProduct(HttpServletRequest request, @PathVariable long id) {
        long userId = MarketStore.num(require(request).get("id"));
        Map<String, Object> current = store.product(id);
        String status = current == null ? "" : String.valueOf(current.get("status"));
        if ("pending".equals(status) || "rejected".equals(status) || "offline".equals(status)) {
            store.deleteOwnProduct(userId, id);
            images.deleteIfOwned(MarketStore.str(current.get("image_url")));
            dropProductCache(id);
            events.publish(id, "deleted");
            return ok(Map.of("deleted", true));
        }
        Map<String, Object> product = store.offlineOwnProduct(userId, id);
        dropProductCache(id);
        events.publish(id, "offline");
        return ok(Map.of("product", product));
    }

    @GetMapping("/api/v1/cart")
    public Map<String, Object> cart(HttpServletRequest request) {
        long userId = MarketStore.num(require(request).get("id"));
        List<Map<String, Object>> items = new java.util.ArrayList<>();
        double total = 0;
        for (Map<String, Object> row : store.cart(userId)) {
            double price = ((Number) row.get("price")).doubleValue();
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", MarketStore.num(row.get("id")));
            item.put("product_id", MarketStore.num(row.get("product_id")));
            item.put("name", row.get("name"));
            item.put("price", price);
            item.put("condition", row.get("condition_level"));
            item.put("image_url", row.get("image_url"));
            item.put("status", row.get("status"));
            item.put("quantity", 1);
            item.put("line_amount", price);
            item.put("seller", Map.of("id", MarketStore.num(row.get("seller_id")), "username", row.get("seller_name")));
            items.add(item);
            total += price;
        }
        return Map.of("data", Map.of("items", items, "total_amount", Math.round(total * 100) / 100.0));
    }

    @PostMapping("/api/v1/cart")
    public ResponseEntity<Map<String, Object>> addCart(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        long userId = MarketStore.num(require(request).get("id"));
        long productId = MarketStore.num(body.get("product_id"));
        boolean created = store.addCart(userId, productId);
        return ResponseEntity.status(created ? 201 : 200).body(Map.of("data", Map.of("created", created)));
    }

    @DeleteMapping("/api/v1/cart/{productId}")
    public Map<String, Object> deleteCart(HttpServletRequest request, @PathVariable long productId) {
        store.removeCart(MarketStore.num(require(request).get("id")), productId);
        return Map.of("data", Map.of("removed", true));
    }

    @GetMapping("/api/v1/orders")
    public Map<String, Object> orders(HttpServletRequest request) {
        return Map.of("data", Map.of("items", store.orders(MarketStore.num(require(request).get("id")))));
    }

    @PostMapping("/api/v1/orders")
    public ResponseEntity<Map<String, Object>> createOrder(HttpServletRequest request, @RequestBody(required = false) Map<String, Object> body) {
        List<Integer> ids = null;
        if (body != null && body.get("product_ids") instanceof List<?> raw) {
            ids = raw.stream().map(item -> (int) MarketStore.num(item)).toList();
        }
        Map<String, Object> order = store.createOrder(MarketStore.num(require(request).get("id")), ids);
        return ResponseEntity.status(201).body(Map.of("data", order));
    }

    @PostMapping("/api/v1/orders/{orderId}/pay")
    public Map<String, Object> pay(HttpServletRequest request, @PathVariable long orderId) {
        Map<String, Object> order = store.pay(MarketStore.num(require(request).get("id")), orderId);
        Object items = order.get("items");
        if (items instanceof List<?> rows) {
            for (Object row : rows) {
                if (row instanceof Map<?, ?> item && item.get("product_id") != null) {
                    long productId = MarketStore.num(item.get("product_id"));
                    dropProductCache(productId);
                    events.publish(productId, "sold");
                }
            }
        }
        return Map.of("data", order);
    }

    @PostMapping("/api/v1/orders/{orderId}/cancel")
    public Map<String, Object> cancel(HttpServletRequest request, @PathVariable long orderId) {
        return Map.of("data", store.cancel(MarketStore.num(require(request).get("id")), orderId));
    }

    @GetMapping("/api/v1/products/{id}/reviews")
    public Map<String, Object> productReviews(@PathVariable long id) {
        return ok(Map.of("items", store.productReviews(id)));
    }

    @PostMapping("/api/v1/orders/{orderId}/reviews")
    public ResponseEntity<Map<String, Object>> review(HttpServletRequest request, @PathVariable long orderId, @RequestBody Map<String, Object> body) {
        store.review(
                MarketStore.num(require(request).get("id")),
                orderId,
                MarketStore.num(body.get("product_id")),
                (int) MarketStore.num(body.get("score")),
                MarketStore.str(body.get("comment")));
        return ResponseEntity.status(201).body(Map.of("data", Map.of("created", true)));
    }

    @PostMapping("/api/v1/behaviors")
    public ResponseEntity<Map<String, Object>> behavior(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        String type = MarketStore.str(body.get("behavior_type"));
        if (!List.of("view", "favorite", "add_cart", "order", "review").contains(type)) {
            throw new ApiException("VALIDATION_ERROR", "behavior_type 无效", 422);
        }
        Integer value = body.get("value") == null ? null : (int) MarketStore.num(body.get("value"));
        store.recordBehavior(MarketStore.num(require(request).get("id")), MarketStore.num(body.get("product_id")), type, value);
        return ResponseEntity.status(201).body(Map.of("data", Map.of("recorded", true)));
    }

    @GetMapping("/api/v1/users/me/favorites")
    public Map<String, Object> favorites(HttpServletRequest request) {
        return Map.of("data", store.favorites(MarketStore.num(require(request).get("id"))));
    }

    @GetMapping("/api/v1/admin/users")
    public Map<String, Object> adminUsers(HttpServletRequest request, @RequestParam(defaultValue = "1") int page, @RequestParam(name = "page_size", defaultValue = "20") int pageSize, @RequestParam(required = false) String keyword, @RequestParam(required = false) String role, @RequestParam(required = false) String status) {
        requirePermission(request, "user:manage");
        List<Map<String, Object>> users = store.adminUsers(keyword, role, status, page, pageSize).stream()
                .map(user -> store.userPublic(user, true)).toList();
        return paged(users, page, pageSize, store.countUsers(keyword, role, status));
    }

    @GetMapping("/api/v1/admin/users/{id}")
    public Map<String, Object> adminUser(HttpServletRequest request, @PathVariable long id) {
        requirePermission(request, "user:manage");
        Map<String, Object> user = store.findUser(id);
        if (user == null) {
            throw new ApiException("NOT_FOUND", "用户不存在", 404);
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("user", store.userPublic(user, true));
        data.put("recent_behaviors", store.recentBehaviors(id));
        data.put("behavior_window_days", 7);
        return Map.of("data", data);
    }

    @PostMapping("/api/v1/admin/users/{id}/ban")
    public Map<String, Object> ban(HttpServletRequest request, @PathVariable long id) {
        Map<String, Object> admin = requirePermission(request, "user:manage");
        if (MarketStore.num(admin.get("id")) == id) {
            throw new ApiException("VALIDATION_ERROR", "不能封禁自己", 409);
        }
        store.setActive(id, false);
        store.writeLog(admin, "user.ban", "user", String.valueOf(id));
        return Map.of("data", Map.of("user", store.userPublic(store.findUser(id), true)));
    }

    @PostMapping("/api/v1/admin/users/{id}/unban")
    public Map<String, Object> unban(HttpServletRequest request, @PathVariable long id) {
        Map<String, Object> admin = requirePermission(request, "user:manage");
        store.setActive(id, true);
        store.writeLog(admin, "user.unban", "user", String.valueOf(id));
        return Map.of("data", Map.of("user", store.userPublic(store.findUser(id), true)));
    }

    @PutMapping("/api/v1/admin/users/{id}/roles")
    public Map<String, Object> setRoles(HttpServletRequest request, @PathVariable long id, @RequestBody Map<String, Object> body) {
        Map<String, Object> admin = requirePermission(request, "user:manage");
        Object raw = body.get("roles");
        if (!(raw instanceof List<?> list) || list.isEmpty()) {
            throw new ApiException("VALIDATION_ERROR", "roles 必须是非空数组", 422);
        }
        List<String> names = list.stream().map(MarketStore::str).filter(name -> !name.isBlank()).distinct().toList();
        Map<String, Object> user = store.setUserRoles(MarketStore.num(admin.get("id")), String.valueOf(admin.get("username")), id, names);
        return Map.of("data", Map.of("user", user));
    }

    @GetMapping("/api/v1/admin/products")
    public Map<String, Object> adminProducts(HttpServletRequest request, @RequestParam(required = false) String status, @RequestParam(defaultValue = "1") int page, @RequestParam(name = "page_size", defaultValue = "20") int pageSize) {
        requirePermission(request, "product:audit");
        List<Map<String, Object>> items = store.adminProducts(status, page, pageSize).stream()
                .map(row -> store.productView(row, true)).toList();
        return paged(items, page, pageSize, store.countAdminProducts(status));
    }

    @PostMapping("/api/v1/admin/products/{id}/approve")
    public Map<String, Object> approve(HttpServletRequest request, @PathVariable long id) {
        return changeStatus(request, id, "approved", null, "pending", "rejected");
    }

    @PostMapping("/api/v1/admin/products/{id}/reject")
    public Map<String, Object> reject(HttpServletRequest request, @PathVariable long id, @RequestBody(required = false) Map<String, Object> body) {
        String reason = body == null ? "" : MarketStore.str(body.get("reason")).trim();
        if (reason.isEmpty() || reason.length() > 200) {
            throw new ApiException("VALIDATION_ERROR", "请填写拒绝原因，不超过 200 字", 422);
        }
        return changeStatus(request, id, "rejected", reason, "pending");
    }

    @PostMapping("/api/v1/admin/products/{id}/offline")
    public Map<String, Object> offline(HttpServletRequest request, @PathVariable long id) {
        return changeStatus(request, id, "offline", null, "approved");
    }

    @GetMapping("/api/v1/admin/stats")
    public Map<String, Object> adminStats(HttpServletRequest request) {
        requirePermission(request, "user:manage");
        return Map.of("data", store.adminStats());
    }

    @GetMapping("/api/v1/admin/operation-logs")
    public Map<String, Object> logs(HttpServletRequest request,
                                    @RequestParam(required = false) String action,
                                    @RequestParam(name = "resource_type", required = false) String resourceType,
                                    @RequestParam(defaultValue = "1") int page,
                                    @RequestParam(name = "page_size", defaultValue = "20") int pageSize) {
        requirePermission(request, "user:manage");
        return paged(store.logs(action, resourceType, page, pageSize), page, pageSize, store.countLogs(action, resourceType));
    }

    @GetMapping("/api/v1/admin/agent-dialogues/{id}")
    public Map<String, Object> agentDialogue(HttpServletRequest request, @PathVariable String id) {
        requirePermission(request, "user:manage");
        Map<String, Object> dialogue = store.agentDialogue(id);
        if (dialogue == null) {
            throw new ApiException("NOT_FOUND", "这段对话不存在", 404);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("data", dialogue);
        return body;
    }

    @GetMapping("/health/live")
    public Map<String, Object> live() {
        return Map.of("status", "ok", "server", "spring-boot");
    }

    private Map<String, Object> changeStatus(HttpServletRequest request, long id, String status, String rejectReason, String... allowed) {
        Map<String, Object> admin = requirePermission(request, "product:audit");
        Map<String, Object> product = store.product(id);
        if (product == null) {
            throw new ApiException("NOT_FOUND", "商品不存在", 404);
        }
        if (!List.of(allowed).contains(String.valueOf(product.get("status")))) {
            throw new ApiException("CONFLICT", "当前状态 " + product.get("status") + " 不允许该操作", 409);
        }
        store.setProductStatus(id, status, rejectReason);
        String action = switch (status) {
            case "approved" -> "product.approve";
            case "rejected" -> "product.reject";
            case "offline" -> "product.offline";
            default -> "product." + status;
        };
        store.writeLog(admin, action, "product", String.valueOf(id));
        dropProductCache(id);
        events.publish(id, status);
        return Map.of("data", Map.of("product", store.productView(store.product(id), true)));
    }

    private void dropProductCache(long productId) {
        cache.invalidate("product:" + productId);
        for (String name : store.categoriesOf(productId)) {
            cache.invalidate("price:" + name);
        }
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
        return user;
    }

    private Map<String, Object> requirePermission(HttpServletRequest request, String permission) {
        Map<String, Object> user = require(request);
        if (!store.hasPermission(MarketStore.num(user.get("id")), permission)) {
            throw new ApiException("AUTH_FORBIDDEN", "没有执行该操作的权限", 403);
        }
        return user;
    }

    private static boolean validPassword(String password) {
        return password.length() >= 8 && password.length() <= 128 && password.matches(".*[A-Za-z].*") && password.matches(".*\\d.*");
    }

    private static String phoneOrNull(Object raw) {
        if (raw == null || String.valueOf(raw).isBlank()) {
            return null;
        }
        String phone = PhoneCipher.normalize(String.valueOf(raw));
        if (phone == null) {
            throw new ApiException("VALIDATION_ERROR", "手机号格式不正确", 422);
        }
        return phone;
    }

    private static Map<String, Object> ok(Object data) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("code", 0);
        body.put("message", "ok");
        body.put("data", data);
        return body;
    }

    private static Map<String, Object> paged(Object data, int page, int pageSize, int total) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("data", data);
        body.put("pagination", Map.of("page", page, "page_size", pageSize, "total", total));
        return body;
    }
}
