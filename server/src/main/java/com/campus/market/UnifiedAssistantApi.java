package com.campus.market;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
public class UnifiedAssistantApi {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private final JdbcTemplate jdbc;
    private final AdminGuard guard;
    private final UserAgentApi agent;
    private final CampusProperties properties;
    private final MarketStore store;
    private final ObjectMapper mapper;
    private final AgentPlanService plans;
    private final RestClient dataClient;

    public UnifiedAssistantApi(JdbcTemplate jdbc, AdminGuard guard, UserAgentApi agent,
                               CampusProperties properties, MarketStore store, ObjectMapper mapper,
                               AgentPlanService plans) {
        this.jdbc = jdbc;
        this.guard = guard;
        this.agent = agent;
        this.properties = properties;
        this.store = store;
        this.mapper = mapper;
        this.plans = plans;
        String root = properties.getDataUrl();
        if (root.endsWith("/")) {
            root = root.substring(0, root.length() - 1);
        }
        this.dataClient = RestClient.builder().baseUrl(root).build();
    }

    @PostMapping("/api/v1/assistant/message")
    public Map<String, Object> message(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        Map<String, Object> user = guard.authenticated(request);
        long userId = MarketStore.num(user.get("id"));
        String message = MarketStore.str(body.get("message"));
        if (message.isBlank() && MarketStore.str(body.get("image_data_url")).isBlank()) {
            throw new ApiException("VALIDATION_ERROR", "message 或图片不能为空", 422);
        }
        Long requested = body.get("session_id") == null ? null : MarketStore.num(body.get("session_id"));
        long sessionId = requested == null ? createSession(userId, message) : ownedSession(requested, userId);

        Map<String, Object> activePlan = plans.active(sessionId);
        if (activePlan != null && isContinuation(message)) {
            long planId = MarketStore.num(activePlan.get("id"));
            if (isCancel(message)) {
                plans.cancel(planId);
                insertMessage(sessionId, "user", message, "text", null, null);
                String reply = "当前计划已取消，相关待确认操作也已取消。";
                Map<String, Object> data = new LinkedHashMap<>();
                data.put("session_id", sessionId);
                data.put("source", "complex");
                data.put("reply", reply);
                data.put("plan_id", planId);
                data.put("plan_steps", activePlan.get("steps"));
                data.put("action_proposals", List.of());
                insertMessage(sessionId, "assistant", reply, "text", data, null);
                return Map.of("data", data);
            }
            List<Map<String, Object>> pending = plans.pendingActions(planId);
            insertMessage(sessionId, "user", message, "text", null, null);
            String reply = pending.isEmpty()
                    ? "当前计划没有待确认动作，请告诉我下一步要做什么。"
                    : "当前还有 " + pending.size() + " 个待确认操作，请在下方逐项确认或取消。";
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("session_id", sessionId);
            data.put("source", "complex");
            data.put("reply", reply);
            data.put("plan_id", planId);
            data.put("plan_steps", activePlan.get("steps"));
            data.put("action_proposals", pending);
            insertMessage(sessionId, "assistant", reply, "text", data, null);
            return Map.of("data", data);
        }

        if (isCapability(message)) {
            insertMessage(sessionId, "user", message, "text", null, null);
            String reply = "我可以帮你查商品、按预算和成色筛选、推荐商品、识别图片，也可以分析商品链接、对比候选商品、给出购买建议和问卖家的话术。加购物车和给卖家发消息需要你确认；下单、支付、删除和改价不会由我直接执行。";
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("session_id", sessionId);
            data.put("source", "quick");
            data.put("engine", "rules");
            data.put("reply", reply);
            data.put("items", List.of());
            insertMessage(sessionId, "assistant", reply, "text", data, null);
            return Map.of("data", data);
        }

        if (isComplex(message)) {
            Map<String, Object> forwarded = new LinkedHashMap<>(body);
            forwarded.put("session_id", sessionId);
            ResponseEntity<Map<String, Object>> response = agent.chat(request, forwarded);
            Map<String, Object> data = response.getBody() == null ? Map.of() : response.getBody();
            Object inner = data.get("data");
            if (inner instanceof Map<?, ?> map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> result = new LinkedHashMap<>((Map<String, Object>) map);
                result.put("source", "complex");
                updateLastAssistantMetadata(sessionId, result);
                return Map.of("data", result);
            }
            return Map.of("data", data);
        }

        List<Map<String, Object>> previousHistory = history(sessionId);
        insertMessage(sessionId, "user", message.isBlank() ? "上传了图片" : message, "text", null, null);
        Map<String, Object> context = context(sessionId);
        Map<String, Object> pythonBody = new LinkedHashMap<>();
        pythonBody.put("user_id", userId);
        pythonBody.put("message", message);
        pythonBody.put("filename", body.get("filename"));
        pythonBody.put("image_data_url", body.get("image_data_url"));
        pythonBody.put("history", previousHistory);
        pythonBody.put("slots", context.get("slots") instanceof Map<?, ?> slots ? slots : Map.of());
        Map<?, ?> response;
        try {
            response = dataClient.post()
                    .uri("/api/ai/assistant-reply")
                    .header("X-Internal-Token", properties.getJwtSecret())
                    .body(pythonBody)
                    .retrieve()
                    .body(Map.class);
        } catch (Exception exc) {
            throw new ApiException("DATA_UNAVAILABLE", "AI 数据服务暂时不可用", 503);
        }
        Object raw = response == null ? null : response.get("data");
        Map<String, Object> data = raw instanceof Map<?, ?> map ? stringMap(map) : new LinkedHashMap<>();
        data.put("session_id", sessionId);
        data.put("source", "quick");
        insertMessage(sessionId, "assistant", MarketStore.str(data.get("reply")), "text", data, null);
        Map<String, Object> next = new LinkedHashMap<>(context);
        if (data.get("slots") instanceof Map<?, ?> slots) {
            next.put("slots", slots);
        }
        if (data.get("items") instanceof List<?> items) {
            List<Long> productIds = new ArrayList<>();
            for (Object item : items) {
                if (item instanceof Map<?, ?> row && row.get("id") != null) {
                    productIds.add(MarketStore.num(row.get("id")));
                }
            }
            next.put("product_ids", productIds.stream().distinct().limit(8).toList());
        }
        updateContext(sessionId, next);
        return Map.of("data", data);
    }

