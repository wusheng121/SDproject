package com.campus.market;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/admin/skills")
public class SkillAdminApi {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final List<String> MODULES = List.of("product", "trade", "recommendation", "user", "admin", "system");
    private static final List<String> HANDLERS = List.of("java", "python_http");
    private final JdbcTemplate jdbc;
    private final AdminGuard guard;
    private final AgentApi agentApi;
    private final ObjectMapper mapper;

    public SkillAdminApi(JdbcTemplate jdbc, AdminGuard guard, AgentApi agentApi, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.guard = guard;
        this.agentApi = agentApi;
        this.mapper = mapper;
    }

    @GetMapping
    public Map<String, Object> list(HttpServletRequest request,
                                    @RequestParam(required = false) String keyword,
                                    @RequestParam(required = false) String module,
                                    @RequestParam(required = false) String status,
                                    @RequestParam(defaultValue = "1") int page,
                                    @RequestParam(name = "page_size", defaultValue = "20") int pageSize) {
        guard.require(request, "skill:view");
        page = Math.max(page, 1);
        pageSize = Math.min(Math.max(pageSize, 1), 100);

        StringBuilder from = new StringBuilder(" FROM skills WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (keyword != null && !keyword.isBlank()) {
            from.append(" AND (code LIKE ? OR name LIKE ? OR skill_no LIKE ?)");
            String like = "%" + keyword.trim() + "%";
            args.add(like);
            args.add(like);
            args.add(like);
        }
        if (module != null && !module.isBlank()) {
            from.append(" AND module = ?");
            args.add(module.trim());
        }
        if (status != null && !status.isBlank()) {
            from.append(" AND status = ?");
            args.add(status.trim());
        }

        Integer total = jdbc.queryForObject("SELECT COUNT(*)" + from, Integer.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(pageSize);
        pageArgs.add((page - 1) * pageSize);
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT *" + from + " ORDER BY id DESC LIMIT ? OFFSET ?", pageArgs.toArray());

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("data", rows);
        body.put("pagination", Map.of("page", page, "page_size", pageSize, "total", total == null ? 0 : total));
        return body;
    }

    @GetMapping("/{id}")
    public Map<String, Object> detail(HttpServletRequest request, @PathVariable long id) {
        guard.require(request, "skill:view");
        Map<String, Object> skill = skill(id);
        if (skill == null) {
            throw new ApiException("NOT_FOUND", "Skill 不存在", 404);
        }
        return Map.of("data", skill);
    }

    @PostMapping
    public ResponseEntity<Map<String, Object>> create(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        Map<String, Object> actor = guard.require(request, "skill:manage");
        String code = normalizedCode(body.get("code"));
        String name = required(body.get("name"), "Skill 名称不能为空");
        String module = required(body.get("module"), "Skill 模块不能为空");
        if (!MODULES.contains(module)) {
            throw new ApiException("VALIDATION_ERROR", "不支持的 Skill 模块", 422);
        }
        String handlerType = valueOr(body.get("handler_type"), "java");
        if (!HANDLERS.contains(handlerType)) {
            throw new ApiException("VALIDATION_ERROR", "不支持的 handler 类型", 422);
        }
        String scope = normalizeScope(MarketStore.str(body.get("scope")));
        String inputSchema = jsonText(body.get("input_schema_json"), "{}");
        String outputSchema = jsonText(body.get("output_schema_json"), "{}");

        try {
            jdbc.update("""
                    INSERT INTO skills (
                        skill_no, code, name, module, description, input_schema_json,
                        output_schema_json, allowed_operations, forbidden_operations, scope,
                        handler_type, handler_target, status, version, created_by, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', 1, ?, ?, ?)
                    """,
                    nullable(body.get("skill_no")), code, name, module, nullable(body.get("description")),
                    inputSchema, outputSchema, nullable(body.get("allowed_operations")),
                    nullable(body.get("forbidden_operations")), scope, handlerType,
                    valueOr(body.get("handler_target"), code), MarketStore.num(actor.get("id")),
                    LocalDateTime.now().format(STAMP), LocalDateTime.now().format(STAMP));
        } catch (DuplicateKeyException exc) {
            throw new ApiException("SKILL_EXISTS", "Skill code 已存在", 409);
        }

        Map<String, Object> created = skillByCode(code);
        audit(actor, "skill.create", String.valueOf(created.get("id")), null, json(created));
        return ResponseEntity.status(201).body(Map.of("data", created));
    }

    @PutMapping("/{id}")
    public Map<String, Object> update(HttpServletRequest request, @PathVariable long id, @RequestBody Map<String, Object> body) {
        Map<String, Object> actor = guard.require(request, "skill:manage");
        Map<String, Object> before = skill(id);
        if (before == null) {
            throw new ApiException("NOT_FOUND", "Skill 不存在", 404);
        }

        String name = required(body.get("name"), "Skill 名称不能为空");
        String module = required(body.get("module"), "Skill 模块不能为空");
        if (!MODULES.contains(module)) {
            throw new ApiException("VALIDATION_ERROR", "不支持的 Skill 模块", 422);
        }
        String handlerType = valueOr(body.get("handler_type"), "java");
        if (!HANDLERS.contains(handlerType)) {
            throw new ApiException("VALIDATION_ERROR", "不支持的 handler 类型", 422);
        }
        String scope = normalizeScope(MarketStore.str(body.get("scope")));

        jdbc.update("""
                UPDATE skills
                SET skill_no = ?, name = ?, module = ?, description = ?, input_schema_json = ?,
                    output_schema_json = ?, allowed_operations = ?, forbidden_operations = ?,
                    scope = ?, handler_type = ?, handler_target = ?, version = version + 1, updated_at = ?
                WHERE id = ?
                """,
                nullable(body.get("skill_no")), name, module, nullable(body.get("description")),
                jsonText(body.get("input_schema_json"), "{}"), jsonText(body.get("output_schema_json"), "{}"),
                nullable(body.get("allowed_operations")), nullable(body.get("forbidden_operations")),
                scope, handlerType, valueOr(body.get("handler_target"), MarketStore.str(before.get("code"))),
                LocalDateTime.now().format(STAMP), id);

        Map<String, Object> after = skill(id);
        audit(actor, "skill.update", String.valueOf(id), json(before), json(after));
        return Map.of("data", after);
    }

    @PostMapping("/{id}/publish")
    public Map<String, Object> publish(HttpServletRequest request, @PathVariable long id) {
        Map<String, Object> actor = guard.require(request, "skill:manage");
        Map<String, Object> before = skill(id);
        if (before == null) {
            throw new ApiException("NOT_FOUND", "Skill 不存在", 404);
        }
        String status = MarketStore.str(before.get("status"));
        if (!"draft".equals(status) && !"disabled".equals(status)) {
            throw new ApiException("SKILL_STATUS_INVALID", "只有草稿或已禁用的 Skill 可以发布", 422);
        }
        jdbc.update("UPDATE skills SET status = 'published', updated_at = ? WHERE id = ?",
                LocalDateTime.now().format(STAMP), id);
        Map<String, Object> after = skill(id);
        audit(actor, "skill.publish", String.valueOf(id), json(before), json(after));
        return Map.of("data", after);
    }

    @PostMapping("/{id}/disable")
    public Map<String, Object> disable(HttpServletRequest request, @PathVariable long id) {
        Map<String, Object> actor = guard.require(request, "skill:manage");
        Map<String, Object> before = skill(id);
        if (before == null) {
            throw new ApiException("NOT_FOUND", "Skill 不存在", 404);
        }
        if (!"published".equals(MarketStore.str(before.get("status")))) {
            throw new ApiException("SKILL_STATUS_INVALID", "只有已发布的 Skill 可以禁用", 422);
        }
        jdbc.update("UPDATE skills SET status = 'disabled', updated_at = ? WHERE id = ?",
                LocalDateTime.now().format(STAMP), id);
        Map<String, Object> after = skill(id);
        audit(actor, "skill.disable", String.valueOf(id), json(before), json(after));
        return Map.of("data", after);
    }

    @PostMapping("/{id}/test")
    public Map<String, Object> test(HttpServletRequest request, @PathVariable long id, @RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> actor = guard.require(request, "skill:test");
        Map<String, Object> skill = skill(id);
        if (skill == null) {
            throw new ApiException("NOT_FOUND", "Skill 不存在", 404);
        }
        if ("disabled".equals(MarketStore.str(skill.get("status")))) {
            throw new ApiException("SKILL_DISABLED", "已禁用的 Skill 不能测试", 422);
        }
        Map<String, Object> params = body != null && body.get("params") instanceof Map<?, ?> raw
                ? stringMap(raw) : Map.of();
        String handler = valueOr(skill.get("handler_target"), MarketStore.str(skill.get("code")));
        long started = System.currentTimeMillis();
        Object result = agentApi.executeSkill(handler, params, MarketStore.num(actor.get("id")));
        long latency = System.currentTimeMillis() - started;

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("skill", skill.get("code"));
        data.put("handler", handler);
        data.put("latency_ms", latency);
        data.put("result", result);
        audit(actor, "skill.test", String.valueOf(id), null, json(data));
        return Map.of("data", data);
    }

    private Map<String, Object> skill(long id) {
        List<Map<String, Object>> rows = jdbc.queryForList("SELECT * FROM skills WHERE id = ?", id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private Map<String, Object> skillByCode(String code) {
        return jdbc.queryForList("SELECT * FROM skills WHERE code = ?", code).get(0);
    }

    private void audit(Map<String, Object> actor, String action, String resourceId, String before, String after) {
        jdbc.update("""
                INSERT INTO operation_logs
                (actor_id, actor_snapshot, action, resource_type, resource_id, before_json, after_json, created_at)
                VALUES (?, ?, ?, 'skill', ?, ?, ?, ?)
                """, MarketStore.num(actor.get("id")), actor.get("username"), action, resourceId,
                before, after, LocalDateTime.now().format(STAMP));
    }

    private String json(Object value) {
        try {
            return value == null ? null : mapper.writeValueAsString(value);
        } catch (Exception exc) {
            return null;
        }
    }

    private String jsonText(Object value, String fallback) {
        if (value == null || String.valueOf(value).isBlank()) {
            return fallback;
        }
        String text = value instanceof String ? String.valueOf(value).trim() : json(value);
        try {
            mapper.readTree(text);
            return text;
        } catch (Exception exc) {
            throw new ApiException("VALIDATION_ERROR", "JSON Schema 格式不正确", 422);
        }
    }

    private String normalizedCode(Object value) {
        String code = required(value, "Skill code 不能为空");
        if (!code.matches("^[a-z][a-z0-9_]{1,63}$")) {
            throw new ApiException("VALIDATION_ERROR", "Skill code 只能使用小写字母、数字和下划线", 422);
        }
        return code;
    }

    private String normalizeScope(String scope) {
        if (scope == null || scope.isBlank()) {
            return "";
        }
        for (String item : scope.split(",")) {
            if (!item.trim().matches("^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$")) {
                throw new ApiException("VALIDATION_ERROR", "scope 格式应为 domain:action", 422);
            }
        }
        return String.join(",", java.util.Arrays.stream(scope.split(",")).map(String::trim).filter(s -> !s.isBlank()).toList());
    }

    private static String required(Object value, String message) {
        String text = MarketStore.str(value);
        if (text.isBlank()) {
            throw new ApiException("VALIDATION_ERROR", message, 422);
        }
        return text;
    }

    private static String valueOr(Object value, String fallback) {
        String text = MarketStore.str(value);
        return text.isBlank() ? fallback : text;
    }

    private static String nullable(Object value) {
        String text = MarketStore.str(value);
        return text.isBlank() ? null : text;
    }

    private static Map<String, Object> stringMap(Map<?, ?> raw) {
        Map<String, Object> data = new LinkedHashMap<>();
        raw.forEach((key, value) -> data.put(String.valueOf(key), value));
        return data;
    }
}
