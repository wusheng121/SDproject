package com.campus.market;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

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
public class AgentOrchestratorApi {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private final JdbcTemplate jdbc;
    private final AgentAuth auth;
    private final AgentApi agentApi;
    private final IntentClient intentClient;
    private final MarketStore store;
    private final ObjectMapper mapper;

    public AgentOrchestratorApi(JdbcTemplate jdbc, AgentAuth auth, AgentApi agentApi,
                                IntentClient intentClient, MarketStore store, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.auth = auth;
        this.agentApi = agentApi;
        this.intentClient = intentClient;
        this.store = store;
        this.mapper = mapper;
    }

    @PostMapping("/api/v1/agent/orchestrate")
    public ResponseEntity<Map<String, Object>> orchestrate(HttpServletRequest request,
                                                           @RequestBody Map<String, Object> body) {
        AgentAuth.Principal principal = auth.authenticate(request);
        String message = MarketStore.str(body.get("message"));
        if (message.isBlank()) {
            throw new ApiException("VALIDATION_ERROR", "message 不能为空", 422);
        }
        long userId = MarketStore.num(principal.user().get("id"));
        long sessionId = session(body.get("session_id"), userId, message);
        String traceId = UUID.randomUUID().toString().replace("-", "");
        String now = LocalDateTime.now().format(STAMP);

        insertMessage(sessionId, "user", message, "main_agent", traceId);

        String ruleIntent = classify(message);
        Map<String, Object> fallbackHint = new LinkedHashMap<>();
        fallbackHint.put("intent", ruleIntent);
        fallbackHint.put("sub_agent", switch (ruleIntent) {
            case "recommendation" -> "recommendation_agent";
            case "trade" -> "trade_agent";
            case "user" -> "user_agent";
            default -> "product_agent";
        });
        fallbackHint.put("skill", defaultSkill(ruleIntent, message));
        fallbackHint.put("source", "rule");
        Map<String, Object> hint = intentClient.classify(message, fallbackHint);
        String intent = validIntent(MarketStore.str(hint.get("intent")))
                ? MarketStore.str(hint.get("intent")) : ruleIntent;
        String subAgent = validAgent(MarketStore.str(hint.get("sub_agent")))
                ? MarketStore.str(hint.get("sub_agent")) : MarketStore.str(fallbackHint.get("sub_agent"));
        String preferredSkill = MarketStore.str(hint.get("skill"));
        String expectedAgent = agentFor(intent);
        if (!expectedAgent.equals(subAgent)) {
            subAgent = expectedAgent;
            preferredSkill = defaultSkill(intent, message);
        }
        if ("product".equals(ruleIntent) && !containsAny(message, "推荐", "适合", "喜欢", "类似", "猜你")) {
            intent = ruleIntent;
            subAgent = MarketStore.str(fallbackHint.get("sub_agent"));
            preferredSkill = MarketStore.str(fallbackHint.get("skill"));
            hint.put("source", "rule");
        }
        Map<String, Object> agent = agent(subAgent);
        if (agent == null) {
            throw new ApiException("AGENT_NOT_FOUND", "子 Agent 不存在或未启用", 503);
        }

        long intentNode = node(sessionId, null, "intent", Map.of(
                "intent", intent,
                "message", message,
                "agent", subAgent
        ), "success", traceId);

        Map<String, Object> skill = chooseSkill(subAgent, message, preferredSkill);
        Object result = null;
        String skillCode = "";
        long toolNode = 0;
        Map<String, Object> reply;
        if (skill == null) {
            reply = new LinkedHashMap<>();
            reply.put("intent", intent);
            reply.put("skill", null);
            reply.put("reply", fallback(intent));
            reply.put("items", List.of());
        } else {
            skillCode = MarketStore.str(skill.get("code"));
            auth.requireScope(principal, MarketStore.str(skill.get("scope")));
            toolNode = node(sessionId, intentNode, "tool_call", Map.of(
                    "skill", skillCode,
                    "agent", subAgent,
                    "params", Map.of("text", message)
            ), "running", traceId);

            long started = System.currentTimeMillis();
            try {
                result = agentApi.executeSkill(MarketStore.str(skill.get("handler_target")),
                        Map.of("text", message), userId);
                long latency = System.currentTimeMillis() - started;
                toolCall(sessionId, toolNode, MarketStore.num(agent.get("id")),
                        MarketStore.num(skill.get("id")), Map.of("text", message), result,
                        "success", latency, null, traceId);
                finishNode(toolNode, "success", null, traceId);
                reply = compose(intent, subAgent, skillCode, result);
            } catch (ApiException exc) {
                long latency = System.currentTimeMillis() - started;
                toolCall(sessionId, toolNode, MarketStore.num(agent.get("id")),
                        MarketStore.num(skill.get("id")), Map.of("text", message), null,
                        "failed", latency, exc.getCode(), traceId);
                finishNode(toolNode, "failed", exc.getCode(), traceId);
                reply = new LinkedHashMap<>();
                reply.put("intent", intent);
                reply.put("skill", skillCode);
                reply.put("reply", "Skill 执行失败：" + exc.getMessage());
                reply.put("items", List.of());
            }
        }

        String replyText = MarketStore.str(reply.get("reply"));
        long responseNode = node(sessionId, toolNode == 0 ? intentNode : toolNode, "response",
                Map.of("reply", replyText, "skill", skillCode), "success", traceId);
        insertMessage(sessionId, "assistant", replyText, subAgent, traceId);
        updateSession(sessionId, message, replyText, now);
        finishNode(responseNode, "success", null, traceId);
        store.writeLog(principal.user(), "agent.orchestrate", "agent_session", String.valueOf(sessionId));

        Map<String, Object> data = new LinkedHashMap<>(reply);
        data.put("session_id", sessionId);
        data.put("trace_id", traceId);
        data.put("agent", "main_agent");
        data.put("sub_agent", subAgent);
        data.put("intent_source", hint.get("source"));
        data.put("result", result);
        return ResponseEntity.ok(Map.of("data", data));
    }