    @GetMapping("/api/v1/assistant/sessions")
    public Map<String, Object> sessions(HttpServletRequest request) {
        Map<String, Object> user = guard.authenticated(request);
        long userId = MarketStore.num(user.get("id"));
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT s.id, s.title, s.updated_at,
                       (SELECT content FROM conversation_messages m
                        WHERE m.session_id = s.id AND m.role = 'user'
                        ORDER BY m.id DESC LIMIT 1) AS preview
                FROM conversation_sessions s
                WHERE s.user_id = ? AND s.deleted_at IS NULL
                ORDER BY s.updated_at DESC, s.id DESC
                LIMIT 50
                """, userId);
        return Map.of("data", rows);
    }

    @GetMapping("/api/v1/assistant/sessions/{id}/messages")
    public Map<String, Object> messages(HttpServletRequest request, @PathVariable long id) {
        Map<String, Object> user = guard.authenticated(request);
        long userId = MarketStore.num(user.get("id"));
        ownedSession(id, userId);
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, role, content, content_type, metadata_json, created_at
                FROM conversation_messages WHERE session_id = ? ORDER BY id
                """, id);
        List<Map<String, Object>> actions = jdbc.queryForList("""
                SELECT id AS action_id, message_id, action_type, status, payload_json,
                       expires_at, executed_at, created_at
                FROM pending_actions WHERE session_id = ? ORDER BY id
                """, id);
        Map<Long, List<Map<String, Object>>> byMessage = new LinkedHashMap<>();
        List<Map<String, Object>> unbound = new ArrayList<>();
        for (Map<String, Object> action : actions) {
            Map<String, Object> item = new LinkedHashMap<>(action);
            item.put("type", action.get("action_type"));
            item.put("payload", jsonMap(action.get("payload_json")));
            item.remove("action_type");
            item.remove("payload_json");
            Object messageId = action.get("message_id");
            if (messageId == null) {
                unbound.add(item);
            } else {
                byMessage.computeIfAbsent(MarketStore.num(messageId), key -> new ArrayList<>()).add(item);
            }
        }

