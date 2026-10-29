# 校园二手交易平台

AI 拍照识物与智能推荐的校园二手交易平台，采用 Vue 3 + Flask + MySQL + Redis 的前后端分离架构。

## 目录

- `backend/`：Flask API、认证会话、RBAC、管理后台接口、Alembic 迁移
- `frontend/`：Vue 3 + Element Plus + Vite
- `docs/`：需求、实现 Schema、OpenAPI、ADR 与运维文档
- `docs/README.md`：文档索引与权威层级
- `docker-compose.yml`：本地 MySQL、Redis、MailHog、后端、前端

## 环境要求

- Python 3.12+
- Node.js 18+ 或 20+
- MySQL 8.0+
- Redis 7+
- Docker Desktop（可选，推荐用于本地基础服务）

Windows PowerShell 如果提示 `npm.ps1 cannot be loaded`，统一使用 `npm.cmd` 代替 `npm`。

## 环境变量

后端配置位于 `backend/.env`，可从 `backend/.env.example` 复制：

```powershell
cd D:\aWusheng\SDproject\backend
Copy-Item .env.example .env
```

主要配置：

| 变量 | 说明 | 示例 |
|---|---|---|
| `APP_ENV` | 运行环境 | `development` / `testing` / `production` |
| `SECRET_KEY` | JWT/会话签名密钥，生产必须至少 32 字节 | 随机 hex 字符串 |
| `DATABASE_URL` | MySQL 连接串 | `mysql+pymysql://campus:campus@127.0.0.1:3307/campus_market?charset=utf8mb4` |
| `REDIS_URL` | Redis 连接串 | `redis://127.0.0.1:6379/0` |
| `RATELIMIT_STORAGE_URI` | 限流存储 | `redis://127.0.0.1:6379/1` |
| `CORS_ORIGINS` | 允许的前端源，逗号分隔 | `http://localhost:5173,http://127.0.0.1:5173` |
| `FRONTEND_URL` | 邮件链接使用的前端地址 | `http://localhost:5173` |
| `JWT_ACCESS_TTL_SECONDS` | Access Token 有效期 | `900` |
| `JWT_REFRESH_TTL_SECONDS` | Refresh Token 有效期 | `2592000` |
| `BCRYPT_COST` | BCrypt 成本 | 生产 `12` |
| `PHONE_ENC_KEY` | 手机号加密密钥 | Fernet key |
| `PHONE_HASH_KEY` | 手机号盲索引 HMAC 密钥 | 随机 hex 字符串 |
| `REFRESH_COOKIE_SECURE` | 生产 HTTPS 下设为 `true` | `false`（本地） |
| `REFRESH_COOKIE_SAMESITE` | Cookie SameSite | `Lax` |
| `SMTP_HOST` / `SMTP_PORT` | 邮件服务 | 本地 MailHog：`127.0.0.1:1025` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `SENTRY_DSN` | Sentry DSN，可选 | 空 |

生成密钥：

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`SECRET_KEY` 和 `PHONE_HASH_KEY` 使用第一行输出；`PHONE_ENC_KEY` 使用第二行输出。

### 前端环境变量

前端配置位于 `frontend/.env`，可从 `frontend/.env.example` 复制：

```powershell
cd D:\aWusheng\SDproject\frontend
Copy-Item .env.example .env
```

| 变量 | 说明 | 本地示例 |
|---|---|---|
| `VITE_API_BASE_URL` | 后端 API 根地址 | `http://127.0.0.1:5000/api` |

本地开发也可以不创建该文件，Vite 会通过 `vite.config.js` 的 `/api` 代理访问 `http://127.0.0.1:5000`。

## 本地部署

### 方式一：Docker Compose 全栈

确保 Docker Desktop 已启动，且 `docker version` 能正常返回：

```powershell
cd D:\aWusheng\SDproject
docker compose up --build
```

服务地址：

- 前端：http://localhost:5173
- 后端：http://localhost:5000
- 健康检查：http://localhost:5000/health/ready
- MailHog：http://localhost:8025

Compose 中 MySQL 映射到 `127.0.0.1:3307`，避免占用本机 3306。后端容器启动时会执行迁移并写入演示数据。

常用命令：

```powershell
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose down
docker compose down -v   # 同时删除 MySQL 数据卷，谨慎使用
```

### 方式二：基础服务用 Docker，前后端在宿主机运行（推荐开发）

这种方式支持后端自动重载和前端 Vite HMR。

1. 启动基础服务：

```powershell
cd D:\aWusheng\SDproject
docker compose up -d mysql redis mailhog
```

2. 启动后端：

```powershell
cd D:\aWusheng\SDproject\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env
flask --app app db upgrade
flask --app app seed-demo
flask --app app run --debug --port 5000
```

使用 `flask --app app run --debug` 才会开启自动重载；`python app.py` 是关闭 debug 的启动方式。

3. 启动前端：

```powershell
cd D:\aWusheng\SDproject\frontend
npm.cmd install
npm.cmd run dev
```

前端 Vite 会把 `/api` 代理到 `http://127.0.0.1:5000`。

### 方式三：使用本机 MySQL

将 `backend/.env` 的 `DATABASE_URL` 改为本机 MySQL，例如：

```text
mysql+pymysql://campus:campus@127.0.0.1:3306/campus_market?charset=utf8mb4
```

首次需要创建数据库和用户：

```sql
CREATE DATABASE campus_market CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'campus'@'%' IDENTIFIED BY 'campus';
GRANT ALL PRIVILEGES ON campus_market.* TO 'campus'@'%';
FLUSH PRIVILEGES;
```

