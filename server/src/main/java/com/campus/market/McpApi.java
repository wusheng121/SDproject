package com.campus.market;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/mcp")
public class McpApi {
    private static final String PROTOCOL_VERSION = "2024-11-05";
    private final JdbcTemplate jdbc;
    private final AgentAuth auth;
    private final AgentApi agentApi;
    private final MarketStore store;
    private final ObjectMapper mapper;

    public McpApi(JdbcTemplate jdbc, AgentAuth auth, AgentApi agentApi, MarketStore store, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.auth = auth;
        this.agentApi = agentApi;
        this.store = store;
        this.mapper = mapper;
    }

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Object> rpc(HttpServletRequest request, @RequestBody Map<String, Object> body) {
        AgentAuth.Principal principal = auth.authenticate(request);
        Object id = body.get("id");
        String method = MarketStore.str(body.get("method"));
        Map<String, Object> params = body.get("params") instanceof Map<?, ?> raw ? stringMap(raw) : Map.of();

        if (id == null && method.startsWith("notifications/")) {
            return ResponseEntity.noContent().build();
        }

        try {
            Object result = switch (method) {
                case "initialize" -> initialize();
                case "ping" -> Map.of();
                case "tools/list" -> Map.of("tools", tools());
                case "tools/call" -> callTool(principal, params);
                default -> throw new RpcException(-32601, "Method not found: " + method);
            };
            Map<String, Object> response = new LinkedHashMap<>();
            response.put("jsonrpc", "2.0");
            response.put("id", id);
            response.put("result", result);
            return ResponseEntity.ok(response);
        } catch (RpcException exc) {
            return ResponseEntity.ok(error(id, exc.code, exc.getMessage()));
        } catch (ApiException exc) {
            return ResponseEntity.ok(error(id, -32000, exc.getMessage()));
        } catch (Exception exc) {
            return ResponseEntity.ok(error(id, -32603, "Internal error"));
        }
    }

    @GetMapping(value = "/sse", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter sse(HttpServletRequest request) {
        auth.authenticate(request);
        SseEmitter emitter = new SseEmitter(0L);
        try {
            emitter.send(SseEmitter.event().name("endpoint").data("/api/v1/mcp"));
        } catch (Exception exc) {
            emitter.completeWithError(exc);
        }
        return emitter;
    }

    private Map<String, Object> initialize() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("protocolVersion", PROTOCOL_VERSION);
        result.put("capabilities", Map.of("tools", Map.of("listChanged", false)));
        result.put("serverInfo", Map.of("name", "campus-market-mcp", "version", "0.1.0"));
        result.put("instructions", "校园二手交易平台只读工具集。禁止删除用户、修改密码、批量写入和提权。");
        return result;
    }

    private List<Map<String, Object>> tools() {
        List<Map<String, Object>> tools = new ArrayList<>();
        for (Map<String, Object> row : jdbc.queryForList(
                "SELECT * FROM skills WHERE status = 'published' ORDER BY id")) {
            Map<String, Object> tool = new LinkedHashMap<>();
            tool.put("name", row.get("code"));
            tool.put("title", row.get("name"));
            tool.put("description", row.get("description"));
            tool.put("inputSchema", jsonObject(row.get("input_schema_json")));
            tool.put("annotations", Map.of("readOnlyHint", true));
            tools.add(tool);
        }
        return tools;
    }

    private Map<String, Object> callTool(AgentAuth.Principal principal, Map<String, Object> params) {
        String name = MarketStore.str(params.get("name"));
        if (name.isBlank()) {
            throw new RpcException(-32602, "tools/call 缺少 name");
        }
        Map<String, Object> arguments = params.get("arguments") instanceof Map<?, ?> raw
                ? stringMap(raw) : Map.of();
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT * FROM skills WHERE code = ? AND status = 'published' LIMIT 1", name);
        if (rows.isEmpty()) {
            throw new ApiException("SKILL_NOT_FOUND", "Skill 不存在或未发布", 404);
        }
        Map<String, Object> skill = rows.get(0);
        auth.requireScope(principal, MarketStore.str(skill.get("scope")));
        String handler = MarketStore.str(skill.get("handler_target"));
        if (handler.isBlank()) {
            handler = name;
        }

        try {
            Map<String, Object> output = agentApi.executeSkill(handler, arguments,
                    MarketStore.num(principal.user().get("id")));
            store.writeLog(principal.user(), "agent.mcp.tools.call", "skill", name);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("content", List.of(Map.of("type", "text", "text", json(output))));
            result.put("structuredContent", output);
            result.put("isError", false);
            return result;
        } catch (ApiException exc) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("content", List.of(Map.of("type", "text", "text", exc.getMessage())));
            result.put("isError", true);
            return result;
        }
    }

    private Object jsonObject(Object value) {
        try {
            return mapper.readTree(MarketStore.str(value).isBlank() ? "{\"type\":\"object\"}" : String.valueOf(value));
        } catch (Exception exc) {
            return Map.of("type", "object");
        }
    }

    private String json(Object value) {
        try {
            return mapper.writeValueAsString(value);
        } catch (Exception exc) {
            return "{}";
        }
    }

    private static Map<String, Object> error(Object id, int code, String message) {
        Map<String, Object> error = new LinkedHashMap<>();
        error.put("code", code);
        error.put("message", message);
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("jsonrpc", "2.0");
        response.put("id", id);
        response.put("error", error);
        return response;
    }

    private static Map<String, Object> stringMap(Map<?, ?> raw) {
        Map<String, Object> data = new LinkedHashMap<>();
        raw.forEach((key, value) -> data.put(String.valueOf(key), value));
        return data;
    }

    private static final class RpcException extends RuntimeException {
        private final int code;

        private RpcException(int code, String message) {
            super(message);
            this.code = code;
        }
    }
}
