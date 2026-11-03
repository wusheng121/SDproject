package com.campus.market;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@ExtendWith(MockitoExtension.class)
class SkillAdminApiTest {
    @Mock
    private JdbcTemplate jdbc;
    @Mock
    private AdminGuard guard;
    @Mock
    private AgentApi agentApi;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        SkillAdminApi api = new SkillAdminApi(jdbc, guard, agentApi, new ObjectMapper());
        mvc = MockMvcBuilders.standaloneSetup(api).build();
        when(guard.require(any(), anyString())).thenReturn(Map.of("id", 2, "username", "admin"));
    }

    @Test
    void listsSkillsWithPagination() throws Exception {
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class))).thenReturn(1);
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenReturn(List.of(skill(1L, "product_query")));

        mvc.perform(get("/api/v1/admin/skills").param("page_size", "20"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].code").value("product_query"))
                .andExpect(jsonPath("$.pagination.total").value(1));
    }

    @Test
    void createsDraftSkillAndAudits() throws Exception {
        when(jdbc.update(anyString(), any(Object[].class))).thenReturn(1);
        when(jdbc.queryForList(anyString(), any(Object[].class)))
                .thenReturn(List.of(skill(7L, "new_skill")));

        String body = """
                {
                  "skill_no": "SK-007",
                  "code": "new_skill",
                  "name": "新技能",
                  "module": "product",
                  "scope": "product:view",
                  "handler_type": "java",
                  "handler_target": "product_query"
                }
                """;

        mvc.perform(post("/api/v1/admin/skills")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.code").value("new_skill"))
                .andExpect(jsonPath("$.data.status").value("draft"));
    }

    private static Map<String, Object> skill(long id, String code) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("id", id);
        data.put("code", code);
        data.put("name", "商品查询");
        data.put("module", "product");
        data.put("status", "draft");
        return data;
    }
}
