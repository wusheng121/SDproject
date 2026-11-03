# Agent 改造方案

- 日期：2026-11-02
- 实施状态：Phase 1-4 已完成主要功能，详见 `docs/agent-skill-mcp.md`
- 复杂用户 Agent：已实现商品链接分析、对比、建议、卖家问题、加购/消息确认，详见 `docs/complex-agent.md`
- 助手统一：快速问答、识图、复杂任务已合并到 `/assistant`，Java 统一会话，Python 仅保留无状态 AI 接口
- 管理后台新增 Agent 会话查看/删除；用户支持软删除自己的会话；加购/问商家改为目标商品确认卡片
- 参考：`D:\Desktop\上课\软件开发课程设计\软件开发综合课程设计·第三次课.pptx`
- 目标：按 Agent-Skill-MCP 三层模型改造现有系统

## 一、已确认决策

- 实现最小 MCP Server
- 主 Agent 采用规则 + LLM 混合路由
- 上下文首批支持应用 JSON 日志 + 后台上传日志文件
- Skill 管理页面仅管理员可用
- Agent 全部业务能力只读，不开放高危写操作

## 二、当前差距

### 当前已有

- Agent 服务账号、API Key、scopes、只读接口
- `POST /api/v1/agent/skills`
  - `product_query`
  - `nl_filter`
  - `recommendation_query`
  - `product_recognize`
- Agent 查询审计
- 用户侧购物助手：多模态、多轮、追问
- Python 侧对话历史表 `agent_dialogues`

### 当前缺失

| 要求 | 当前状态 |
|---|---|
| 管理员 Skill 管理页面 | 无 |
| Skill 能力清单和 7 个字段 | 无独立表，代码里硬编码 |
| 主 Agent + 模块子 Agent | 无，只有单一助手 |
| 对话历史表 | 只有 `agent_dialogues.messages_json` |
| 对话节点表 | 无 |
| 上下文提炼 | 只有 `slots_json` 和最近消息 |
| 日志文件同步入库 | 无 |
| 真正 MCP 协议 | 无，只有 REST Skill facade |
| Java 创建 Agent API Key | 无，当前 `api_keys` 表为 0 |

## 三、目标架构

```text
用户 / 外部 AI 客户端
        │
        ▼
主 Agent（意图识别、任务拆解、路由）
        │
        ├── 商品子 Agent
        ├── 交易子 Agent
        ├── 推荐子 Agent
        ├── 用户/客服子 Agent
        └── 管理只读子 Agent
        │
        ▼
MCP Server（JSON-RPC / SSE）
        │
        ▼
Skill 注册中心（鉴权、参数校验、限流、审计）
        │
        ▼
业务 API（Java 主服务 / Python 数据服务）
        │
        ▼
MySQL / Redis / ES / RabbitMQ
```

核心定位：

- Agent：意图推理、任务拆解、上下文管理
- Skill：业务能力封装、安全校验、权限边界
- MCP：Agent 与 Skill 之间的标准通信协议

## 四、实现位置

### Java `server` 负责

- Skill 注册中心
- Skill 管理页面 API
- MCP Server
- 主 Agent / 子 Agent 编排
- 对话历史与节点
- 上下文摘要
- Agent API Key 管理
- 审计

### Python 5001 负责

- DeepSeek 对话与识图
- 推荐查询
- 自然语言解析

不要把 Agent 编排再放一套到 Python，避免对话和权限双份实现。

## 五、数据模型

### 1. agents

```text
id
code              main_agent / product_agent / trade_agent / ...
name
agent_type        main / sub
description
model
prompt_version
status
config_json
created_at
updated_at
```

### 2. skills

按 PPT 的 7 个字段落地：

```text
id
code              SK-001
name              商品信息查询
module            product / trade / recommendation / user / admin
description
input_schema_json
output_schema_json
allowed_operations
forbidden_operations
scope             product:view / recommendation:query
handler_type      java / python_http
handler_target
status            draft / published / disabled
version
created_by
created_at
updated_at
```