    private long session(Object rawSessionId, long userId, String message) {
        if (rawSessionId != null && !String.valueOf(rawSessionId).isBlank()) {
            long id = MarketStore.num(rawSessionId);
            List<Map<String, Object>> rows = jdbc.queryForList(
                    "SELECT id, user_id FROM conversation_sessions WHERE id = ?", id);
            if (rows.isEmpty()) {
                throw new ApiException("SESSION_NOT_FOUND", "会话不存在", 404);
            }
            if (MarketStore.num(rows.get(0).get("user_id")) != userId) {
                throw new ApiException("AUTH_FORBIDDEN", "无权访问该会话", 403);
            }
            return id;
        }
        String title = message.length() > 80 ? message.substring(0, 80) : message;
        String now = LocalDateTime.now().format(STAMP);
        return insert("""
                INSERT INTO conversation_sessions
                (user_id, agent_code, title, status, token_budget, last_message_at, created_at, updated_at)
                VALUES (?, 'main_agent', ?, 'active', 6000, ?, ?, ?)
                """, userId, title, now, now, now);
    }

    private void insertMessage(long sessionId, String role, String content, String agentCode, String traceId) {
        jdbc.update("""
                INSERT INTO conversation_messages
                (session_id, role, content, content_type, agent_code, token_count, trace_id, created_at)
                VALUES (?, ?, ?, 'text', ?, ?, ?, ?)
                """, sessionId, role, content, agentCode, Math.max(1, content.length() / 4),
                traceId, LocalDateTime.now().format(STAMP));
    }

