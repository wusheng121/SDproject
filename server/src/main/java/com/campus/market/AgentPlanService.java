package com.campus.market;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class AgentPlanService {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;

    public AgentPlanService(JdbcTemplate jdbc, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.mapper = mapper;
    }

    public long create(long sessionId, long userId, String goal, List<String> labels) {
        List<Map<String, Object>> steps = new ArrayList<>();
        for (int i = 0; i < labels.size(); i++) {
            Map<String, Object> step = new LinkedHashMap<>();
            step.put("step", i + 1);
            step.put("name", labels.get(i));
            step.put("status", "pending");
            steps.add(step);
        }
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement statement = connection.prepareStatement("""
                    INSERT INTO agent_plans
                    (session_id, user_id, goal, status, steps_json, current_step, context_json, created_at, updated_at)
                    VALUES (?, ?, ?, 'executing', ?, 0, '{}', ?, ?)
                    """, Statement.RETURN_GENERATED_KEYS);
            statement.setObject(1, sessionId);
            statement.setObject(2, userId);
            statement.setObject(3, trim(goal, 500));
            statement.setObject(4, json(steps));
            statement.setObject(5, LocalDateTime.now().format(STAMP));
            statement.setObject(6, LocalDateTime.now().format(STAMP));
            return statement;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            throw new ApiException("PLAN_WRITE_FAILED", "计划写入失败", 500);
        }
        return key.longValue();
    }

    public void finish(long planId, String status, List<String> labels) {
        List<Map<String, Object>> steps = new ArrayList<>();
        for (int i = 0; i < labels.size(); i++) {
            Map<String, Object> step = new LinkedHashMap<>();
            step.put("step", i + 1);
            step.put("name", labels.get(i));
            step.put("status", "completed");
            steps.add(step);
        }
        jdbc.update("""
                UPDATE agent_plans
                SET status = ?, current_step = ?, steps_json = ?, updated_at = ?
                WHERE id = ?
                """, status, labels.size(), json(steps), LocalDateTime.now().format(STAMP), planId);
    }

    public void completeIfNoPending(long planId) {
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM pending_actions WHERE plan_id = ? AND status = 'pending'",
                Integer.class, planId);
        if (count != null && count == 0) {
            jdbc.update("UPDATE agent_plans SET status = 'completed', updated_at = ? WHERE id = ?",
                    LocalDateTime.now().format(STAMP), planId);
        }
    }

    public void cancel(long planId) {
        jdbc.update("UPDATE pending_actions SET status = 'cancelled' WHERE plan_id = ? AND status = 'pending'", planId);
        jdbc.update("UPDATE agent_plans SET status = 'cancelled', updated_at = ? WHERE id = ?",
                LocalDateTime.now().format(STAMP), planId);
    }

    public Map<String, Object> active(long sessionId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT * FROM agent_plans
                WHERE session_id = ? AND status IN ('executing', 'awaiting_confirmation')
                ORDER BY id DESC LIMIT 1
                """, sessionId);
        if (rows.isEmpty()) {
            return null;
        }
        Map<String, Object> plan = new LinkedHashMap<>(rows.get(0));
        plan.put("steps", jsonList(plan.get("steps_json")));
        plan.remove("steps_json");
        return plan;
    }

    public Map<String, Object> latest(long sessionId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT * FROM agent_plans WHERE session_id = ? ORDER BY id DESC LIMIT 1
                """, sessionId);
        if (rows.isEmpty()) {
            return null;
        }
        Map<String, Object> plan = new LinkedHashMap<>(rows.get(0));
        plan.put("steps", jsonList(plan.get("steps_json")));
        plan.remove("steps_json");
        return plan;
    }

    public List<Map<String, Object>> pendingActions(long planId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id AS action_id, message_id, action_type, payload_json, status,
                       expires_at, executed_at, created_at
                FROM pending_actions
                WHERE plan_id = ? AND status = 'pending'
                ORDER BY id
                """, planId);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            Map<String, Object> item = new LinkedHashMap<>(row);
            item.put("type", row.get("action_type"));
            item.put("payload", jsonMap(row.get("payload_json")));
            item.remove("action_type");
            item.remove("payload_json");
            result.add(item);
        }
        return result;
    }

    private List<Map<String, Object>> jsonList(Object value) {
        try {
            return value == null || String.valueOf(value).isBlank()
                    ? List.of() : mapper.readValue(String.valueOf(value), List.class);
        } catch (Exception exc) {
            return List.of();
        }
    }

    private Map<String, Object> jsonMap(Object value) {
        try {
            return value == null || String.valueOf(value).isBlank()
                    ? Map.of() : mapper.readValue(String.valueOf(value), Map.class);
        } catch (Exception exc) {
            return Map.of();
        }
    }

    private String json(Object value) {
        try {
            return mapper.writeValueAsString(value);
        } catch (Exception exc) {
            return "[]";
        }
    }

    private static String trim(String value, int max) {
        String text = value == null ? "" : value.trim();
        return text.length() <= max ? text : text.substring(0, max);
    }
}
