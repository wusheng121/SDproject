package com.campus.market;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@RestController
public class UserAgentApi {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final Pattern PRODUCT_LINK = Pattern.compile("/product/(\\d+)");
    private final JdbcTemplate jdbc;
    private final AdminGuard guard;
    private final AgentApi agentApi;
    private final MarketStore store;
    private final SellerMessages messages;
    private final ObjectMapper mapper;
    private final AgentPlanService plans;

    public UserAgentApi(JdbcTemplate jdbc, AdminGuard guard, AgentApi agentApi,
                        MarketStore store, SellerMessages messages, ObjectMapper mapper,
                        AgentPlanService plans) {
        this.jdbc = jdbc;
        this.guard = guard;
        this.agentApi = agentApi;
        this.store = store;
        this.messages = messages;
        this.mapper = mapper;
        this.plans = plans;
    }

    @PostMapping("/api/v1/assistant/agent")
    public ResponseEntity<Map<String, Object>> chat(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        Map<String, Object> user = guard.authenticated(request);
        long userId = MarketStore.num(user.get("id"));
        String message = MarketStore.str(body.get("message"));
        if (message.isBlank()) {
            throw new ApiException("VALIDATION_ERROR", "message 不能为空", 422);
        }
        long sessionId = session(body.get("session_id"), userId, message);
        String traceId = UUID.randomUUID().toString().replace("-", "");
        insertMessage(sessionId, "user", message, traceId);

        List<Long> linked = productIds(message);
        List<Long> previous = contextIds(sessionId);
        boolean compareIntent = contains(message, "对比", "比较", "哪个好", "性价比");
        boolean cartIntent = contains(message, "加购物车", "加入购物车", "加购");
        boolean contactIntent = contains(message, "问卖家", "问一下", "帮我问", "帮问", "咨询", "联系卖家", "发消息");
        boolean reference = contains(message, "这个", "它", "刚才", "上面", "之前", "链接") || !linked.isEmpty();
        String intent = intentOf(message);

        List<Long> active = new ArrayList<>();
        if (!linked.isEmpty()) {
            active.addAll(linked);
        } else if (!(compareIntent && !reference)) {
            active.addAll(previous);
        }
        List<String> planLabels = planLabels(linked, compareIntent, cartIntent, contactIntent);
        long planId = plans.create(sessionId, userId, message, planLabels);

        List<Map<String, Object>> products = new ArrayList<>();
        Map<String, Object> advice = null;
        Map<String, Object> comparison = null;
        List<String> questions = new ArrayList<>();
        String script = "";
        List<Map<String, Object>> actions = new ArrayList<>();
        Long primary = active.isEmpty() ? null : active.get(0);

        Long actionTarget = null;
        if ((cartIntent || contactIntent) && !active.isEmpty()) {
            actionTarget = resolveTarget(message, active);
            if (actionTarget == null && (active.size() == 1 || contactIntent)) {
                actionTarget = active.get(0);
            }
            if (actionTarget != null) {
                if (!active.contains(actionTarget)) {
                    active.add(0, actionTarget);
                }
                primary = actionTarget;
            }
        }

        if (primary != null && !cartIntent) {
            advice = agentApi.executeSkill("product_advice", Map.of("product_id", primary), userId);
            questions = strings(advice.get("questions"));
            script = MarketStore.str(advice.get("script"));
        }
        if (contactIntent) {
            advice = null;
        }

        if (compareIntent) {
            List<Long> compareIds = new ArrayList<>(reference ? active : List.of());
            if (compareIds.size() < 2) {
                Map<String, Object> search = agentApi.executeSkill("nl_filter", Map.of("text", message), userId);
                for (Object item : list(search.get("items"))) {
                    Map<String, Object> row = map(item);
                    if (row.get("id") != null) {
                        long id = MarketStore.num(row.get("id"));
                        if (!compareIds.contains(id)) {
                            compareIds.add(id);
                        }
                    }
                    if (compareIds.size() >= 3) {
                        break;
                    }
                }
            }
            if (compareIds.size() >= 2) {
                comparison = agentApi.executeSkill("product_compare",
                        Map.of("product_ids", compareIds.subList(0, Math.min(compareIds.size(), 3))), userId);
                active.clear();
                active.addAll(compareIds.stream().distinct().limit(5).toList());
            }
        }

        List<Long> displayIds = new ArrayList<>(active);
        if (comparison != null) {
            displayIds = list(comparison.get("items")).stream()
                    .map(item -> map(item).get("product_id"))
                    .filter(value -> value != null)
                    .map(MarketStore::num)
                    .distinct()
                    .toList();
        } else if ((cartIntent || contactIntent) && actionTarget != null) {
            displayIds = List.of(actionTarget);
        }
        for (Long id : displayIds.stream().limit(5).toList()) {
            Map<String, Object> detail = agentApi.executeSkill("product_detail", Map.of("product_id", id), userId);
            products.add(map(detail.get("product")));
        }

        if (cartIntent && actionTarget != null) {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("product_id", actionTarget);
            actions.add(proposal(userId, sessionId, "cart_add", payload, traceId, planId));
        }
        if (contactIntent && actionTarget != null) {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("product_id", actionTarget);
            payload.put("content", trim(script, 500));
            actions.add(proposal(userId, sessionId, "seller_message", payload, traceId, planId));
        }

        String reply = reply(intent, products, advice, comparison, actions);
        long assistantMessageId = insertMessage(sessionId, "assistant", reply, traceId);
        for (Map<String, Object> action : actions) {
            jdbc.update("UPDATE pending_actions SET message_id = ?, plan_id = ? WHERE id = ?",
                    assistantMessageId, planId, MarketStore.num(action.get("action_id")));
        }
        plans.finish(planId, actions.isEmpty() ? "completed" : "awaiting_confirmation", planLabels);
        updateContext(sessionId, active, planId);
        store.writeLog(user, "assistant.agent.chat", "agent_session", String.valueOf(sessionId));

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("session_id", sessionId);
        data.put("trace_id", traceId);
        data.put("intent", intent);
        data.put("reply", reply);
        data.put("products", products);
        data.put("advice", advice);
        data.put("comparison", comparison);
        data.put("questions", questions);
        data.put("action_proposals", actions);
        data.put("plan_id", planId);
        data.put("plan_steps", planLabels);
        return ResponseEntity.ok(Map.of("data", data));
    }

