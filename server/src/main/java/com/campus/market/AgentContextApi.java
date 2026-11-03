package com.campus.market;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
public class AgentContextApi {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private final JdbcTemplate jdbc;
    private final AdminGuard guard;
    private final MarketStore store;
    private final ObjectMapper mapper;

    public AgentContextApi(JdbcTemplate jdbc, AdminGuard guard, MarketStore store, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.guard = guard;
        this.store = store;
        this.mapper = mapper;
    }

    @PostMapping("/api/v1/admin/context/logs/import")
    public ResponseEntity<Map<String, Object>> importLogs(HttpServletRequest request,
                                                          @RequestBody Map<String, Object> body) {
        Map<String, Object> actor = guard.require(request, "user:manage");
        String content = MarketStore.str(body.get("content"));
        if (content.isBlank()) {
            throw new ApiException("VALIDATION_ERROR", "日志内容不能为空", 422);
        }
        if (content.length() > 2_000_000) {
            throw new ApiException("VALIDATION_ERROR", "单次日志不能超过 2MB", 422);
        }
        String filename = valueOr(body.get("filename"), "uploaded.log");
        String hash = Tokens.sha256(content);
        List<Map<String, Object>> existing = jdbc.queryForList(
                "SELECT * FROM context_artifacts WHERE content_hash = ?", hash);
        if (!existing.isEmpty()) {
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("duplicate", true);
            data.put("artifact_id", existing.get(0).get("id"));
            return ResponseEntity.ok(Map.of("data", data));
        }

        Parsed parsed = parse(content);
        String redacted = redact(content);
        Long sessionId = resolveSession(body.get("session_id"), parsed.sessionId);
        String summary = summarize(parsed, redacted);
        String id;
        try {
            jdbc.update("""
                    INSERT INTO context_artifacts
                    (session_id, source_type, source_ref, content_hash, raw_storage_key,
                     raw_content, extracted_json, summary, status, created_at)
                    VALUES (?, 'uploaded_file', ?, ?, NULL, ?, ?, ?, 'ready', ?)
                    """, sessionId, filename.substring(0, Math.min(filename.length(), 255)), hash,
                    redacted, json(parsed.toMap()), summary, LocalDateTime.now().format(STAMP));
            id = String.valueOf(jdbc.queryForObject(
                    "SELECT id FROM context_artifacts WHERE content_hash = ?", Long.class, hash));
        } catch (DuplicateKeyException exc) {
            id = String.valueOf(jdbc.queryForList(
                    "SELECT id FROM context_artifacts WHERE content_hash = ?", hash).get(0).get("id"));
        }

        if (sessionId != null) {
            appendSummary(sessionId, summary);
        }
        store.writeLog(actor, "context.log.import", "context_artifact", id);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("duplicate", false);
        data.put("artifact_id", id);
        data.put("session_id", sessionId);
        data.put("lines", parsed.lines);
        data.put("errors", parsed.errors);
        data.put("summary", summary);
        return ResponseEntity.status(201).body(Map.of("data", data));
    }