禁止注册为 Skill：

- 删除用户
- 修改密码
- 批量修改关键业务数据
- 角色提权
- 真实支付
- 任意 SQL 执行

### 3. agent_skills

```text
agent_id
skill_id
enabled
priority
```

用于限制子 Agent 的 Skill 白名单。

### 4. conversation_sessions

```text
id
user_id
agent_id
title
status
context_summary
token_budget
last_message_at
created_at
updated_at
```

### 5. conversation_messages

```text
id
session_id
role              user / assistant / system / tool
content
content_type      text / image / tool_result
agent_code
model
token_count
trace_id
created_at
```

### 6. conversation_nodes

保存节点树，而不是只存平铺消息：

```text
id
session_id
parent_node_id
node_type         intent / plan / tool_call / tool_result / summary / response
content_json
status
started_at
finished_at
error_code
trace_id
created_at
```

### 7. agent_tool_calls

```text
id
session_id
node_id
agent_id
skill_id
request_json
response_json
status
latency_ms
error_code
trace_id
created_at
```

### 8. context_artifacts

用于日志文件和应用日志同步：

```text
id
session_id
source_type       app_log / uploaded_file / system_event
source_ref
content_hash
raw_storage_key
extracted_json
summary
status
created_at
```

原始日志文件放受控文件/对象存储，数据库只保存摘要、索引和引用。

## 六、Skill 管理页面

新增：

```text
/admin/skills
```

权限：

```text
skill:view
skill:manage
skill:test
```

管理员功能：

1. Skill 列表
   - 编号、名称、模块、scope、版本、状态
   - 按模块、状态、关键字筛选

2. 新建/编辑
   - 名称
   - 描述
   - 输入 JSON Schema
   - 返回字段 Schema
   - 允许操作
   - 禁止操作
   - scope
   - handler 类型和目标
   - 版本

3. 发布/禁用
   - `draft -> published`
   - `published -> disabled`
   - 禁用后立即从 MCP `tools/list` 消失

4. Skill 测试
   - 管理员填写示例参数
   - 执行只读测试
   - 显示结果、耗时、错误码
   - 不允许真实写操作

5. 审计
   - 创建、修改、发布、禁用
   - 测试调用
   - 变更前后快照

## 七、主 Agent + 子 Agent

```text
用户请求
  -> 主 Agent
  -> 意图识别
  -> 选择子 Agent
  -> 子 Agent 选择 Skill
  -> MCP tools/call
  -> 业务 API
  -> 汇总结果
```

子 Agent：

| 子 Agent | Skill 白名单 |
|---|---|
| product_agent | product_query、nl_filter、product_recognize |
| trade_agent | order_query、cart_query |
| recommendation_agent | recommendation_query、similar_query |
| user_agent | profile_query、preference_query |
| admin_read_agent | pending_product_query、audit_log_query |

路由：

```text
明确意图 -> 规则路由
复杂意图 -> DeepSeek 输出 JSON 意图
```

限制：

- 最大步骤 5
- 单步超时 15 秒
- 总超时 60 秒
- 最多重试 1 次
- 禁止子 Agent 互相调用
- 禁止重复循环调用同一 Skill
- 全部只读，写操作不注册为 Skill

## 八、最小 MCP Server

接口：

```text
POST /api/v1/mcp
GET  /api/v1/mcp/sse
```

传输：

- HTTP JSON-RPC 2.0
- SSE 用于服务端事件流

方法：

```text
initialize
tools/list
tools/call
ping
```

鉴权：

```http
Authorization: Bearer <agent_api_key>
```

兼容：

```http
X-API-Key: cmk_xxx
```

`tools/list` 从 `skills` 表生成工具描述和 `inputSchema`。

