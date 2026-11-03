package com.campus.market;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

@Component
public class SkillRegistry {
    private final JdbcTemplate jdbc;

    public SkillRegistry(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Map<String, Object> published(String code) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT * FROM skills WHERE code = ? AND status = 'published' LIMIT 1", code);
        return rows.isEmpty() ? null : rows.get(0);
    }

    public boolean isPublished(String code) {
        return published(code) != null;
    }

    public List<Map<String, Object>> publishedTools() {
        return jdbc.queryForList("""
                SELECT id, skill_no, code, name, module, description, input_schema_json,
                       output_schema_json, allowed_operations, forbidden_operations, scope,
                       handler_type, handler_target, version
                FROM skills
                WHERE status = 'published'
                ORDER BY id
                """);
    }
}