        List<Map<String, Object>> result = new ArrayList<>();
        long lastAssistant = 0;
        for (Map<String, Object> row : rows) {
            Map<String, Object> item = new LinkedHashMap<>(row);
            item.put("metadata", jsonMap(row.get("metadata_json")));
            item.remove("metadata_json");
            long messageId = MarketStore.num(row.get("id"));
            if ("assistant".equals(MarketStore.str(row.get("role")))) {
                lastAssistant = messageId;
            }
            item.put("actions", byMessage.getOrDefault(messageId, List.of()));
            result.add(item);
        }
        if (!unbound.isEmpty()) {
            for (int i = result.size() - 1; i >= 0; i--) {
                if (MarketStore.num(result.get(i).get("id")) == lastAssistant) {
                    List<Map<String, Object>> merged = new ArrayList<>(castList(result.get(i).get("actions")));
                    merged.addAll(unbound);
                    result.get(i).put("actions", merged);
                    break;
                }
            }
        }
        return Map.of("data", result);
    }

    @GetMapping("/api/v1/assistant/sessions/{id}/plan")
    public Map<String, Object> plan(HttpServletRequest request, @PathVariable long id) {
        Map<String, Object> user = guard.authenticated(request);
        ownedSession(id, MarketStore.num(user.get("id")));
        Map<String, Object> plan = plans.latest(id);
        if (plan == null) {
            throw new ApiException("NOT_FOUND", "计划不存在", 404);
        }
        return Map.of("data", plan);
    }

    @DeleteMapping("/api/v1/assistant/sessions/{id}")
    public Map<String, Object> delete(HttpServletRequest request, @PathVariable long id) {
        Map<String, Object> user = guard.authenticated(request);
        long userId = MarketStore.num(user.get("id"));
        ownedSession(id, userId);
        String now = LocalDateTime.now().format(STAMP);
        jdbc.update("UPDATE conversation_sessions SET deleted_at = ?, deleted_by = ? WHERE id = ? AND user_id = ?",
                now, userId, id, userId);
        jdbc.update("UPDATE pending_actions SET status = 'cancelled' WHERE session_id = ? AND status = 'pending'", id);
        store.writeLog(user, "assistant.session.delete", "agent_session", String.valueOf(id));
        return Map.of("data", Map.of("deleted", true, "session_id", id));
    }

    private long createSession(long userId, String message) {
        String title = message == null || message.isBlank() ? "图片对话" : trim(message, 80);
        String now = LocalDateTime.now().format(STAMP);
        return insert("""
                INSERT INTO conversation_sessions
                (user_id, agent_code, title, status, token_budget, context_json, last_message_at, created_at, updated_at)
                VALUES (?, 'assistant', ?, 'active', 6000, '{}', ?, ?, ?)
                """, userId, title, now, now, now);
    }

    private long ownedSession(long id, long userId) {
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM conversation_sessions WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
                Integer.class, id, userId);
        if (count == null || count == 0) {
            throw new ApiException("SESSION_NOT_FOUND", "会话不存在", 404);
        }
        return id;
    }

    private Map<String, Object> context(long sessionId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT context_json FROM conversation_sessions WHERE id = ?", sessionId);
        Map<String, Object> context = rows.isEmpty() ? new LinkedHashMap<>() : jsonMap(rows.get(0).get("context_json"));
        if (!(context.get("slots") instanceof Map<?, ?>)) {
            context.put("slots", Map.of());
        }
        return context;
    }

    private List<Map<String, Object>> history(long sessionId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT role, content FROM conversation_messages
                WHERE session_id = ? AND role IN ('user','assistant')
                ORDER BY id DESC LIMIT 20
                """, sessionId);
        List<Map<String, Object>> result = new ArrayList<>();
        for (int i = rows.size() - 1; i >= 0; i--) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("role", rows.get(i).get("role"));
            item.put("content", rows.get(i).get("content"));
            result.add(item);
        }
        return result;
    }

    private void insertMessage(long sessionId, String role, String content, String contentType,
                               Map<String, Object> metadata, String traceId) {
        jdbc.update("""
                INSERT INTO conversation_messages
                (session_id, role, content, content_type, metadata_json, agent_code, token_count, trace_id, created_at)
                VALUES (?, ?, ?, ?, ?, 'assistant', ?, ?, ?)
                """, sessionId, role, content, contentType, json(metadata),
                Math.max(1, content.length() / 4), traceId, LocalDateTime.now().format(STAMP));
    }

    private void updateContext(long sessionId, Map<String, Object> context) {
        jdbc.update("UPDATE conversation_sessions SET context_json = ?, updated_at = ? WHERE id = ?",
                json(context), LocalDateTime.now().format(STAMP), sessionId);
    }

    private void updateLastAssistantMetadata(long sessionId, Map<String, Object> data) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id FROM conversation_messages
                WHERE session_id = ? AND role = 'assistant'
                ORDER BY id DESC LIMIT 1
                """, sessionId);
        if (!rows.isEmpty()) {
            jdbc.update("UPDATE conversation_messages SET metadata_json = ? WHERE id = ?",
                    json(data), rows.get(0).get("id"));
        }
    }

    private static boolean isContinuation(String message) {
        return has(message, "继续", "下一步", "确认", "取消", "不用了", "接着");
    }

    private static boolean isCancel(String message) {
        return has(message, "取消", "不用了");
    }

    private static boolean isCapability(String message) {
        return has(message, "你能做什么", "能做哪些事", "能帮我做什么", "你会什么", "有什么功能");
    }

    private static boolean isComplex(String message) {
        return has(message, "/product/", "对比", "比较", "哪个好", "加购物车", "加入购物车",
                "加购", "问卖家", "联系卖家", "发消息", "帮我问", "帮问", "值得买", "分析");
    }

    private static boolean has(String text, String... words) {
        for (String word : words) {
            if (text.contains(word)) {
                return true;
            }
        }
        return false;
    }

    private Map<String, Object> jsonMap(Object value) {
        try {
            return value == null || String.valueOf(value).isBlank()
                    ? new LinkedHashMap<>() : mapper.readValue(String.valueOf(value), Map.class);
        } catch (Exception exc) {
            return new LinkedHashMap<>();
        }
    }

    private String json(Object value) {
        try {
            return value == null ? null : mapper.writeValueAsString(value);
        } catch (Exception exc) {
            return null;
        }
    }

    private static Map<String, Object> stringMap(Map<?, ?> raw) {
        Map<String, Object> data = new LinkedHashMap<>();
        raw.forEach((key, value) -> data.put(String.valueOf(key), value));
        return data;
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> castList(Object value) {
        return value instanceof List<?> list ? (List<Map<String, Object>>) list : List.of();
    }

    private static String trim(String value, int max) {
        String text = value == null ? "" : value.trim();
        return text.length() <= max ? text : text.substring(0, max);
    }

    private long insert(String sql, Object... args) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement statement = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
            for (int i = 0; i < args.length; i++) {
                statement.setObject(i + 1, args[i]);
            }
            return statement;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            throw new ApiException("CONTEXT_WRITE_FAILED", "会话写入失败", 500);
        }
        return key.longValue();
    }
}