    @GetMapping("/api/v1/admin/context/logs")
    public Map<String, Object> logs(HttpServletRequest request,
                                    @RequestParam(name = "session_id", required = false) Long sessionId,
                                    @RequestParam(defaultValue = "1") int page,
                                    @RequestParam(name = "page_size", defaultValue = "20") int pageSize) {
        guard.require(request, "user:manage");
        page = Math.max(page, 1);
        pageSize = Math.min(Math.max(pageSize, 1), 100);
        String where = sessionId == null ? "" : " WHERE session_id = ?";
        Object[] args = sessionId == null ? new Object[0] : new Object[]{sessionId};
        Integer total = jdbc.queryForObject("SELECT COUNT(*) FROM context_artifacts" + where, Integer.class, args);
        List<Object> pageArgs = new ArrayList<>(List.of(args));
        pageArgs.add(pageSize);
        pageArgs.add((page - 1) * pageSize);
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, session_id, source_type, source_ref, content_hash, summary,
                       status, created_at
                FROM context_artifacts
                """ + where + " ORDER BY id DESC LIMIT ? OFFSET ?", pageArgs.toArray());
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("data", rows);
        result.put("pagination", Map.of("page", page, "page_size", pageSize, "total", total == null ? 0 : total));
        return result;
    }

    @GetMapping("/api/v1/admin/context/sessions/{id}")
    public Map<String, Object> sessionDetail(HttpServletRequest request, @PathVariable long id) {
        guard.require(request, "user:manage");
        List<Map<String, Object>> sessions = jdbc.queryForList(
                "SELECT * FROM conversation_sessions WHERE id = ?", id);
        if (sessions.isEmpty()) {
            throw new ApiException("NOT_FOUND", "会话不存在", 404);
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("session", sessions.get(0));
        data.put("messages", jdbc.queryForList(
                "SELECT * FROM conversation_messages WHERE session_id = ? ORDER BY id", id));
        data.put("nodes", jdbc.queryForList(
                "SELECT * FROM conversation_nodes WHERE session_id = ? ORDER BY id", id));
        data.put("tool_calls", jdbc.queryForList(
                "SELECT * FROM agent_tool_calls WHERE session_id = ? ORDER BY id", id));
        data.put("artifacts", jdbc.queryForList("""
                SELECT id, source_type, source_ref, summary, status, created_at
                FROM context_artifacts WHERE session_id = ? ORDER BY id
                """, id));
        return Map.of("data", data);
    }

    private Parsed parse(String content) {
        Parsed result = new Parsed();
        for (String line : content.split("\\r?\\n")) {
            if (line.isBlank()) {
                continue;
            }
            result.lines++;
            try {
                @SuppressWarnings("unchecked")
                Map<String, Object> item = mapper.readValue(line, Map.class);
                result.parsed++;
                if (result.traceId.isBlank() && item.get("trace_id") != null) {
                    result.traceId = String.valueOf(item.get("trace_id"));
                }
                if (result.sessionId == null && item.get("session_id") != null) {
                    result.sessionId = MarketStore.num(item.get("session_id"));
                }
                String level = MarketStore.str(item.get("level"));
                if ("ERROR".equalsIgnoreCase(level) || "FATAL".equalsIgnoreCase(level)
                        || item.get("error") != null) {
                    result.errors++;
                }
            } catch (Exception ignored) {
                if (line.contains("ERROR") || line.contains("Exception")) {
                    result.errors++;
                }
            }
        }
        return result;
    }

    private Long resolveSession(Object raw, Long parsedSessionId) {
        Long id = raw == null || String.valueOf(raw).isBlank() ? parsedSessionId : MarketStore.num(raw);
        if (id == null) {
            return null;
        }
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM conversation_sessions WHERE id = ?", Integer.class, id);
        return count != null && count > 0 ? id : null;
    }

    private void appendSummary(long sessionId, String summary) {
        Map<String, Object> row = jdbc.queryForList(
                "SELECT context_summary FROM conversation_sessions WHERE id = ?", sessionId).get(0);
        String existing = row.get("context_summary") == null ? "" : String.valueOf(row.get("context_summary"));
        String value = (existing + "\n[日志] " + summary).trim();
        if (value.length() > 4000) {
            value = value.substring(value.length() - 4000);
        }
        jdbc.update("UPDATE conversation_sessions SET context_summary = ?, updated_at = ? WHERE id = ?",
                value, LocalDateTime.now().format(STAMP), sessionId);
    }

    private static String summarize(Parsed parsed, String content) {
        String first = content.replaceAll("\\s+", " ").trim();
        if (first.length() > 500) {
            first = first.substring(0, 500) + "...";
        }
        return "行数=" + parsed.lines + "，JSON=" + parsed.parsed + "，错误=" + parsed.errors + "；" + first;
    }

    private static String redact(String content) {
        return content
                .replaceAll("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", "[email]")
                .replaceAll("\\b1[3-9]\\d{9}\\b", "[phone]");
    }

    private String json(Object value) {
        try {
            return value == null ? null : mapper.writeValueAsString(value);
        } catch (Exception exc) {
            return null;
        }
    }

    private static String valueOr(Object value, String fallback) {
        String text = MarketStore.str(value);
        return text.isBlank() ? fallback : text;
    }

    private static final class Parsed {
        private int lines;
        private int parsed;
        private int errors;
        private String traceId = "";
        private Long sessionId;

        private Map<String, Object> toMap() {
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("lines", lines);
            data.put("json_lines", parsed);
            data.put("errors", errors);
            data.put("trace_id", traceId.isBlank() ? null : traceId);
            data.put("session_id", sessionId);
            return data;
        }
    }
}
