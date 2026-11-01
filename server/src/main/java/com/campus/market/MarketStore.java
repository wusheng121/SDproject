package com.campus.market;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Repository
public class MarketStore {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final List<String> CONDITIONS = List.of("全新", "九五新", "九成新", "八成新", "七成新");
    private final JdbcTemplate jdbc;
    private final PhoneCipher phones;

    public MarketStore(JdbcTemplate jdbc, PhoneCipher phones) {
        this.jdbc = jdbc;
        this.phones = phones;
    }

    public Map<String, Object> findUser(String identifier) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT * FROM users WHERE username = ? OR email_normalized = ? LIMIT 1",
                identifier, identifier.toLowerCase());
        return rows.isEmpty() ? null : rows.get(0);
    }

    public Map<String, Object> findUser(long id) {
        List<Map<String, Object>> rows = jdbc.queryForList("SELECT * FROM users WHERE id = ?", id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    public boolean phoneTaken(String phoneHash) {
        if (phoneHash == null) {
            return false;
        }
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM users WHERE phone_hash = ?", Integer.class, phoneHash);
        return count != null && count > 0;
    }

    @Transactional
    public long register(String username, String email, String passwordHash, String phoneCipher, String phoneHash, String roleName) {
        jdbc.update("""
                INSERT INTO users
                (username, email, email_normalized, password_hash, phone_ciphertext, phone_hash, user_type, failed_login_count, is_active, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1, 1, ?, ?)
                """, username, email, email, passwordHash, phoneCipher, phoneHash, roleName, now(), now());
        long userId = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        grantRole(userId, roleName);
        if ("admin".equals(roleName)) {
            grantRole(userId, "normal_user");
        }
        return userId;
    }

    private void grantRole(long userId, String roleName) {
        Long roleId = jdbc.queryForObject("SELECT id FROM roles WHERE name = ?", Long.class, roleName);
        if (roleId == null) {
            throw new ApiException("VALIDATION_ERROR", "所选身份不存在", 422);
        }
        jdbc.update("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", userId, roleId);
    }

    public String issueEmailToken(long userId) {
        String raw = phones.opaqueToken();
        jdbc.update("""
                INSERT INTO email_verification_tokens (user_id, token_hash, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """, userId, Tokens.sha256(raw), LocalDateTime.now().plusHours(24).format(STAMP), now());
        return raw;
    }

    public String issueResetToken(long userId) {
        String raw = phones.opaqueToken();
        jdbc.update("""
                INSERT INTO password_reset_tokens (user_id, token_hash, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """, userId, Tokens.sha256(raw), LocalDateTime.now().plusMinutes(30).format(STAMP), now());
        return raw;
    }

    @Transactional
    public boolean verifyEmail(String rawToken) {
        Map<String, Object> row = unusedToken("email_verification_tokens", rawToken);
        if (row == null) {
            return false;
        }
        jdbc.update("UPDATE email_verification_tokens SET used_at = ? WHERE id = ?", now(), num(row.get("id")));
        jdbc.update("UPDATE users SET email_verified_at = ?, updated_at = ? WHERE id = ?", now(), now(), num(row.get("user_id")));
        return true;
    }

    @Transactional
    public boolean resetPassword(String rawToken, String passwordHash) {
        Map<String, Object> row = unusedToken("password_reset_tokens", rawToken);
        if (row == null) {
            return false;
        }
        long userId = num(row.get("user_id"));
        jdbc.update("UPDATE password_reset_tokens SET used_at = ? WHERE id = ?", now(), num(row.get("id")));
        jdbc.update("UPDATE users SET password_hash = ?, password_changed_at = ?, updated_at = ? WHERE id = ?",
                passwordHash, now(), now(), userId);
        jdbc.update("UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", now(), userId);
        return true;
    }

    private Map<String, Object> unusedToken(String table, String rawToken) {
        if (rawToken == null || rawToken.isBlank()) {
            return null;
        }
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT * FROM " + table + " WHERE token_hash = ? AND used_at IS NULL",
                Tokens.sha256(rawToken));
        if (rows.isEmpty()) {
            return null;
        }
        LocalDateTime expires = parseStamp(rows.get(0).get("expires_at"));
        if (expires == null || !expires.isAfter(LocalDateTime.now())) {
            return null;
        }
        return rows.get(0);
    }

    public Map<String, Object> userPublic(Map<String, Object> user, boolean permissions) {
        long id = num(user.get("id"));
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("id", id);
        data.put("username", user.get("username"));
        data.put("email", user.get("email"));
        data.put("user_type", user.get("user_type"));
        data.put("phone", PhoneCipher.mask(phones.decrypt(text(user.get("phone_ciphertext")))));
        data.put("email_verified", user.get("email_verified_at") != null);
        data.put("is_active", flag(user.get("is_active")));
        data.put("preferred_categories", split(str(user.get("preferred_categories"))));
        data.put("roles", roles(id));
        data.put("created_at", text(user.get("created_at")));
        if (permissions) {
            data.put("permissions", permissionsForRole(id, String.valueOf(user.get("user_type"))));
        }
        return data;
    }

    public List<String> roles(long userId) {
        return jdbc.queryForList(
                "SELECT r.name FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = ? ORDER BY r.name",
                String.class, userId);
    }

    public List<String> permissions(long userId) {
        return jdbc.queryForList("""
                SELECT DISTINCT p.name
                FROM user_roles ur
                JOIN role_permissions rp ON rp.role_id = ur.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE ur.user_id = ?
                ORDER BY p.name
                """, String.class, userId);
    }

    public boolean hasPermission(long userId, String permission, String roleName) {
        Integer count = jdbc.queryForObject("""
                SELECT COUNT(*)
                FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                JOIN role_permissions rp ON rp.role_id = r.id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE ur.user_id = ? AND r.name = ? AND p.name = ?
                """, Integer.class, userId, roleName, permission);
        return count != null && count > 0;
    }

    public List<String> permissionsForRole(long userId, String roleName) {
        return jdbc.queryForList("""
                SELECT DISTINCT p.name
                FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                JOIN role_permissions rp ON rp.role_id = r.id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE ur.user_id = ? AND r.name = ?
                ORDER BY p.name
                """, String.class, userId, roleName);
    }

    public void setLoginRole(long userId, String roleName) {
        jdbc.update("UPDATE users SET user_type = ?, updated_at = ? WHERE id = ?", roleName, now(), userId);
    }

    public void resetLogin(long userId) {
        jdbc.update("UPDATE users SET failed_login_count = 0, locked_until = NULL, last_login_at = ? WHERE id = ?",
                now(), userId);
    }

    public void recordLoginFailure(Map<String, Object> user) {
        int failed = (int) num(user.get("failed_login_count")) + 1;
        String locked = failed >= 5 ? LocalDateTime.now().plusMinutes(15).format(STAMP) : null;
        jdbc.update("UPDATE users SET failed_login_count = ?, locked_until = ? WHERE id = ?",
                failed, locked, num(user.get("id")));
    }

    public String createSession(long userId) {
        String raw = UUID.randomUUID() + "." + UUID.randomUUID();
        jdbc.update("""
                INSERT INTO auth_sessions
                (user_id, refresh_token_hash, family_id, expires_at, ip, user_agent, created_at)
                VALUES (?, ?, ?, ?, '', '', ?)
                """, userId, Tokens.sha256(raw), UUID.randomUUID().toString(),
                LocalDateTime.now().plusDays(30).format(STAMP), now());
        return raw;
    }

    public Long rotateSession(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT * FROM auth_sessions WHERE refresh_token_hash = ?", Tokens.sha256(raw));
        if (rows.isEmpty() || rows.get(0).get("revoked_at") != null) {
            return null;
        }
        long userId = num(rows.get(0).get("user_id"));
        jdbc.update("UPDATE auth_sessions SET revoked_at = ?, last_used_at = ? WHERE id = ?",
                now(), now(), num(rows.get(0).get("id")));
        return userId;
    }

    public void revokeSession(String raw) {
        if (raw == null) {
            return;
        }
        jdbc.update("UPDATE auth_sessions SET revoked_at = ? WHERE refresh_token_hash = ? AND revoked_at IS NULL",
                now(), Tokens.sha256(raw));
    }

    public List<Map<String, Object>> listProducts(String category, String q, String minCondition, Double minPrice, Double maxPrice, String sort, int page, int pageSize) {
        StringBuilder sql = new StringBuilder("SELECT p.* FROM products p WHERE p.status = 'approved'");
        List<Object> args = new ArrayList<>();
        appendFilters(sql, args, category, q, minCondition, minPrice, maxPrice);
        sql.append(switch (sort == null ? "" : sort) {
            case "price_asc" -> " ORDER BY p.price ASC";
            case "price_desc" -> " ORDER BY p.price DESC";
            case "new" -> " ORDER BY p.created_at DESC";
            default -> " ORDER BY p.created_at DESC";
        });
        sql.append(" LIMIT ? OFFSET ?");
        args.add(pageSize);
        args.add((page - 1) * pageSize);
        return jdbc.queryForList(sql.toString(), args.toArray());
    }

    public int countProducts(String category, String q, String minCondition, Double minPrice, Double maxPrice) {
        StringBuilder sql = new StringBuilder("SELECT COUNT(*) FROM products p WHERE p.status = 'approved'");
        List<Object> args = new ArrayList<>();
        appendFilters(sql, args, category, q, minCondition, minPrice, maxPrice);
        Integer count = jdbc.queryForObject(sql.toString(), Integer.class, args.toArray());
        return count == null ? 0 : count;
    }

    public List<Map<String, Object>> listProductsByIds(List<Long> ids, String category, String minCondition, Double minPrice, Double maxPrice) {
        if (ids == null || ids.isEmpty()) {
            return List.of();
        }
        StringBuilder sql = new StringBuilder("SELECT p.* FROM products p WHERE p.status = 'approved' AND p.id IN (");
        sql.append(String.join(",", ids.stream().map(id -> "?").toList())).append(")");
        List<Object> args = new ArrayList<>(ids);
        appendFilters(sql, args, category, null, minCondition, minPrice, maxPrice);
        Map<Long, Map<String, Object>> byId = new HashMap<>();
        for (Map<String, Object> row : jdbc.queryForList(sql.toString(), args.toArray())) {
            byId.put(num(row.get("id")), row);
        }
        List<Map<String, Object>> ordered = new ArrayList<>();
        for (Long id : ids) {
            Map<String, Object> row = byId.get(id);
            if (row != null) {
                ordered.add(row);
            }
        }
        return ordered;
    }

    public List<Map<String, Object>> allProducts() {
        return jdbc.queryForList("SELECT * FROM products");
    }

    public List<Map<String, Object>> rankForUser(long userId, List<Map<String, Object>> rows) {
        if (rows.size() < 2) {
            return rows;
        }
        Map<String, Object> user = findUser(userId);
        Set<String> preferred = new HashSet<>();
        if (user != null) {
            preferred.addAll(split(str(user.get("preferred_categories"))));
        }
        Map<String, Integer> weights = new HashMap<>();
        for (Map<String, Object> event : jdbc.queryForList("""
                SELECT c.name AS category_name, b.behavior_type
                FROM behavior_events b
                JOIN product_categories pc ON pc.product_id = b.product_id
                JOIN categories c ON c.id = pc.category_id
                WHERE b.user_id = ?
                """, userId)) {
            int weight = switch (str(event.get("behavior_type"))) {
                case "view" -> 1;
                case "favorite" -> 3;
                case "add_cart" -> 4;
                case "order" -> 5;
                case "review" -> 2;
                default -> 0;
            };
            String name = str(event.get("category_name"));
            if (weight > 0 && !name.isBlank()) {
                weights.merge(name, weight, Integer::sum);
            }
        }
        if (preferred.isEmpty() && weights.isEmpty()) {
            return rows;
        }
        List<Map<String, Object>> ranked = new ArrayList<>(rows);
        ranked.sort((left, right) -> Double.compare(
                interestScore(right, preferred, weights),
                interestScore(left, preferred, weights)));
        return ranked;
    }

    private double interestScore(Map<String, Object> product, Set<String> preferred, Map<String, Integer> weights) {
        double score = 0;
        for (String name : categoriesOf(num(product.get("id")))) {
            if (preferred.contains(name)) {
                score += 70;
            }
            score += weights.getOrDefault(name, 0) * 3.0;
        }
        return score;
    }

    static void appendFilters(StringBuilder sql, List<Object> args, String category, String q, String minCondition, Double minPrice, Double maxPrice) {
        if (q != null && !q.isBlank()) {
            sql.append(" AND p.name LIKE ?");
            args.add("%" + q + "%");
        }
        if (category != null && !category.isBlank()) {
            sql.append(" AND EXISTS (SELECT 1 FROM product_categories pc JOIN categories c ON c.id = pc.category_id WHERE pc.product_id = p.id AND c.name = ?)");
            args.add(category);
        }
        List<String> grades = gradesAtLeast(minCondition);
        if (!grades.isEmpty()) {
            sql.append(" AND p.condition_level IN (").append(String.join(",", grades.stream().map(item -> "?").toList())).append(")");
            args.addAll(grades);
        }
        if (minPrice != null) {
            sql.append(" AND p.price >= ?");
            args.add(minPrice);
        }
        if (maxPrice != null) {
            sql.append(" AND p.price <= ?");
            args.add(maxPrice);
        }
    }

    private static void checkProductText(String name, String category, String condition, double price, String description) {
        if (name.isBlank() || name.length() > 80 || name.indexOf('<') >= 0 || category.isBlank() || !CONDITIONS.contains(condition) || price <= 0 || price > 100000) {
            throw new ApiException("VALIDATION_ERROR", "请填写 1-80 字的名称、有效品类、1 到 100000 的价格和成色", 400);
        }
        if (description.length() > 1000 || description.indexOf('<') >= 0) {
            throw new ApiException("VALIDATION_ERROR", "商品描述最多 1000 字，且不能包含 HTML 标签", 400);
        }
    }

    private static List<String> gradesAtLeast(String minimum) {
        if (minimum == null || minimum.isBlank()) {
            return List.of();
        }
        List<String> ordered = List.of("七成新", "八成新", "九成新", "九五新", "全新");
        int index = ordered.indexOf(minimum);
        if (index < 0) {
            return List.of();
        }
        return ordered.subList(index, ordered.size());
    }

    public Map<String, Object> product(long id) {
        List<Map<String, Object>> rows = jdbc.queryForList("SELECT * FROM products WHERE id = ?", id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    public List<String> categoriesOf(long productId) {
        return jdbc.queryForList("""
                SELECT c.name FROM product_categories pc
                JOIN categories c ON c.id = pc.category_id
                WHERE pc.product_id = ?
                """, String.class, productId);
    }

    public List<String> allCategories() {
        return jdbc.queryForList("SELECT name FROM categories ORDER BY name", String.class);
    }

    public Map<String, Object> productView(Map<String, Object> product, boolean detail) {
        long id = num(product.get("id"));
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("id", id);
        data.put("name", product.get("name"));
        data.put("price", product.get("price"));
        data.put("condition", product.get("condition_level"));
        data.put("image_url", product.get("image_url"));
        data.put("status", product.get("status"));
        data.put("reject_reason", product.get("reject_reason") == null ? "" : String.valueOf(product.get("reject_reason")));
        data.put("categories", categoriesOf(id));
        data.put("created_at", text(product.get("created_at")));
        if (detail) {
            data.put("description", product.get("description"));
            data.put("brand", product.get("brand"));
            data.put("has_notes", flag(product.get("has_notes")));
            data.put("defect_description", product.get("defect_description"));
            data.put("trade_method", product.get("trade_method"));
            data.put("trade_location", product.get("trade_location"));
            Map<String, Object> seller = findUser(num(product.get("seller_id")));
            data.put("seller", seller == null ? null : Map.of(
                    "id", num(seller.get("id")),
                    "username", seller.get("username")));
        }
        return data;
    }

    @Transactional
    public long publish(long sellerId, Map<String, Object> body) {
        String name = str(body.get("name"));
        String category = str(body.get("category"));
        String condition = str(body.get("condition"));
        double price = body.get("price") instanceof Number n ? n.doubleValue() : Double.parseDouble(str(body.get("price")));
        checkProductText(name, category, condition, price, str(body.get("description")));
        List<Long> categoryIds = jdbc.queryForList("SELECT id FROM categories WHERE name = ?", Long.class, category);
        if (categoryIds.isEmpty()) {
            throw new ApiException("VALIDATION_ERROR", "商品品类不存在", 400);
        }
        jdbc.update("""
                INSERT INTO products
                (name, description, price, condition_level, brand, has_notes, defect_description,
                 trade_method, trade_location, image_url, ai_category, ai_condition, status, seller_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                """,
                name, str(body.get("description")), price, condition, emptyToNull(str(body.get("brand"))),
                bool(body.get("has_notes")) ? 1 : 0, emptyToNull(str(body.get("defect_description"))),
                emptyToNull(str(body.get("trade_method"))), emptyToNull(str(body.get("trade_location"))),
                emptyToNull(str(body.get("image_url"))), emptyToNull(str(body.get("ai_category"))),
                emptyToNull(str(body.get("ai_condition"))), sellerId, now(), now());
        long productId = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        jdbc.update("INSERT INTO product_categories (product_id, category_id) VALUES (?, ?)", productId, categoryIds.get(0));
        return productId;
    }

    public List<Map<String, Object>> myProducts(long sellerId) {
        return jdbc.queryForList(
                "SELECT * FROM products WHERE seller_id = ? ORDER BY created_at DESC", sellerId);
    }

    @Transactional
    public Map<String, Object> updateOwnProduct(long sellerId, long productId, Map<String, Object> body) {
        Map<String, Object> product = product(productId);
        if (product == null) {
            throw new ApiException("NOT_FOUND", "商品不存在", 404);
        }
        if (num(product.get("seller_id")) != sellerId) {
            throw new ApiException("AUTH_FORBIDDEN", "只能编辑自己发布的商品", 403);
        }
        if ("sold".equals(product.get("status")) || "offline".equals(product.get("status"))) {
            throw new ApiException("CONFLICT", "已下架或已售出的商品不能编辑", 409);
        }
        String name = str(body.get("name"));
        String category = str(body.get("category"));
        String condition = str(body.get("condition"));
        double price = body.get("price") instanceof Number n ? n.doubleValue() : Double.parseDouble(str(body.get("price")));
        checkProductText(name, category, condition, price, str(body.get("description")));
        List<Long> categoryIds = jdbc.queryForList("SELECT id FROM categories WHERE name = ?", Long.class, category);
        if (categoryIds.isEmpty()) {
            throw new ApiException("VALIDATION_ERROR", "商品品类不存在", 400);
        }
        jdbc.update("""
                UPDATE products
                SET name = ?, description = ?, price = ?, condition_level = ?, brand = ?, has_notes = ?,
                    defect_description = ?, trade_method = ?, trade_location = ?, image_url = ?, updated_at = ?
                WHERE id = ?
                """,
                name, str(body.get("description")), price, condition, emptyToNull(str(body.get("brand"))),
                bool(body.get("has_notes")) ? 1 : 0, emptyToNull(str(body.get("defect_description"))),
                emptyToNull(str(body.get("trade_method"))), emptyToNull(str(body.get("trade_location"))),
                imageUrl(body, product), now(), productId);
        jdbc.update("DELETE FROM product_categories WHERE product_id = ?", productId);
        jdbc.update("INSERT INTO product_categories (product_id, category_id) VALUES (?, ?)", productId, categoryIds.get(0));
        return productView(this.product(productId), true);
    }

    @Transactional
    public Map<String, Object> offlineOwnProduct(long sellerId, long productId) {
        Map<String, Object> product = product(productId);
        if (product == null) {
            throw new ApiException("NOT_FOUND", "商品不存在", 404);
        }
        if (num(product.get("seller_id")) != sellerId) {
            throw new ApiException("AUTH_FORBIDDEN", "只能下架自己发布的商品", 403);
        }
        if (!"approved".equals(String.valueOf(product.get("status")))) {
            throw new ApiException("CONFLICT", "只有正在出售的商品可以下架", 409);
        }
        jdbc.update("UPDATE products SET status = 'offline', updated_at = ? WHERE id = ?", now(), productId);
        return productView(this.product(productId), true);
    }

    @Transactional
    public void deleteOwnProduct(long sellerId, long productId) {
        Map<String, Object> product = product(productId);
        if (product == null) {
            throw new ApiException("NOT_FOUND", "商品不存在", 404);
        }
        if (num(product.get("seller_id")) != sellerId) {
            throw new ApiException("AUTH_FORBIDDEN", "只能删除自己发布的商品", 403);
        }
        if (!List.of("pending", "rejected", "offline").contains(String.valueOf(product.get("status")))) {
            throw new ApiException("CONFLICT", "只有待审核、被拒绝或已下架的商品可以删除", 409);
        }
        Integer orders = jdbc.queryForObject(
                "SELECT COUNT(*) FROM order_items WHERE product_id = ?", Integer.class, productId);
        if (orders != null && orders > 0) {
            throw new ApiException("CONFLICT", "这件商品已经有订单，不能删除", 409);
        }
        jdbc.update("DELETE FROM products WHERE id = ?", productId);
    }

    public List<Map<String, Object>> cart(long userId) {
        return jdbc.queryForList("""
                SELECT c.id, c.product_id, c.quantity, p.name, p.price, p.condition_level, p.image_url, p.status,
                       u.id AS seller_id, u.username AS seller_name
                FROM carts c
                JOIN products p ON p.id = c.product_id
                JOIN users u ON u.id = p.seller_id
                WHERE c.user_id = ?
                ORDER BY c.created_at DESC
                """, userId);
    }

    @Transactional
    public boolean addCart(long userId, long productId) {
        Map<String, Object> product = product(productId);
        if (product == null) {
            throw new ApiException("NOT_FOUND", "商品不存在", 404);
        }
        if (num(product.get("seller_id")) == userId) {
            throw new ApiException("TRADE_OWN_PRODUCT", "不能购买自己发布的商品", 403);
        }
        if (!"approved".equals(product.get("status"))) {
            throw new ApiException("TRADE_UNAVAILABLE", "商品未上架或已售出", 409);
        }
        Integer pending = jdbc.queryForObject("""
                SELECT COUNT(*) FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE oi.product_id = ? AND o.status = 'pending'
                """, Integer.class, productId);
        if (pending != null && pending > 0) {
            throw new ApiException("TRADE_UNAVAILABLE", "该商品已有待支付订单", 409);
        }
        Integer existing = jdbc.queryForObject(
                "SELECT COUNT(*) FROM carts WHERE user_id = ? AND product_id = ?", Integer.class, userId, productId);
        if (existing != null && existing > 0) {
            return false;
        }
        jdbc.update("INSERT INTO carts (user_id, product_id, quantity, created_at) VALUES (?, ?, 1, ?)",
                userId, productId, now());
        Integer recorded = jdbc.queryForObject("""
                SELECT COUNT(*) FROM user_behaviors
                WHERE user_id = ? AND product_id = ? AND behavior_type = 'add_cart'
                """, Integer.class, userId, productId);
        if (recorded == null || recorded == 0) {
            jdbc.update("""
                    INSERT INTO user_behaviors (user_id, product_id, behavior_type, value, created_at, updated_at)
                    VALUES (?, ?, 'add_cart', 1, ?, ?)
                    """, userId, productId, now(), now());
            jdbc.update("""
                    INSERT INTO behavior_events (user_id, product_id, behavior_type, created_at)
                    VALUES (?, ?, 'add_cart', ?)
                    """, userId, productId, now());
        }
        return true;
    }

    public void removeCart(long userId, long productId) {
        int rows = jdbc.update("DELETE FROM carts WHERE user_id = ? AND product_id = ?", userId, productId);
        if (rows == 0) {
            throw new ApiException("NOT_FOUND", "购物车中没有该商品", 404);
        }
    }

    @Transactional
    public Map<String, Object> createOrder(long userId, List<Integer> productIds) {
        List<Map<String, Object>> lines = cart(userId);
        if (productIds != null && !productIds.isEmpty()) {
            lines = lines.stream().filter(row -> productIds.contains((int) num(row.get("product_id")))).toList();
        }
        if (lines.isEmpty()) {
            throw new ApiException("VALIDATION_ERROR", "购物车是空的", 422);
        }
        double total = lines.stream().mapToDouble(row -> ((Number) row.get("price")).doubleValue()).sum();
        jdbc.update("INSERT INTO orders (buyer_id, status, total_amount, created_at, updated_at) VALUES (?, 'pending', ?, ?, ?)",
                userId, total, now(), now());
        long orderId = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        for (Map<String, Object> line : lines) {
            long productId = num(line.get("product_id"));
            jdbc.update("""
                    INSERT INTO order_items (order_id, product_id, quantity, price, created_at)
                    VALUES (?, ?, 1, ?, ?)
                    """, orderId, productId, line.get("price"), now());
            jdbc.update("DELETE FROM carts WHERE user_id = ? AND product_id = ?", userId, productId);
        }
        return order(userId, orderId);
    }

    public List<Map<String, Object>> orders(long userId) {
        List<Long> ids = jdbc.queryForList(
                "SELECT id FROM orders WHERE buyer_id = ? ORDER BY created_at DESC", Long.class, userId);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Long id : ids) {
            result.add(order(userId, id));
        }
        return result;
    }

    public Map<String, Object> order(long userId, long orderId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT * FROM orders WHERE id = ? AND buyer_id = ?", orderId, userId);
        if (rows.isEmpty()) {
            throw new ApiException("NOT_FOUND", "订单不存在", 404);
        }
        Map<String, Object> order = rows.get(0);
        List<Map<String, Object>> items = jdbc.queryForList("""
                SELECT oi.*, p.name, p.image_url
                FROM order_items oi
                LEFT JOIN products p ON p.id = oi.product_id
                WHERE oi.order_id = ?
                """, orderId);
        List<Map<String, Object>> view = new ArrayList<>();
        for (Map<String, Object> item : items) {
            List<Map<String, Object>> reviewRows = jdbc.queryForList("""
                    SELECT score, comment FROM reviews
                    WHERE order_id = ? AND user_id = ? AND product_id = ?
                    ORDER BY created_at DESC LIMIT 1
                    """, orderId, userId, num(item.get("product_id")));
            Map<String, Object> review = null;
            if (!reviewRows.isEmpty()) {
                review = new LinkedHashMap<>();
                review.put("score", reviewRows.get(0).get("score"));
                review.put("comment", reviewRows.get(0).get("comment") == null ? "" : reviewRows.get(0).get("comment"));
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", num(item.get("id")));
            row.put("product_id", num(item.get("product_id")));
            row.put("name", item.get("name") == null ? "商品已删除" : item.get("name"));
            row.put("image_url", item.get("image_url"));
            row.put("quantity", num(item.get("quantity")));
            row.put("price", item.get("price"));
            row.put("line_amount", ((Number) item.get("price")).doubleValue() * num(item.get("quantity")));
            row.put("reviewed", review != null);
            row.put("review", review);
            view.add(row);
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("id", num(order.get("id")));
        data.put("status", order.get("status"));
        data.put("total_amount", order.get("total_amount"));
        data.put("created_at", text(order.get("created_at")));
        data.put("items", view);
        return data;
    }

    @Transactional
    public Map<String, Object> pay(long userId, long orderId) {
        Map<String, Object> order = order(userId, orderId);
        if (!"pending".equals(order.get("status"))) {
            throw new ApiException("ORDER_STATE", "只有待支付订单可以支付", 409);
        }
        jdbc.update("UPDATE orders SET status = 'paid', updated_at = ? WHERE id = ?", now(), orderId);
        List<Map<String, Object>> items = (List<Map<String, Object>>) order.get("items");
        for (Map<String, Object> item : items) {
            long productId = num(item.get("product_id"));
            jdbc.update("UPDATE products SET status = 'sold', updated_at = ? WHERE id = ?", now(), productId);
            jdbc.update("DELETE FROM carts WHERE product_id = ?", productId);
        }
        return order(userId, orderId);
    }

    @Transactional
    public Map<String, Object> cancel(long userId, long orderId) {
        Map<String, Object> order = order(userId, orderId);
        if (!"pending".equals(order.get("status"))) {
            throw new ApiException("ORDER_STATE", "只有待支付订单可以取消", 409);
        }
        jdbc.update("UPDATE orders SET status = 'cancelled', updated_at = ? WHERE id = ?", now(), orderId);
        for (Map<String, Object> item : (List<Map<String, Object>>) order.get("items")) {
            long productId = num(item.get("product_id"));
            Map<String, Object> product = product(productId);
            if (product != null && "approved".equals(product.get("status"))) {
                Integer exists = jdbc.queryForObject(
                        "SELECT COUNT(*) FROM carts WHERE user_id = ? AND product_id = ?",
                        Integer.class, userId, productId);
                if (exists == null || exists == 0) {
                    jdbc.update("INSERT INTO carts (user_id, product_id, quantity, created_at) VALUES (?, ?, 1, ?)",
                            userId, productId, now());
                }
            }
        }
        return order(userId, orderId);
    }

    public void review(long userId, long orderId, long productId, int score, String comment) {
        Map<String, Object> order = order(userId, orderId);
        if (!"paid".equals(order.get("status"))) {
            throw new ApiException("ORDER_STATE", "支付完成后才能评价", 409);
        }
        if (score < 1 || score > 5) {
            throw new ApiException("VALIDATION_ERROR", "评分必须是 1 到 5 的整数", 422);
        }
        if (comment.length() > 500 || comment.indexOf('<') >= 0) {
            throw new ApiException("VALIDATION_ERROR", "评价最多 500 字，且不能包含 HTML 标签", 422);
        }
        Integer item = jdbc.queryForObject(
                "SELECT COUNT(*) FROM order_items WHERE order_id = ? AND product_id = ?",
                Integer.class, orderId, productId);
        if (item == null || item == 0) {
            throw new ApiException("NOT_FOUND", "订单中没有该商品", 404);
        }
        Integer exists = jdbc.queryForObject("""
                SELECT COUNT(*) FROM reviews WHERE user_id = ? AND product_id = ? AND order_id = ?
                """, Integer.class, userId, productId, orderId);
        if (exists != null && exists > 0) {
            throw new ApiException("REVIEW_EXISTS", "该商品已经评价过", 409);
        }
        jdbc.update("""
                INSERT INTO reviews (user_id, product_id, order_id, score, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, userId, productId, orderId, score, comment, now());
    }

    public List<Map<String, Object>> productReviews(long productId) {
        if (product(productId) == null) {
            throw new ApiException("NOT_FOUND", "商品不存在", 404);
        }
        return jdbc.query("""
                SELECT r.id, r.order_id, r.product_id, r.score, r.comment, r.created_at, u.id AS user_id, u.username
                FROM reviews r
                LEFT JOIN users u ON u.id = r.user_id
                WHERE r.product_id = ?
                ORDER BY r.created_at DESC
                """, (rs, rowNum) -> {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", rs.getLong("id"));
            item.put("order_id", rs.getObject("order_id"));
            item.put("product_id", rs.getLong("product_id"));
            item.put("score", rs.getInt("score"));
            item.put("comment", rs.getString("comment") == null ? "" : rs.getString("comment"));
            item.put("created_at", rs.getTimestamp("created_at"));
            if (rs.getObject("user_id") == null) {
                item.put("user", null);
            } else {
                Map<String, Object> user = new LinkedHashMap<>();
                user.put("id", rs.getLong("user_id"));
                user.put("username", rs.getString("username"));
                item.put("user", user);
            }
            return item;
        }, productId);
    }

    public void savePreferences(long userId, List<String> categories) {
        String value = String.join(",", categories.stream().map(String::trim).filter(s -> !s.isBlank()).toList());
        jdbc.update("UPDATE users SET preferred_categories = ?, updated_at = ? WHERE id = ?", value, now(), userId);
    }

    @Transactional
    public boolean updateProfile(long userId, String username, boolean changePhone, String phoneCipher, String phoneHash, String email) {
        if (username != null) {
            Integer taken = jdbc.queryForObject(
                    "SELECT COUNT(*) FROM users WHERE username = ? AND id <> ?", Integer.class, username, userId);
            if (taken != null && taken > 0) {
                throw new ApiException("AUTH_USERNAME_EXISTS", "用户名已存在", 409);
            }
            jdbc.update("UPDATE users SET username = ? WHERE id = ?", username, userId);
        }
        boolean emailChanged = false;
        if (email != null) {
            Integer taken = jdbc.queryForObject(
                    "SELECT COUNT(*) FROM users WHERE email_normalized = ? AND id <> ?", Integer.class, email, userId);
            if (taken != null && taken > 0) {
                throw new ApiException("AUTH_EMAIL_EXISTS", "邮箱已存在", 409);
            }
            Integer same = jdbc.queryForObject(
                    "SELECT COUNT(*) FROM users WHERE id = ? AND email_normalized = ?", Integer.class, userId, email);
            if (same == null || same == 0) {
                jdbc.update("UPDATE users SET email = ?, email_normalized = ?, email_verified_at = NULL WHERE id = ?",
                        email, email, userId);
                emailChanged = true;
            }
        }
        if (changePhone) {
            if (phoneHash != null) {
                Integer taken = jdbc.queryForObject(
                        "SELECT COUNT(*) FROM users WHERE phone_hash = ? AND id <> ?", Integer.class, phoneHash, userId);
                if (taken != null && taken > 0) {
                    throw new ApiException("AUTH_PHONE_EXISTS", "手机号已被使用", 409);
                }
            }
            jdbc.update("UPDATE users SET phone_ciphertext = ?, phone_hash = ? WHERE id = ?", phoneCipher, phoneHash, userId);
        }
        jdbc.update("UPDATE users SET version = COALESCE(version, 0) + 1, updated_at = ? WHERE id = ?", now(), userId);
        return emailChanged;
    }

    @Transactional
    public List<Long> closeAccount(long userId) {
        List<Long> listingIds = jdbc.queryForList(
                "SELECT id FROM products WHERE seller_id = ? AND status IN ('pending', 'approved', 'rejected')",
                Long.class, userId);
        String stamp = now();
        jdbc.update("""
                UPDATE products SET status = 'offline', updated_at = ?
                WHERE seller_id = ? AND status IN ('pending', 'approved', 'rejected')
                """, stamp, userId);
        jdbc.update("UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", stamp, userId);
        jdbc.update("""
                UPDATE users
                SET username = ?, email = ?, email_normalized = ?, phone_ciphertext = NULL, phone_hash = NULL,
                    is_active = 0, deleted_at = ?, updated_at = ?
                WHERE id = ?
                """, "已注销用户" + userId, "closed-" + userId + "@closed.local", "closed-" + userId + "@closed.local",
                stamp, stamp, userId);
        return listingIds;
    }

    public Map<String, Object> stats(long userId) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("favorites", count("SELECT COUNT(*) FROM user_behaviors WHERE user_id = ? AND behavior_type = 'favorite'", userId));
        data.put("behaviors", count("SELECT COUNT(*) FROM user_behaviors WHERE user_id = ?", userId));
        data.put("products", count("SELECT COUNT(*) FROM products WHERE seller_id = ?", userId));
        data.put("categories", split(str(findUser(userId).get("preferred_categories"))).size());
        return data;
    }

    public void recordBehavior(long userId, long productId, String type, Integer value) {
        Map<String, Object> product = product(productId);
        if (product == null || !"approved".equals(product.get("status"))) {
            throw new ApiException("NOT_FOUND", "商品不存在或未上架", 404);
        }
        if ("favorite".equals(type) && value != null && value == 0) {
            jdbc.update("DELETE FROM user_behaviors WHERE user_id = ? AND product_id = ? AND behavior_type = 'favorite'",
                    userId, productId);
            return;
        }
        Integer exists = jdbc.queryForObject("""
                SELECT COUNT(*) FROM user_behaviors WHERE user_id = ? AND product_id = ? AND behavior_type = ?
                """, Integer.class, userId, productId, type);
        if (exists == null || exists == 0) {
            jdbc.update("""
                    INSERT INTO user_behaviors (user_id, product_id, behavior_type, value, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, userId, productId, type, value == null ? 1 : value, now(), now());
        }
        if ("view".equals(type) || "favorite".equals(type) || "add_cart".equals(type)) {
            jdbc.update("INSERT INTO behavior_events (user_id, product_id, behavior_type, created_at) VALUES (?, ?, ?, ?)",
                    userId, productId, type, now());
        }
    }

    public List<Map<String, Object>> favorites(long userId) {
        List<Long> ids = jdbc.queryForList("""
                SELECT product_id FROM user_behaviors
                WHERE user_id = ? AND behavior_type = 'favorite'
                ORDER BY created_at DESC
                """, Long.class, userId);
        List<Map<String, Object>> items = new ArrayList<>();
        for (Long id : ids) {
            Map<String, Object> product = product(id);
            if (product != null && "approved".equals(product.get("status"))) {
                items.add(productView(product, false));
            }
        }
        return items;
    }

    public boolean favorited(long userId, long productId) {
        Integer count = jdbc.queryForObject("""
                SELECT COUNT(*) FROM user_behaviors
                WHERE user_id = ? AND product_id = ? AND behavior_type = 'favorite'
                """, Integer.class, userId, productId);
        return count != null && count > 0;
    }

    public List<Map<String, Object>> adminUsers(String keyword, String role, String status, int page, int pageSize) {
        UserQuery query = userQuery(keyword, role, status);
        query.args.add(pageSize);
        query.args.add((page - 1) * pageSize);
        return jdbc.queryForList(query.sql + " ORDER BY u.id DESC LIMIT ? OFFSET ?", query.args.toArray());
    }

    public int countUsers(String keyword, String role, String status) {
        UserQuery query = userQuery(keyword, role, status);
        Integer count = jdbc.queryForObject("SELECT COUNT(DISTINCT u.id) FROM users u" + query.fromWhere, Integer.class, query.args.toArray());
        return count == null ? 0 : count;
    }

    @Transactional
    public Map<String, Object> setUserRoles(long actorId, String actorName, long userId, List<String> names) {
        Map<String, Object> user = findUser(userId);
        if (user == null) {
            throw new ApiException("NOT_FOUND", "用户不存在", 404);
        }
        if (names == null || names.isEmpty()) {
            throw new ApiException("VALIDATION_ERROR", "roles 必须是非空数组", 422);
        }
        List<String> before = roles(userId);
        List<Long> roleIds = new ArrayList<>();
        for (String name : names) {
            List<Long> found = jdbc.queryForList("SELECT id FROM roles WHERE name = ?", Long.class, name);
            if (found.isEmpty()) {
                throw new ApiException("VALIDATION_ERROR", "包含不存在的角色", 422);
            }
            roleIds.add(found.get(0));
        }
        jdbc.update("DELETE FROM user_roles WHERE user_id = ?", userId);
        for (Long roleId : roleIds) {
            jdbc.update("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", userId, roleId);
        }
        String userType = names.contains("admin") ? "admin" : names.contains("agent_service") ? "agent_service" : "normal_user";
        jdbc.update("UPDATE users SET user_type = ?, updated_at = ? WHERE id = ?", userType, now(), userId);
        jdbc.update("""
                INSERT INTO operation_logs
                (actor_id, actor_snapshot, action, resource_type, resource_id, before_json, after_json, created_at)
                VALUES (?, ?, 'user.roles.update', 'user', ?, ?, ?, ?)
                """, actorId, actorName, String.valueOf(userId), String.join(",", before), String.join(",", names), now());
        return userPublic(findUser(userId), true);
    }

    private UserQuery userQuery(String keyword, String role, String status) {
        StringBuilder fromWhere = new StringBuilder();
        List<Object> args = new ArrayList<>();
        if (role != null && !role.isBlank()) {
            fromWhere.append(" JOIN user_roles ur ON ur.user_id = u.id JOIN roles r ON r.id = ur.role_id");
        }
        List<String> where = new ArrayList<>();
        where.add("u.deleted_at IS NULL");
        if (keyword != null && !keyword.isBlank()) {
            where.add("(u.username LIKE ? OR u.email LIKE ?)");
            args.add("%" + keyword.trim() + "%");
            args.add("%" + keyword.trim() + "%");
        }
        if (role != null && !role.isBlank()) {
            where.add("r.name = ?");
            args.add(role.trim());
        }
        if ("active".equals(status)) {
            where.add("u.is_active = 1");
        } else if ("banned".equals(status)) {
            where.add("u.is_active = 0");
        }
        if (!where.isEmpty()) {
            fromWhere.append(" WHERE ").append(String.join(" AND ", where));
        }
        UserQuery query = new UserQuery();
        query.fromWhere = fromWhere.toString();
        query.sql = "SELECT DISTINCT u.* FROM users u" + query.fromWhere;
        query.args = args;
        return query;
    }

    private static final class UserQuery {
        private String sql;
        private String fromWhere;
        private List<Object> args;
    }

    public void setActive(long userId, boolean active) {
        jdbc.update("UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?", active ? 1 : 0, now(), userId);
        if (!active) {
            jdbc.update("UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", now(), userId);
        }
    }

    public void writeLog(Map<String, Object> actor, String action, String resourceType, String resourceId) {
        jdbc.update("""
                INSERT INTO operation_logs
                (actor_id, actor_snapshot, action, resource_type, resource_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                num(actor.get("id")), actor.get("username"), action, resourceType, resourceId, now());
    }

    public void setProductStatus(long productId, String status, String rejectReason) {
        if ("rejected".equals(status)) {
            jdbc.update("UPDATE products SET status = ?, reject_reason = ?, updated_at = ? WHERE id = ?", status, rejectReason, now(), productId);
            return;
        }
        jdbc.update("UPDATE products SET status = ?, reject_reason = NULL, updated_at = ? WHERE id = ?", status, now(), productId);
    }

    public List<Map<String, Object>> adminProducts(String status, int page, int pageSize) {
        if (status == null || status.isBlank()) {
            return jdbc.queryForList(
                    "SELECT * FROM products ORDER BY created_at DESC LIMIT ? OFFSET ?", pageSize, (page - 1) * pageSize);
        }
        return jdbc.queryForList(
                "SELECT * FROM products WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                status, pageSize, (page - 1) * pageSize);
    }

    public int countAdminProducts(String status) {
        if (status == null || status.isBlank()) {
            return count("SELECT COUNT(*) FROM products");
        }
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM products WHERE status = ?", Integer.class, status);
        return count == null ? 0 : count;
    }

    public List<Map<String, Object>> recentBehaviors(long userId) {
        return jdbc.queryForList("""
                SELECT e.id, e.user_id, e.product_id, p.name AS product_name, e.behavior_type, e.created_at
                FROM behavior_events e
                LEFT JOIN products p ON p.id = e.product_id
                WHERE e.user_id = ? AND e.created_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 7 DAY)
                ORDER BY e.created_at DESC
                """, userId);
    }

    public Map<String, Object> adminStats() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("users", Map.of("total", count("SELECT COUNT(*) FROM users WHERE deleted_at IS NULL"), "active", count("SELECT COUNT(*) FROM users WHERE is_active = 1 AND deleted_at IS NULL")));
        data.put("products", Map.of(
                "total", count("SELECT COUNT(*) FROM products"),
                "pending", count("SELECT COUNT(*) FROM products WHERE status = 'pending'"),
                "approved", count("SELECT COUNT(*) FROM products WHERE status = 'approved'")));
        data.put("behaviors", count("SELECT COUNT(*) FROM user_behaviors"));
        data.put("orders", count("SELECT COUNT(*) FROM orders"));
        data.put("behavior_window_days", 7);
        return data;
    }

    public List<Map<String, Object>> logs(String action, String resourceType, int page, int pageSize) {
        LogQuery query = logQuery(action, resourceType);
        query.args.add(pageSize);
        query.args.add((page - 1) * pageSize);
        return jdbc.queryForList(query.sql + " ORDER BY created_at DESC LIMIT ? OFFSET ?", query.args.toArray());
    }

    public int countLogs(String action, String resourceType) {
        LogQuery query = logQuery(action, resourceType);
        String countSql = "SELECT COUNT(*) FROM operation_logs" + query.where;
        Integer count = jdbc.queryForObject(countSql, Integer.class, query.args.toArray());
        return count == null ? 0 : count;
    }

    private LogQuery logQuery(String action, String resourceType) {
        StringBuilder where = new StringBuilder();
        List<Object> args = new ArrayList<>();
        List<String> filters = new ArrayList<>();
        if (action != null && !action.isBlank()) {
            filters.add("action = ?");
            args.add(action.trim());
        }
        if (resourceType != null && !resourceType.isBlank()) {
            filters.add("resource_type = ?");
            args.add(resourceType.trim());
        }
        if (!filters.isEmpty()) {
            where.append(" WHERE ").append(String.join(" AND ", filters));
        }
        LogQuery query = new LogQuery();
        query.sql = """
                SELECT id, actor_id, actor_snapshot AS actor, action, resource_type, resource_id,
                       after_json, ip, trace_id, created_at
                FROM operation_logs
                """ + where;
        query.where = where.toString();
        query.args = args;
        return query;
    }

    private static final class LogQuery {
        private String sql;
        private String where;
        private List<Object> args;
    }

    public Map<String, Object> agentDialogue(String id) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT d.id, d.user_id, u.username, d.messages_json, d.updated_at
                FROM agent_dialogues d
                LEFT JOIN users u ON u.id = d.user_id
                WHERE d.id = ?
                """, id);
        if (rows.isEmpty()) {
            return null;
        }
        Map<String, Object> row = rows.get(0);
        Map<String, Object> dialogue = new LinkedHashMap<>();
        dialogue.put("id", row.get("id"));
        dialogue.put("user_id", row.get("user_id"));
        dialogue.put("username", row.get("username") == null ? "" : row.get("username"));
        Object updated = row.get("updated_at");
        dialogue.put("updated_at", updated instanceof LocalDateTime time ? time.format(STAMP) : updated);
        dialogue.put("messages", readDialogueMessages(row.get("messages_json")));
        return dialogue;
    }

    private List<Map<String, Object>> readDialogueMessages(Object raw) {
        if (raw == null || String.valueOf(raw).isBlank()) {
            return List.of();
        }
        try {
            List<Map<String, Object>> parsed = new ObjectMapper().readValue(String.valueOf(raw), new TypeReference<>() {});
            List<Map<String, Object>> messages = new ArrayList<>();
            for (Map<String, Object> item : parsed) {
                Object role = item.get("role");
                if (!"user".equals(role) && !"assistant".equals(role)) {
                    continue;
                }
                Map<String, Object> message = new LinkedHashMap<>();
                message.put("role", role);
                message.put("content", item.get("content") == null ? "" : item.get("content"));
                if (item.get("filename") != null) {
                    message.put("filename", item.get("filename"));
                }
                if (item.get("engine") != null) {
                    message.put("engine", item.get("engine"));
                }
                if (item.get("items") instanceof List<?> products) {
                    message.put("items", products);
                }
                messages.add(message);
            }
            return messages;
        } catch (Exception ex) {
            return List.of();
        }
    }

    public int count(String sql, Object... args) {
        Integer count = jdbc.queryForObject(sql, Integer.class, args);
        return count == null ? 0 : count;
    }

    public static long num(Object value) {
        return value instanceof Number number ? number.longValue() : Long.parseLong(String.valueOf(value));
    }

    public static boolean flag(Object value) {
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        if (value instanceof Boolean bool) {
            return bool;
        }
        return "1".equals(String.valueOf(value)) || "true".equalsIgnoreCase(String.valueOf(value));
    }

    public static String str(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private static String text(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private static String emptyToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }

    private static String imageUrl(Map<String, Object> body, Map<String, Object> product) {
        if (!body.containsKey("image_url")) {
            return emptyToNull(str(product.get("image_url")));
        }
        String url = emptyToNull(str(body.get("image_url")));
        if (url != null && url.length() > 500) {
            throw new ApiException("VALIDATION_ERROR", "商品图片地址过长", 400);
        }
        return url;
    }

    private static boolean bool(Object value) {
        return flag(value);
    }

    private static List<String> split(String value) {
        if (value == null || value.isBlank()) {
            return List.of();
        }
        List<String> items = new ArrayList<>();
        for (String part : value.split(",")) {
            if (!part.isBlank()) {
                items.add(part.trim());
            }
        }
        return items;
    }

    private static String now() {
        return LocalDateTime.now().format(STAMP);
    }

    private static LocalDateTime parseStamp(Object value) {
        if (value == null) {
            return null;
        }
        String text = String.valueOf(value).replace('T', ' ');
        int dot = text.indexOf('.');
        if (dot >= 0) {
            text = text.substring(0, dot);
        }
        return LocalDateTime.parse(text, STAMP);
    }
}