    @PostMapping("/api/v1/assistant/actions/{id}/confirm")
    public Map<String, Object> confirm(HttpServletRequest request, @PathVariable long id,
                                       @RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> user = guard.authenticated(request);
        long userId = MarketStore.num(user.get("id"));
        Map<String, Object> action = pending(id, userId);
        String type = MarketStore.str(action.get("action_type"));
        Map<String, Object> payload = jsonMap(action.get("payload_json"));
        long productId = MarketStore.num(payload.get("product_id"));
        Object result;
        if ("cart_add".equals(type)) {
            boolean created = store.addCart(userId, productId);
            result = Map.of("created", created, "product_id", productId);
        } else if ("seller_message".equals(type)) {
            Map<String, Object> conversation = messages.open(userId, productId);
            long conversationId = MarketStore.num(conversation.get("id"));
            String content = body == null ? MarketStore.str(payload.get("content"))
                    : MarketStore.str(body.get("content"));
            result = messages.send(userId, conversationId, trim(content, 500));
        } else {
            throw new ApiException("ACTION_UNSUPPORTED", "不支持的操作类型", 422);
        }
        jdbc.update("UPDATE pending_actions SET status = 'executed', executed_at = ? WHERE id = ?",
                LocalDateTime.now().format(STAMP), id);
        if (action.get("plan_id") != null) {
            plans.completeIfNoPending(MarketStore.num(action.get("plan_id")));
        }
        store.writeLog(user, "assistant.action.confirm", type, String.valueOf(id));
        return Map.of("data", Map.of("executed", true, "action_type", type, "result", result));
    }

    @PostMapping("/api/v1/assistant/actions/{id}/cancel")
    public Map<String, Object> cancel(HttpServletRequest request, @PathVariable long id) {
        Map<String, Object> user = guard.authenticated(request);
        Map<String, Object> action = pending(id, MarketStore.num(user.get("id")));
        jdbc.update("UPDATE pending_actions SET status = 'cancelled' WHERE id = ?", id);
        if (action.get("plan_id") != null) {
            plans.completeIfNoPending(MarketStore.num(action.get("plan_id")));
        }
        return Map.of("data", Map.of("cancelled", true));
    }

