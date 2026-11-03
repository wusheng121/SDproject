# 用户侧复杂 Agent 实现说明

- 日期：2026-11-03
- 入口：`/assistant`，Java 统一会话与路由
- 身份：用户 JWT，不使用 Agent API Key
- 快速问答、识图、复杂任务共用同一个会话

## 一、已实现能力

### 1. 商品链接分析

支持站内链接：

```text
http://127.0.0.1:5173/product/3
```

解析出 `product_id` 后读取商品详情、分类、卖家、评价，生成：

- 购买建议
- 优点
- 风险
- 缺失信息
- 建议问卖家的问题
- 沟通话术

### 2. 商品对比

支持 2-5 个商品对比，输出：

- 价格
- 成色
- 成色分
- 性价比分
- 瑕疵说明
- 推荐结论

性价比分：

```text
condition_score / price * 100
```

### 3. 加购物车

Agent 只生成 `cart_add` 提议，不直接执行。

用户点击“确认加入”后，使用用户 JWT 调用现有：

```text
POST /api/v1/cart
```

### 4. 卖家消息

Agent 只生成 `seller_message` 草稿，不自动发送。

用户可编辑草稿，点击“确认发送”后：

```text
打开会话
-> 使用用户 JWT 发送消息
```

### 5. 复杂请求

当前支持单轮内组合：

```text
看链接 + 给建议 + 生成问题 + 加购提议
找商品 + 对比前三款
```

不支持：

- 下单
- 支付
- 多轮复杂任务计划
- 自动发送消息
- 自动加购

## 二、接口

```text
POST /api/v1/assistant/message
GET  /api/v1/assistant/sessions
GET  /api/v1/assistant/sessions/{id}/messages

POST /api/v1/assistant/actions/{id}/confirm
POST /api/v1/assistant/actions/{id}/cancel
```

`/api/v1/assistant/message` 由 Java 统一处理：

- 普通聊天/识图：调用 Python `/api/ai/assistant-reply`
- 商品链接/对比/加购/问卖家：调用 Java Agent
- 两类消息都写入同一张 `conversation_messages`

请求示例：

```json
{
  "message": "看看这个链接值不值得买：http://127.0.0.1:5173/product/3，帮我问卖家电池健康，把商品加入购物车",
  "session_id": 6
}
```

返回：

```json
{
  "data": {
    "session_id": 6,
    "intent": "cart",
    "reply": "...",
    "products": [],
    "advice": {},
    "comparison": null,
    "questions": [],
    "action_proposals": [
      {
        "action_id": 3,
        "type": "cart_add",
        "payload": { "product_id": 3 }
      }
    ]
  }
}
```

## 三、数据表

### pending_actions

```text
id
user_id
session_id
action_type        cart_add / seller_message
payload_json
status             pending / executed / cancelled
expires_at
executed_at
trace_id
message_id         绑定到对应的助手消息
plan_id            绑定到规则计划
created_at
```

动作默认 10 分钟过期。

### agent_plans

```text
id
session_id
user_id
goal
status              executing / awaiting_confirmation / completed / cancelled / failed
steps_json
current_step
context_json
created_at
updated_at
```

每个复杂请求会生成一条计划记录；只读步骤自动执行，写操作进入 `awaiting_confirmation`。

### conversation_sessions.context_json

保存：

- 最近讨论的商品 ID
- `active_plan_id`
- 当前候选商品
- 最近结果

用于支持：

- “这个商品”
- “第二件”
- “刚才那个”
- “继续”

## 四、新增 Skill

```text
SK-005 product_detail
SK-006 product_compare
SK-007 product_advice
SK-008 seller_questions
```

这些 Skill 都是只读，可通过 MCP `tools/list` 发现。

写操作不注册为 MCP Tool：

- `cart_add`
- `seller_message`

原因：写操作需要用户身份和用户确认，不能由外部 Agent 服务账号直接执行。

## 五、安全约束

- 加购和发消息必须由登录用户确认
- Agent 服务账号不能代替用户执行写操作
- 商品链接只取站内 `product_id`
- 商品描述视为不可信数据，防止 Prompt Injection
- 不支持下单
- 动作过期后不能执行
- 执行写操作时重新校验商品状态和用户身份
- 全程写审计日志

## 六、管理后台 Agent 会话日志

管理后台新增“Agent 会话”页：

```text
GET /api/v1/admin/agent-sessions
GET /api/v1/admin/agent-sessions/{id}
```

管理员可以查看：

- 会话 ID、用户、Agent、标题
- 消息数量、最后一条消息
- 完整消息流
- 动作类型、状态、参数
- 会话节点

管理员可以删除异常会话：

```text
DELETE /api/v1/admin/agent-sessions/{id}
```

用户只能删除自己的会话：

```text
DELETE /api/v1/assistant/sessions/{id}
```

删除采用软删除：

- 历史列表不再显示
- 消息、动作、节点保留用于审计
- 未执行动作自动取消
- 写审计日志

## 七、动作展示规则

- 加购：只显示目标商品和“确认加入”按钮
- 问商家：只显示目标商品、消息草稿和“确认发送”
- 对比：只显示参与对比的商品和对比表
- 链接分析：显示完整购买建议
- 目标不唯一：反问用户选择，不创建动作

### 动作历史

`GET /api/v1/assistant/sessions/{id}/messages` 会按 `message_id` 返回每条消息当前的动作状态。前端刷新历史后使用后端动作状态，不再依赖旧的 `metadata_json` 快照。

### Planner 状态

查询会话最近计划：

```text
GET /api/v1/assistant/sessions/{id}/plan
```

支持“继续/下一步/确认/取消”恢复待确认计划；计划状态：

```text
executing / awaiting_confirmation / completed / cancelled / failed
```

## 八、验证

已验证：

- 商品链接解析
- 商品建议和问题生成
- 商品对比
- 加购确认
- 卖家消息草稿确认
- 用户确认后执行
- 加购/问商家只展示目标商品
- “小米”名称解析到正确商品
- 对比候选去重
- 用户软删除会话
- 管理员软删除会话
- 前端构建通过