    private long node(long sessionId, Long parentId, String type, Map<String, Object> content,
                      String status, String traceId) {
        String now = LocalDateTime.now().format(STAMP);
        return insert("""
                INSERT INTO conversation_nodes
                (session_id, parent_node_id, node_type, content_json, status, started_at, trace_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, sessionId, parentId, type, json(content), status, now, traceId, now);
    }

    private void finishNode(long nodeId, String status, String errorCode, String traceId) {
        jdbc.update("""
                UPDATE conversation_nodes
                SET status = ?, finished_at = ?, error_code = ?
                WHERE id = ?
                """, status, LocalDateTime.now().format(STAMP), errorCode, nodeId);
    }

    private void toolCall(long sessionId, long nodeId, long agentId, long skillId,
                          Map<String, Object> request, Object response, String status,
                          long latencyMs, String errorCode, String traceId) {
        jdbc.update("""
                INSERT INTO agent_tool_calls
                (session_id, node_id, agent_id, skill_id, request_json, response_json, status,
                 latency_ms, error_code, trace_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, sessionId, nodeId, agentId, skillId, json(request), json(response), status,
                latencyMs, errorCode, traceId, LocalDateTime.now().format(STAMP));
    }

    private void updateSession(long sessionId, String message, String reply, String now) {
        String addition = "用户: " + message + "\n助手: " + reply;
        Map<String, Object> row = jdbc.queryForList(
                "SELECT context_summary FROM conversation_sessions WHERE id = ?", sessionId).get(0);
        String existing = row.get("context_summary") == null ? "" : String.valueOf(row.get("context_summary"));
        String summary = (existing + "\n" + addition).trim();
        if (summary.length() > 2000) {
            summary = summary.substring(summary.length() - 2000);
        }
        jdbc.update("""
                UPDATE conversation_sessions
                SET context_summary = ?, last_message_at = ?, updated_at = ?
                WHERE id = ?
                """, summary, now, now, sessionId);
    }

    private Map<String, Object> chooseSkill(String agentCode, String message, String preferredSkill) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT s.*
                FROM agent_skills ask
                JOIN agents a ON a.id = ask.agent_id
                JOIN skills s ON s.id = ask.skill_id
                WHERE a.code = ? AND ask.enabled = 1 AND s.status = 'published'
                ORDER BY ask.priority, s.id
                """, agentCode);
        if (rows.isEmpty()) {
            return null;
        }
        if ("recommendation_agent".equals(agentCode)) {
            return rows.stream().filter(row -> "recommendation_query".equals(MarketStore.str(row.get("code"))))
                    .findFirst().orElse(rows.get(0));
        }
        if (preferredSkill != null && !preferredSkill.isBlank()) {
            for (Map<String, Object> row : rows) {
                if (preferredSkill.equals(MarketStore.str(row.get("code")))) {
                    return row;
                }
            }
        }
        boolean naturalLanguage = message.contains("以内") || message.contains("元")
                || message.contains("新") || message.contains("找") || message.contains("搜")
                || message.contains("想") || message.contains("要");
        for (Map<String, Object> row : rows) {
            String code = MarketStore.str(row.get("code"));
            if (naturalLanguage && "nl_filter".equals(code)) {
                return row;
            }
            if (!naturalLanguage && "product_query".equals(code)) {
                return row;
            }
        }
        return rows.get(0);
    }

    private Map<String, Object> compose(String intent, String subAgent, String skill, Object result) {
        List<?> items = List.of();
        if (result instanceof Map<?, ?> map && map.get("items") instanceof List<?> list) {
            items = list;
        }
        String reply = "已由 " + subAgent + " 调用 " + skill + " 完成查询";
        if (!items.isEmpty()) {
            reply += "，共找到 " + items.size() + " 件商品";
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("intent", intent);
        data.put("skill", skill);
        data.put("reply", reply);
        data.put("items", items);
        return data;
    }

    private static String classify(String message) {
        if (containsAny(message, "推荐", "适合", "喜欢", "类似", "猜你")) {
            return "recommendation";
        }
        if (containsAny(message, "订单", "购物车", "买了", "支付", "下单")) {
            return "trade";
        }
        if (containsAny(message, "我的", "资料", "偏好", "账号", "收藏")) {
            return "user";
        }
        return "product";
    }

    private static boolean containsAny(String text, String... words) {
        for (String word : words) {
            if (text.contains(word)) {
                return true;
            }
        }
        return false;
    }

    private static String defaultSkill(String intent, String message) {
        if ("recommendation".equals(intent)) {
            return "recommendation_query";
        }
        if (!"product".equals(intent)) {
            return null;
        }
        return message.contains("以内") || message.contains("元") || message.contains("新")
                || message.contains("找") || message.contains("搜") ? "nl_filter" : "product_query";
    }

    private static boolean validIntent(String value) {
        return "product".equals(value) || "recommendation".equals(value)
                || "trade".equals(value) || "user".equals(value);
    }

    private static String agentFor(String intent) {
        return switch (intent) {
            case "recommendation" -> "recommendation_agent";
            case "trade" -> "trade_agent";
            case "user" -> "user_agent";
            default -> "product_agent";
        };
    }

    private static boolean validAgent(String value) {
        return "product_agent".equals(value) || "recommendation_agent".equals(value)
                || "trade_agent".equals(value) || "user_agent".equals(value);
    }

    private static String fallback(String intent) {
        return switch (intent) {
            case "trade" -> "当前 Agent 只提供只读商品查询和推荐，订单、购物车和支付操作请在平台页面完成。";
            case "user" -> "当前 Agent 只提供只读商品查询和推荐，用户资料与偏好请在个人中心查看。";
            default -> "请告诉我你想找的商品、分类、价格或成色。";
        };
    }

    private Map<String, Object> agent(String code) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT * FROM agents WHERE code = ? AND status = 'active'", code);
        return rows.isEmpty() ? null : rows.get(0);
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

    private String json(Object value) {
        try {
            return value == null ? null : mapper.writeValueAsString(value);
        } catch (Exception exc) {
            return null;
        }
    }
}