    private long session(Object raw, long userId, String message) {
        if (raw != null && !String.valueOf(raw).isBlank()) {
            long id = MarketStore.num(raw);
            Integer count = jdbc.queryForObject(
                    "SELECT COUNT(*) FROM conversation_sessions WHERE id = ? AND user_id = ?",
                    Integer.class, id, userId);
            if (count == null || count == 0) {
                throw new ApiException("SESSION_NOT_FOUND", "会话不存在", 404);
            }
            return id;
        }
        String title = trim(message, 80);
        String now = LocalDateTime.now().format(STAMP);
        return insert("""
                INSERT INTO conversation_sessions
                (user_id, agent_code, title, status, token_budget, context_json, last_message_at, created_at, updated_at)
                VALUES (?, 'user_agent', ?, 'active', 6000, '{}', ?, ?, ?)
                """, userId, title, now, now, now);
    }

    private long insertMessage(long sessionId, String role, String content, String traceId) {
        return insert("""
                INSERT INTO conversation_messages
                (session_id, role, content, content_type, agent_code, token_count, trace_id, created_at)
                VALUES (?, ?, ?, 'text', 'user_agent', ?, ?, ?)
                """, sessionId, role, content, Math.max(1, content.length() / 4), traceId,
                LocalDateTime.now().format(STAMP));
    }

    private List<Long> contextIds(long sessionId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT context_json FROM conversation_sessions WHERE id = ?", sessionId);
        if (rows.isEmpty() || rows.get(0).get("context_json") == null) {
            return new ArrayList<>();
        }
        Map<String, Object> context = jsonMap(rows.get(0).get("context_json"));
        return longs(context.get("product_ids"));
    }

    private void updateContext(long sessionId, List<Long> productIds, long planId) {
        Map<String, Object> context = new LinkedHashMap<>();
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT context_json FROM conversation_sessions WHERE id = ?", sessionId);
        if (!rows.isEmpty()) {
            context.putAll(jsonMap(rows.get(0).get("context_json")));
        }
        context.put("product_ids", productIds.stream().distinct().limit(8).toList());
        context.put("active_plan_id", planId);
        context.put("updated_at", LocalDateTime.now().format(STAMP));
        jdbc.update("UPDATE conversation_sessions SET context_json = ?, updated_at = ? WHERE id = ?",
                json(context), LocalDateTime.now().format(STAMP), sessionId);
    }

    private Map<String, Object> proposal(long userId, long sessionId, String type,
                                         Map<String, Object> payload, String traceId, long planId) {
        String expires = LocalDateTime.now().plusMinutes(10).format(STAMP);
        long id = insert("""
                INSERT INTO pending_actions
                (user_id, session_id, action_type, payload_json, status, expires_at, trace_id, plan_id, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                """, userId, sessionId, type, json(payload), expires, traceId, planId,
                LocalDateTime.now().format(STAMP));
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("action_id", id);
        data.put("type", type);
        data.put("payload", payload);
        data.put("expires_at", expires);
        return data;
    }

