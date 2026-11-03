# Agent-Skill-MCP 实现说明

- 日期：2026-11-02
- 对应方案：`Agent改造方案.md`
- 当前状态：Phase 1-4 已完成主要功能，Phase 5 文档与验收材料进行中

## 一、已实现范围

### 1. Skill 注册中心

数据库表：

- `agents`
- `skills`
- `agent_skills`

已内置：

| 编号 | Code | 模块 | Scope |
|---|---|---|---|
| SK-001 | `product_query` | product | `product:view` |
| SK-002 | `nl_filter` | product | `product:view` |
| SK-003 | `recommendation_query` | recommendation | `recommendation:query` |
| SK-004 | `product_recognize` | product | `product:view` |

内置 Agent：

- `main_agent`
- `product_agent`
- `recommendation_agent`
- `trade_agent`
- `user_agent`
- `admin_read_agent`

管理接口：

```text
GET    /api/v1/admin/skills
GET    /api/v1/admin/skills/{id}
POST   /api/v1/admin/skills
PUT    /api/v1/admin/skills/{id}
POST   /api/v1/admin/skills/{id}/publish
POST   /api/v1/admin/skills/{id}/disable
POST   /api/v1/admin/skills/{id}/test
```

权限：

```text
skill:view
skill:manage
skill:test
```

只有管理员拥有写权限。Skill 写入和发布操作写 `operation_logs`。

管理页面：

```text
/admin -> Skill 管理
```

支持列表、筛选、新建、编辑、发布、禁用、测试。

### 2. Agent API Key

接口：

```text
GET    /api/v1/users/me/api-keys
POST   /api/v1/users/me/api-keys
DELETE /api/v1/users/me/api-keys/{id}

GET    /api/v1/admin/agent-users
GET    /api/v1/admin/agent-users/{userId}/api-keys
POST   /api/v1/admin/agent-users/{userId}/api-keys
DELETE /api/v1/admin/agent-users/{userId}/api-keys/{id}
```

规则：

- 仅 `agent_service` 和 `admin` 可创建
- 完整 Key 只返回一次
- 数据库保存 SHA-256 hash 和 prefix
- 支持 scopes、过期时间、吊销、最后使用时间
- Agent 请求支持：
  - `X-API-Key: cmk_xxx.yyy`
  - `Authorization: Bearer cmk_xxx.yyy`
- 校验 Key 状态、过期时间、账号状态、scope
- 默认有效期 30 天，`expires_in_days=0` 表示永不过期

管理页面：

```text
/admin -> Agent 接入
```

### 3. 最小 MCP Server

接口：

```text
POST /api/v1/mcp
GET  /api/v1/mcp/sse
```

方法：

```text
initialize
ping
tools/list
tools/call
notifications/initialized
```

协议版本：

```text
2024-11-05
```

鉴权：

```http
Authorization: Bearer <agent_api_key>
```

兼容：

```http
X-API-Key: <agent_api_key>
```

`tools/list` 只返回 `status='published'` 的 Skill。

`tools/call` 流程：

```text
校验 Key
-> 查找已发布 Skill
-> 校验 scope
-> 调用对应 handler
-> 写审计日志
-> 返回 content + structuredContent
```

工具全部只读，禁止：

- 删除用户
- 修改密码
- 批量修改关键数据
- 角色提权
- 真实支付

### 4. 主 Agent + 子 Agent

接口：

```text
POST /api/v1/agent/orchestrate
```

请求：

```json
{
  "message": "帮我找500元以内的手机",
  "session_id": 1
}
```

返回：

```json
{
  "data": {
    "session_id": 1,
    "trace_id": "...",
    "agent": "main_agent",
    "sub_agent": "product_agent",
    "intent": "product",
    "intent_source": "llm",
    "skill": "nl_filter",
    "reply": "已由 product_agent 调用 nl_filter 完成查询，共找到 0 件商品",
    "items": [],
    "result": {}
  }
}
```

路由：

```text
明确规则优先
-> Python /api/ai/intent 调 DeepSeek
-> 失败回退规则
-> 商品类有明确价格/关键词时强制走规则，避免误判为推荐
```

子 Agent 只能调用 `agent_skills` 中启用且已发布的 Skill。

### 5. 上下文持久化

数据库表：

- `conversation_sessions`
- `conversation_messages`
- `conversation_nodes`
- `agent_tool_calls`
- `context_artifacts`

每次编排记录：

- 用户消息
- 意图节点
- 工具调用节点
- 工具入参/出参
- 助手回复
- trace_id
- 会话摘要

日志导入（可选 API，管理后台页面已移除）：

```text
POST /api/v1/admin/context/logs/import
```

支持 JSON Lines 和普通文本：

- 自动脱敏邮箱、手机号
- 按 SHA-256 去重
- 解析 `trace_id`、`session_id`、错误数量
- 写入 `context_artifacts`
- 可关联到对话会话
- 追加到会话上下文摘要

查询：

```text
GET /api/v1/admin/context/logs
GET /api/v1/admin/context/sessions/{id}
```

后台“上下文”页面已移除，日志导入和会话节点查看仅保留 API。

## 二、演示步骤

```text
1. 管理员登录 /admin
2. 进入 Skill 管理
3. 查看 SK-001 ~ SK-004
4. 新建一个草稿 Skill
5. 发布 Skill
6. 执行测试
7. 进入 Agent 接入
8. 选择 agent 服务账号
9. 创建 API Key，复制完整 Key
10. 用 MCP Inspector 连接 http://127.0.0.1:8080/api/v1/mcp
11. 添加 Authorization: Bearer <key>
12. initialize
13. tools/list
14. tools/call product_query
15. 调用 /api/v1/agent/orchestrate
16. 查看操作日志
```

## 三、MCP Inspector 配置

传输：

```text
HTTP
```

URL：

```text
http://127.0.0.1:8080/api/v1/mcp
```

Header：

```http
Authorization: Bearer cmk_xxx.yyy
```

## 四、当前限制

- 未实现按 Key 维度的限流
- 未实现 MCP resources/prompts，仅 tools
- 未实现 RabbitMQ 异步日志处理，当前同步导入
- 未实现向量检索，只保存结构化摘要
- 未实现完整 LLM 多轮规划，只做意图路由
- 未实现 Skill 删除，只有禁用和发布
- 当前 PowerShell 环境 `npm run build` 偶发挂起，已验证 `node ./node_modules/vite/bin/vite.js build` 可正常完成

## 五、验证结果

已实际验证：

- Skill 列表、创建、编辑、发布、禁用、测试
- Agent API Key 创建、scope 校验、吊销
- MCP initialize、tools/list、tools/call
- 主 Agent 规则 + LLM 混合路由
- 商品查询与推荐子 Agent 路由
- 会话消息、节点、工具调用落库
- 日志文件导入、脱敏、去重
- 管理后台前端构建
