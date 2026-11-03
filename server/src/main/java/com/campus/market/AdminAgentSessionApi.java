package com.campus.market;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
public class AdminAgentSessionApi {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private final JdbcTemplate jdbc;
    private final AdminGuard guard;
    private final MarketStore store;

    public AdminAgentSessionApi(JdbcTemplate jdbc, AdminGuard guard, MarketStore store) {
        this.jdbc = jdbc;
        this.guard = guard;
        this.store = store;
    }

    @GetMapping("/api/v1/admin/agent-sessions")
    public Map<String, Object> list(HttpServletRequest request,
                                    @RequestParam(required = false) String keyword,
                                    @RequestParam(defaultValue = "1") int page,
                                    @RequestParam(name = "page_size", defaultValue = "20") int pageSize) {
        guard.require(request, "user:manage");
        page = Math.max(page, 1);
        pageSize = Math.min(Math.max(pageSize, 1), 100);
        StringBuilder where = new StringBuilder(" WHERE s.deleted_at IS NULL");
        List<Object> args = new ArrayList<>();
        if (keyword != null && !keyword.isBlank()) {
            where.append(" AND (s.title LIKE ? OR u.username LIKE ? OR s.agent_code LIKE ?)");
            String like = "%" + keyword.trim() + "%";
            args.add(like);
            args.add(like);
            args.add(like);
        }
        Integer total = jdbc.queryForObject(
                "SELECT COUNT(*) FROM conversation_sessions s JOIN users u ON u.id = s.user_id" + where,
                Integer.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(pageSize);
        pageArgs.add((page - 1) * pageSize);
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT s.id, s.user_id, u.username, s.agent_code, s.title, s.status,
                       s.created_at, s.updated_at,
                       (SELECT COUNT(*) FROM conversation_messages m WHERE m.session_id = s.id) AS message_count,
                       (SELECT LEFT(m.content, 120) FROM conversation_messages m
                        WHERE m.session_id = s.id ORDER BY m.id DESC LIMIT 1) AS last_message
                FROM conversation_sessions s
                JOIN users u ON u.id = s.user_id
                """ + where + " ORDER BY s.updated_at DESC, s.id DESC LIMIT ? OFFSET ?", pageArgs.toArray());
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("data", rows);
        data.put("pagination", Map.of("page", page, "page_size", pageSize, "total", total == null ? 0 : total));
        return data;
    }

    @GetMapping("/api/v1/admin/agent-sessions/{id}")
    public Map<String, Object> detail(HttpServletRequest request, @PathVariable long id) {
        guard.require(request, "user:manage");
        List<Map<String, Object>> sessions = jdbc.queryForList("""
                SELECT s.*, u.username
                FROM conversation_sessions s JOIN users u ON u.id = s.user_id
                WHERE s.id = ? AND s.deleted_at IS NULL
                """, id);
        if (sessions.isEmpty()) {
            throw new ApiException("NOT_FOUND", "Agent 会话不存在", 404);
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("session", sessions.get(0));
        data.put("messages", jdbc.queryForList("""
                SELECT id, role, content, content_type, metadata_json, created_at
                FROM conversation_messages WHERE session_id = ? ORDER BY id
                """, id));
        data.put("actions", jdbc.queryForList("""
                SELECT id, action_type, status, payload_json, created_at, executed_at
                FROM pending_actions WHERE session_id = ? ORDER BY id DESC
                """, id));
        data.put("nodes", jdbc.queryForList("""
                SELECT id, node_type, status, content_json, created_at
                FROM conversation_nodes WHERE session_id = ? ORDER BY id
                """, id));
        return Map.of("data", data);
    }

    @DeleteMapping("/api/v1/admin/agent-sessions/{id}")
    public Map<String, Object> delete(HttpServletRequest request, @PathVariable long id) {
        Map<String, Object> actor = guard.require(request, "user:manage");
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT id FROM conversation_sessions WHERE id = ? AND deleted_at IS NULL", id);
        if (rows.isEmpty()) {
            throw new ApiException("NOT_FOUND", "Agent 会话不存在", 404);
        }
        jdbc.update("UPDATE conversation_sessions SET deleted_at = ?, deleted_by = ? WHERE id = ?",
                LocalDateTime.now().format(STAMP), MarketStore.num(actor.get("id")), id);
        jdbc.update("UPDATE pending_actions SET status = 'cancelled' WHERE session_id = ? AND status = 'pending'", id);
        store.writeLog(actor, "admin.agent.session.delete", "agent_session", String.valueOf(id));
        return Map.of("data", Map.of("deleted", true, "session_id", id));
    }
}
