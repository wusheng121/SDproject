package com.campus.market;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Component
public class SellerMessages {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private final JdbcTemplate jdbc;

    public SellerMessages(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    public Map<String, Object> open(long userId, long productId) {
        List<Map<String, Object>> products = jdbc.queryForList(
                "SELECT id, name, seller_id, status FROM products WHERE id = ?", productId);
        if (products.isEmpty()) {
            throw new ApiException("NOT_FOUND", "商品不存在", 404);
        }
        long sellerId = MarketStore.num(products.get(0).get("seller_id"));
        if (sellerId == userId) {
            throw new ApiException("CONFLICT", "不能联系自己", 409);
        }
        List<Long> existing = jdbc.queryForList(
                "SELECT id FROM conversations WHERE product_id = ? AND buyer_id = ?",
                Long.class, productId, userId);
        long conversationId;
        if (existing.isEmpty()) {
            String now = now();
            jdbc.update("""
                    INSERT INTO conversations (product_id, buyer_id, seller_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """, productId, userId, sellerId, now, now);
            conversationId = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        } else {
            conversationId = existing.get(0);
        }
        return conversation(conversationId, userId);
    }

    public List<Map<String, Object>> list(long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT c.id, c.product_id, c.buyer_id, c.seller_id, c.updated_at,
                       p.name AS product_name, buyer.username AS buyer_name, seller.username AS seller_name,
                       (SELECT content FROM messages m WHERE m.conversation_id = c.id ORDER BY m.id DESC LIMIT 1) AS last_message
                FROM conversations c
                JOIN products p ON p.id = c.product_id
                JOIN users buyer ON buyer.id = c.buyer_id
                JOIN users seller ON seller.id = c.seller_id
                WHERE c.buyer_id = ? OR c.seller_id = ?
                ORDER BY c.updated_at DESC, c.id DESC
                """, userId, userId);
        List<Map<String, Object>> items = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            items.add(summary(row, userId));
        }
        return items;
    }

    public List<Map<String, Object>> messages(long userId, long conversationId) {
        requireParticipant(userId, conversationId);
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, sender_id, content, created_at
                FROM messages WHERE conversation_id = ? ORDER BY id
                """, conversationId);
        List<Map<String, Object>> items = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", MarketStore.num(row.get("id")));
            item.put("sender_id", MarketStore.num(row.get("sender_id")));
            item.put("content", String.valueOf(row.get("content")));
            item.put("created_at", text(row.get("created_at")));
            items.add(item);
        }
        return items;
    }

    @Transactional
    public Map<String, Object> send(long userId, long conversationId, String content) {
        requireParticipant(userId, conversationId);
        String text = content == null ? "" : content.trim();
        if (text.isEmpty() || text.length() > 500 || text.contains("<")) {
            throw new ApiException("VALIDATION_ERROR", "消息需要 1 到 500 字，且不能包含 HTML 标签", 422);
        }
        String now = now();
        jdbc.update(
                "INSERT INTO messages (conversation_id, sender_id, content, created_at) VALUES (?, ?, ?, ?)",
                conversationId, userId, text, now);
        jdbc.update("UPDATE conversations SET updated_at = ? WHERE id = ?", now, conversationId);
        long messageId = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", messageId);
        item.put("sender_id", userId);
        item.put("content", text);
        item.put("created_at", now);
        return item;
    }

    private void requireParticipant(long userId, long conversationId) {
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM conversations WHERE id = ? AND (buyer_id = ? OR seller_id = ?)",
                Integer.class, conversationId, userId, userId);
        if (count == null || count == 0) {
            throw new ApiException("NOT_FOUND", "对话不存在", 404);
        }
    }

    private Map<String, Object> conversation(long conversationId, long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT c.id, c.product_id, c.buyer_id, c.seller_id, c.updated_at,
                       p.name AS product_name, buyer.username AS buyer_name, seller.username AS seller_name,
                       (SELECT content FROM messages m WHERE m.conversation_id = c.id ORDER BY m.id DESC LIMIT 1) AS last_message
                FROM conversations c
                JOIN products p ON p.id = c.product_id
                JOIN users buyer ON buyer.id = c.buyer_id
                JOIN users seller ON seller.id = c.seller_id
                WHERE c.id = ?
                """, conversationId);
        if (rows.isEmpty()) {
            throw new ApiException("NOT_FOUND", "对话不存在", 404);
        }
        return summary(rows.get(0), userId);
    }

    private static Map<String, Object> summary(Map<String, Object> row, long userId) {
        long buyerId = MarketStore.num(row.get("buyer_id"));
        boolean buyer = buyerId == userId;
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", MarketStore.num(row.get("id")));
        item.put("product_id", MarketStore.num(row.get("product_id")));
        item.put("product_name", String.valueOf(row.get("product_name")));
        item.put("buyer_id", buyerId);
        item.put("seller_id", MarketStore.num(row.get("seller_id")));
        item.put("peer_name", buyer ? String.valueOf(row.get("seller_name")) : String.valueOf(row.get("buyer_name")));
        item.put("last_message", row.get("last_message") == null ? "" : String.valueOf(row.get("last_message")));
        item.put("updated_at", text(row.get("updated_at")));
        return item;
    }

    private static String text(Object value) {
        return value == null ? "" : String.valueOf(value).replace('T', ' ');
    }

    private static String now() {
        return LocalDateTime.now().format(STAMP);
    }
}