    private Map<String, Object> pending(long id, long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT * FROM pending_actions
                WHERE id = ? AND user_id = ? AND status = 'pending' AND expires_at > NOW()
                """, id, userId);
        if (rows.isEmpty()) {
            throw new ApiException("ACTION_EXPIRED", "操作不存在、已处理或已过期", 410);
        }
        return rows.get(0);
    }

    private static List<String> planLabels(List<Long> linked, boolean compareIntent,
                                          boolean cartIntent, boolean contactIntent) {
        List<String> labels = new ArrayList<>();
        if (!linked.isEmpty() || (!compareIntent && !cartIntent && !contactIntent)) {
            labels.add("读取商品信息");
            labels.add("生成购买建议");
        }
        if (compareIntent) {
            labels.add("搜索候选商品");
            labels.add("对比候选商品");
        }
        if (cartIntent) {
            labels.add("解析目标商品");
            labels.add("生成加购动作");
        }
        if (contactIntent) {
            labels.add("解析目标商品");
            labels.add("生成卖家问题");
            labels.add("生成消息草稿");
        }
        if (labels.isEmpty()) {
            labels.add("处理请求");
        }
        return labels;
    }

    private static String reply(String intent, List<Map<String, Object>> products,
                                Map<String, Object> advice, Map<String, Object> comparison,
                                List<Map<String, Object>> actions) {
        StringBuilder text = new StringBuilder();
        if (products.size() > 1) {
            text.append("已解析 ").append(products.size()).append(" 件商品。");
        } else if (products.size() == 1) {
            text.append("已读取商品：").append(products.get(0).get("name")).append("。");
        } else if (comparison != null) {
            text.append("已找到候选商品并完成对比。");
        } else {
            text.append("暂未识别到商品链接，请粘贴站内商品链接或描述需求。");
        }
        if (advice != null && advice.get("summary") != null) {
            text.append("\n").append(advice.get("summary"));
        }
        if (comparison != null && comparison.get("recommendation") != null) {
            text.append("\n对比建议：").append(comparison.get("recommendation"));
        }
        if (!actions.isEmpty()) {
            text.append("\n已生成操作提议，请在下方确认后执行。");
        }
        return text.toString();
    }

    private Long resolveTarget(String message, List<Long> candidates) {
        String[] ordinals = {"第一", "第二", "第三", "第1", "第2", "第3"};
        for (int i = 0; i < ordinals.length; i++) {
            if (message.contains(ordinals[i]) && candidates.size() > i % 3) {
                return candidates.get(i % 3);
            }
        }

        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT id, name FROM products WHERE status = 'approved'");
        List<Long> matches = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            String name = MarketStore.str(row.get("name"));
            String token = name.split("\\s+")[0];
            if (token.length() >= 2 && message.contains(token)) {
                matches.add(MarketStore.num(row.get("id")));
            }
        }
        List<Long> preferred = matches.stream().filter(candidates::contains).distinct().toList();
        if (preferred.size() == 1) {
            return preferred.get(0);
        }
        if (matches.size() == 1) {
            return matches.get(0);
        }
        if (candidates.size() == 1) {
            return candidates.get(0);
        }
        if (contains(message, "这个", "它", "刚才") && !candidates.isEmpty()) {
            return candidates.get(0);
        }
        return null;
    }

    private static String intentOf(String message) {
        if (contains(message, "对比", "比较", "哪个好", "性价比")) {
            return "compare";
        }
        if (contains(message, "加购物车", "加入购物车", "加购")) {
            return "cart";
        }
        if (contains(message, "问卖家", "问一下", "帮我问", "帮问", "咨询", "联系卖家", "发消息")) {
            return "contact_seller";
        }
        return "product_analysis";
    }

    private static boolean contains(String text, String... words) {
        for (String word : words) {
            if (text.contains(word)) {
                return true;
            }
        }
        return false;
    }

    private static List<Long> productIds(String message) {
        List<Long> ids = new ArrayList<>();
        Matcher matcher = PRODUCT_LINK.matcher(message);
        while (matcher.find()) {
            ids.add(Long.parseLong(matcher.group(1)));
        }
        return ids;
    }

    private static List<String> strings(Object value) {
        List<String> result = new ArrayList<>();
        if (value instanceof List<?> list) {
            for (Object item : list) {
                String text = MarketStore.str(item);
                if (!text.isBlank()) {
                    result.add(text);
                }
            }
        }
        return result;
    }

    private static List<?> list(Object value) {
        return value instanceof List<?> list ? list : List.of();
    }

    private static List<Long> longs(Object value) {
        List<Long> result = new ArrayList<>();
        if (value instanceof List<?> list) {
            for (Object item : list) {
                try {
                    result.add(MarketStore.num(item));
                } catch (RuntimeException ignored) {
                }
            }
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Object value) {
        return value instanceof Map<?, ?> raw ? (Map<String, Object>) raw : Map.of();
    }

    private Map<String, Object> jsonMap(Object value) {
        try {
            return value == null ? Map.of() : mapper.readValue(String.valueOf(value), Map.class);
        } catch (Exception exc) {
            return Map.of();
        }
    }

    private String json(Object value) {
        try {
            return value == null ? "{}" : mapper.writeValueAsString(value);
        } catch (Exception exc) {
            return "{}";
        }
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
            throw new ApiException("CONTEXT_WRITE_FAILED", "上下文写入失败", 500);
        }
        return key.longValue();
    }
}
