# 运维 Runbook（成员A范围）

## 1. 发布前检查

- CI 通过：ruff、pytest、Alembic 检查、前端 build。
- 生产环境变量齐全：`DATABASE_URL`、`REDIS_URL`、`SECRET_KEY`、`PHONE_ENC_KEY`、`PHONE_HASH_KEY`、`CORS_ORIGINS`、`SMTP_*`。
- 备份已完成，并记录备份 ID。
- 迁移脚本已评审，确认可回滚或具备向前修复方案。

## 2. 数据库迁移

```bash
cd backend
flask --app app db upgrade
```

禁止在应用启动时自动 `create_all`。生产使用独立迁移账号执行 DDL。

## 3. 发布

1. 构建并推送后端镜像。
2. 执行数据库迁移。
3. 滚动更新后端，等待 `/health/ready` 返回 200。
4. 更新前端静态资源。
5. 验证登录、刷新、管理后台核心路径。

## 4. 回滚

- 应用回滚：切回上一个镜像标签。
- 数据库回滚：优先使用向前修复迁移；如必须降级，执行 `flask --app app db downgrade -1`，并确认数据兼容。
- 禁止直接修改生产表结构。

## 5. 备份与恢复

- 托管 MySQL 开启自动备份与 binlog PITR。
- 每日逻辑备份到对象存储，保留至少 7 天。
- 每季度做一次恢复演练，记录 RTO/RPO。
- 恢复后校验：用户数、商品数、最近操作日志。

## 6. 封禁与安全事件

1. 管理后台封禁用户，填写原因。
2. 系统自动吊销 refresh session 与 API Key。
3. 检查 `operation_logs` 中该用户的最近行为。
4. 如涉及密钥泄露，轮换 `SECRET_KEY`、`PHONE_ENC_KEY`、`PHONE_HASH_KEY`，并强制所有用户重新登录。

## 7. 监控与告警

- 指标：5xx 比例、P95 延迟、DB 连接数、Redis 可用性、登录失败率、备份失败。
- 日志：JSON 结构化日志，`trace_id` 贯穿请求。
- 审计：管理后台写操作必须出现在 `operation_logs`，且不可通过 API 修改/删除。

## 8. 管理员初始化

生产环境不执行 demo seed：

```bash
ADMIN_USERNAME=... ADMIN_EMAIL=... ADMIN_PASSWORD=... flask --app app bootstrap-admin
```

首次登录后立即修改密码，并启用邮箱验证。