然后执行迁移和 seed。

## 数据库初始化与同步

表结构通过 Alembic 管理，不要手动改生产表。

```powershell
cd D:\aWusheng\SDproject\backend
flask --app app db upgrade
```

演示数据：

```powershell
flask --app app seed-demo
```

当前 seed 包含：

- 3 个演示账号
- 3 个角色、12 个权限
- 31 个品类、47 个商品
- 商品按名称幂等插入，重复执行不会产生重复商品

生产环境不执行 `seed-demo`，使用一次性管理员初始化：

```powershell
$env:ADMIN_USERNAME="admin"
$env:ADMIN_EMAIL="admin@example.com"
$env:ADMIN_PASSWORD="Admin12345"
flask --app app bootstrap-admin
```

### 协作者如何同步数据

- Schema：提交 Alembic 迁移，其他成员 `git pull` 后执行 `flask db upgrade`。
- 演示/字典数据：写入 `backend/seed/init_products.py`，提交代码后执行 `flask --app app seed-demo`。
- 真实数据：使用 `mysqldump` 或共享开发数据库，不要提交 Git。

备份：

```powershell
mysqldump -h 127.0.0.1 -P 3307 -u campus -pcampus campus_market > campus_market.sql
```

恢复：

```powershell
cmd /c "mysql -h 127.0.0.1 -P 3307 -u campus -pcampus campus_market < campus_market.sql"
```

SQL 文件可能包含用户、手机号和行为数据，不要提交 Git。

## 演示账号

仅开发环境：

- 普通用户：`testuser / Test12345`
- 管理员：`admin / Admin12345`
- Agent：`agent / Agent12345`

连续输错密码 5 次会锁定 15 分钟。需要解锁时可由管理员处理，或开发环境执行：

```sql
UPDATE users
SET failed_login_count = 0, locked_until = NULL
WHERE username = 'testuser';
```

## 测试

后端静态检查与单元/集成测试：

```powershell
cd D:\aWusheng\SDproject\backend
ruff check app.py auth.py config.py extensions.py models.py routes utils seed tests
pytest -q
```

使用 MySQL 测试库：

```powershell
$env:APP_ENV="testing"
$env:TEST_DATABASE_URL="mysql+pymysql://campus:campus@127.0.0.1:3307/campus_market_test?charset=utf8mb4"
python -m pytest -q
```

前端生产构建：

```powershell
cd D:\aWusheng\SDproject\frontend
npm.cmd run build
```

## 认证与权限

- 注册/登录：`/api/v1/auth/*`
- Access Token：仅保存在内存
- Refresh Token：HttpOnly Cookie，轮换、重放检测、支持吊销
- RBAC：`normal_user`、`admin`、`agent_service`
- Agent：API Key + scopes，只读
- 手机号：加密存储、盲索引查询、接口脱敏

普通用户与 Agent 的区别：

- 普通用户：Web 登录，可浏览、发布/编辑/下架自己的商品、收藏、下单、评价
- Agent：机器账号，通过 `X-API-Key` 只读查询商品与推荐，不能写数据
- Agent 调用会记录审计日志

## 生产部署要点

- 使用 Docker 镜像 + Gunicorn，不使用 Flask 开发服务器
- 使用托管 MySQL 8 与 Redis
- `APP_ENV=production`
- `SECRET_KEY` 至少 32 字节
- `REFRESH_COOKIE_SECURE=true`
- `CORS_ORIGINS` 配置真实前端域名，禁止 `*`
- 迁移作为发布步骤执行，不在应用启动时自动建表
- 不执行 `seed-demo`
- 配置 SMTP、Sentry、备份与监控
- 发布前验证 `/health/ready`

`render.yaml` 仅提供容器部署入口，真实部署仍需外接 MySQL/Redis，并配置环境变量。

## 常见问题

### npm 命令被 PowerShell 拦截

使用：

```powershell
npm.cmd run dev
npm.cmd run build
```

### Docker 命令卡住或连接失败

确认 Docker Desktop 显示 Engine running，并执行：

```powershell
docker version
```

如果仍不可用，可以先使用本机 MySQL，或将前后端直接跑在宿主机。

### 登录后刷新页面掉登录态

检查：

- `CORS_ORIGINS` 是否包含当前访问地址，例如 `http://127.0.0.1:5173`
- 是否同时使用 `localhost` 和 `127.0.0.1` 混用
- 浏览器是否拦截了 Cookie
- 后端是否已用最新 `.env` 重启

### PyJWT 提示 InsecureKeyLengthWarning

`SECRET_KEY` 太短。重新生成至少 32 字节的密钥并重启后端：

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### 商品列表为空

先确认接口：

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/api/products?page_size=12"
```

如果接口有数据但页面为空，按 `Ctrl+F5` 强制刷新，避免旧前端模块缓存。

## 文档

文档入口：`docs/README.md`

- `需求文档.docx`：最终提交版需求，仅本地保留，不入库
- `docs/需求文档_完整版.md`：仓库内工程需求说明
- `docs/database/schema.md`：当前实现层 Schema 与 ER 图
- `docs/api/openapi.yaml`：成员A范围 API 契约
- `docs/adr/0001-production-baseline.md`：生产基线与技术决策
- `docs/operations/runbook.md`：发布、备份、回滚与安全事件处理
- `docs/需求文档图表.md`：需求阶段图表源

`需求文档.docx` 是最终提交版，不随 Git 分发；协作者使用 Markdown 工程说明和实现 ER。