`tools/call` 示例：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "product_query",
    "arguments": {
      "category": "手机",
      "max_price": 1000
    }
  }
}
```

错误码：

```text
INVALID_ARGUMENT
UNAUTHORIZED
FORBIDDEN
SKILL_NOT_FOUND
SKILL_DISABLED
UPSTREAM_ERROR
TIMEOUT
RATE_LIMITED
```

## 九、Agent API Key 管理

Java 增加：

```text
GET    /api/v1/users/me/api-keys
POST   /api/v1/users/me/api-keys
DELETE /api/v1/users/me/api-keys/{id}
```

规则：

- 仅 `agent_service` 和 `admin` 可创建
- 完整 Key 只返回一次
- 数据库存哈希和 prefix
- 支持 scopes、过期时间、吊销、最后使用时间
- 支持 `expires_at` 校验
- 按 Key 限流
- 创建、吊销写审计日志

## 十、上下文提炼与日志落库

### 第一层：完整记录

- `conversation_messages`
- `conversation_nodes`
- `agent_tool_calls`
- `context_artifacts`

### 第二层：结构化提炼

每个节点提取：

```text
用户目标
业务模块
筛选条件
已确认事实
已执行动作
未解决问题
错误/异常
下一步
```

存入 `content_json`。

### 第三层：会话摘要

每 N 轮或 token 超限生成：

```text
context_summary
pinned_facts
active_slots
recent_messages
```

后续只带：

- 摘要
- 固定事实
- 最近 6-8 条消息
- 当前节点相关工具结果

### 日志同步

新增：

```text
POST /api/v1/admin/context/logs/import
```

流程：

```text
上传/读取日志
-> JSON Lines 解析
-> PII 脱敏
-> 按 trace_id/session_id 关联
-> 提取错误、意图、工具调用
-> 生成摘要
-> 写 context_artifacts
-> 原文存受控存储
```

使用 RabbitMQ 异步处理，按 `content_hash` 幂等去重。

## 十一、安全要求

按 PPT 五原则：

1. 最小权限：只返回必要字段，手机号脱敏
2. 输入强校验：JSON Schema、类型、长度、枚举、范围
3. 独立鉴权：Agent 服务账号 + API Key，禁止复用用户 Token
4. 结果可预期：统一错误码、超时、降级
5. 操作留痕：服务账号、Skill、入参摘要、时间、结果、trace_id

禁止：

- Agent 直接访问数据库
- 动态执行任意 URL
- 将删除用户、改密、提权等注册为 Skill
- 无审计的 Agent 调用

## 十二、实施阶段

### Phase 1：Skill 注册中心

- `agents`、`skills`、`agent_skills` 迁移
- Skill CRUD、版本、发布/禁用
- 管理后台 `/admin/skills`
- Skill 测试与审计

### Phase 2：MCP + API Key

- Java API Key 创建/撤销/过期/限流
- `/api/v1/mcp` JSON-RPC
- `initialize/tools/list/tools/call/ping`
- MCP Inspector 验证

### Phase 3：主 Agent + 子 Agent

- 主 Agent 意图路由
- 子 Agent 与 Skill 白名单
- 多轮对话与槽位
- 超时、重试、步骤限制

### Phase 4：上下文与日志

- 会话、消息、节点、工具调用表
- 摘要和上下文预算
- JSON 日志同步
- 上传日志文件
- RabbitMQ 异步处理

### Phase 5：测试与文档

- Skill 管理测试
- API Key 生命周期测试
- MCP 协议测试
- 主/子 Agent 路由测试
- 上下文摘要测试
- 日志同步幂等测试
- 新增 `docs/agent-skill-mcp.md`

## 十三、验收演示

```text
1. 管理员进入 /admin/skills
2. 创建一个只读 Skill
3. 发布 Skill
4. 创建 Agent API Key
5. MCP Inspector initialize
6. tools/list
7. tools/call product_query
8. tools/call nl_filter
9. tools/call recommendation_query
10. tools/call product_recognize
11. 尝试写操作，确认被拒绝
12. 查看对话历史、对话节点、工具调用
13. 上传日志文件并查看上下文摘要
14. 查看审计日志
```
