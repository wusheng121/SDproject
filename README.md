# 校园二手交易平台

校园二手交易平台，当前采用：

- 前端：Vue 3 + Element Plus + Vite
- 主服务：Java Spring Boot，端口 8080
- 数据服务：Python Flask，端口 5001
- 数据库：MySQL，端口 3407
- 缓存与消息：Redis、RabbitMQ
- 搜索：Elasticsearch

## 目录

```text
backend/       Python 数据服务、Alembic 迁移、演示数据
server/        Java Spring Boot 主服务
frontend/      Vue 3 PC 前端
wx_client/     微信小程序
scripts/       本地启动脚本
docs/          项目文档
```

## 端口

| 服务 | 端口 |
|---|---:|
| MySQL | 3407 |
| Redis（宿主机） | 16379 |

> Redis 容器内部仍使用 `6379`，宿主机映射到 `16379`，避免落入 Windows 动态保留端口范围。本地 Python/Java 连接 `127.0.0.1:16379`。
| RabbitMQ | 5672 |
| RabbitMQ 管理台 | 15672 |
| Elasticsearch | 9200 |
| Java 主服务 | 8080 |
| Python 数据服务 | 5001 |
| 前端开发服务器 | 5173 |

> Windows 当前排除了 `3307-3406` 端口范围，所以本项目使用 MySQL `3407`，不要再改回 3307。

## 环境要求

- Java 21+
- Maven 3.9+
- Python 3.12+
- Node.js 18+ 或 20+
- MySQL 8.0+ 或 9.x
- Docker Desktop（Redis、RabbitMQ、Elasticsearch）

Windows PowerShell 下如果 `npm.ps1` 被拦截，统一使用：

```powershell
npm.cmd run dev
npm.cmd run build
```

## 一、从 0 启动

### 1. 准备 MySQL

当前推荐的数据目录：

```text
D:\aWusheng\mysql-data
```

如果该目录已经存在，直接执行：

```powershell
cd D:\aWusheng\SDproject
powershell -ExecutionPolicy Bypass -File .\scripts\start-mysql.ps1
```

如果是全新的空目录，先初始化 MySQL：

```powershell
& "C:\Program Files\MySQL\MySQL Server 9.4\bin\mysqld.exe" `
  --initialize-insecure `
  --datadir=D:\aWusheng\mysql-data
```

再启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-mysql.ps1
```

首次创建数据库和账号：

```powershell
& "C:\Program Files\MySQL\MySQL Server 9.4\bin\mysql.exe" -P 3407 -u root -e "
CREATE DATABASE campus_market CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'campus'@'%' IDENTIFIED BY 'campus';
GRANT ALL PRIVILEGES ON campus_market.* TO 'campus'@'%';
FLUSH PRIVILEGES;
"
```

### 2. 启动中间件

只启动 Redis、RabbitMQ、Elasticsearch：

```powershell
cd D:\aWusheng\SDproject
docker compose up -d redis rabbitmq elasticsearch
docker compose ps
```

如果你之前运行过旧版 Compose（Redis 映射为 `6379`），需要先重建 Redis 容器使新端口生效：

```powershell
docker compose up -d --force-recreate redis
```

不要同时启动 Compose 里的 MySQL，避免和本地 3407 实例冲突。

### 3. 安装依赖

Python：

```powershell
cd D:\aWusheng\SDproject\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

前端：

```powershell
cd D:\aWusheng\SDproject\frontend
npm.cmd install
```

Java：

```powershell
cd D:\aWusheng\SDproject\server
mvn -q -DskipTests package
```

### 4. 配置环境变量

后端配置位于：

```text
backend/.env
```

从示例复制：

```powershell
cd D:\aWusheng\SDproject
Copy-Item backend\.env.example backend\.env
```

至少确认：

```text
DATABASE_URL=mysql+pymysql://campus:campus@127.0.0.1:3407/campus_market?charset=utf8mb4
REDIS_URL=redis://127.0.0.1:16379/0
SECRET_KEY=至少32字节的随机字符串
```

Java 启动时会读取 `backend/.env`，并自动连接同一个数据库。

前端默认通过 Vite 代理访问 Java 8080，一般不需要额外配置。

### 5. 执行数据库迁移

```powershell
cd D:\aWusheng\SDproject\backend
python -m flask --app app db upgrade
```

不要用 `init_db.py` 代替 Alembic 迁移，否则可能缺少后续 Agent/Planner 表。

### 6. 初始化管理员

#### 方式 A：演示数据

```powershell
cd D:\aWusheng\SDproject\backend
python -m flask --app app seed-demo
```

会创建：

```text
普通用户：testuser / Test12345
管理员：admin / Admin12345
Agent：agent / Agent12345
```

这种方式默认不会强制管理员改密码。
如果要演示首次登录强制改密，执行：

```powershell
& "C:\Program Files\MySQL\MySQL Server 9.4\bin\mysql.exe" `
  -h 127.0.0.1 -P 3407 -u campus -pcampus campus_market `
  -e "UPDATE users SET must_change_password=1 WHERE username='admin';"
```

#### 方式 B：正式 bootstrap 管理员

先在 `backend/.env` 中配置：

```text
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=YourPassword123
```

再初始化 RBAC 和分类：

```powershell
cd D:\aWusheng\SDproject\backend
python -c "from app import app; from seed.init_products import seed_rbac, seed_categories; ctx=app.app_context(); ctx.push(); seed_rbac(); seed_categories(); print('rbac ready')"
```

启动 Java 后，如果系统中没有管理员，会自动创建：

- 管理员账号
- `admin + normal_user` 双角色
- `must_change_password=1`

管理员第一次登录后会跳转到 `/change-password` 强制改密。

### 7. 启动 Python 数据服务

另开终端：

```powershell
cd D:\aWusheng\SDproject\backend
python data_server.py
```

### 8. 启动 Java 主服务

另开终端：

```powershell
cd D:\aWusheng\SDproject\server
java -jar target\market-server-0.1.0.jar
```

如果 Java 代码有修改：

```powershell
mvn -q -DskipTests package
java -jar target\market-server-0.1.0.jar
```

### 9. 启动前端

另开终端：

```powershell
cd D:\aWusheng\SDproject\frontend
npm.cmd run dev
```

访问：

```text
http://127.0.0.1:5173
```

健康检查：

```text
Java:   http://127.0.0.1:8080/health/live
Python: http://127.0.0.1:5001/health/live
```

## 二、日常正常启动

数据库和中间件已经准备好时，只需要：

### 1. 启动 MySQL

```powershell
cd D:\aWusheng\SDproject
powershell -ExecutionPolicy Bypass -File .\scripts\start-mysql.ps1
```

### 2. 启动中间件

```powershell
docker compose up -d redis rabbitmq elasticsearch
```

如果 Redis 容器是旧版 `6379` 映射，使用：

```powershell
docker compose up -d --force-recreate redis
```

Redis 宿主机端口为 `16379`，容器内部仍为 `6379`。

### 3. 启动 Python

```powershell
cd D:\aWusheng\SDproject\backend
python data_server.py
```

### 4. 启动 Java

```powershell
cd D:\aWusheng\SDproject\server
java -jar target\market-server-0.1.0.jar
```

### 5. 启动前端

```powershell
cd D:\aWusheng\SDproject\frontend
npm.cmd run dev
```

## 三、管理员首次登录强制改密

如果管理员是 bootstrap 创建的，登录后会自动跳转：

```text
/login -> /change-password
```

当前已有管理员如果要重新演示强制改密：

```powershell
& "C:\Program Files\MySQL\MySQL Server 9.4\bin\mysql.exe" `
  -h 127.0.0.1 -P 3407 -u campus -pcampus campus_market `
  -e "UPDATE users SET must_change_password=1 WHERE username='admin';"
```

然后重新登录管理员账号。

注意：

- 修改成功后 `must_change_password` 会变回 0
- 修改密码后管理员进入 `/admin`
- 普通用户进入 `/`

## 四、登录 500 排查

登录 500 最常见原因是 MySQL 3407 没有启动。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-mysql.ps1
```

检查端口：

```powershell
Get-NetTCPConnection -LocalPort 3407 -State Listen
```

检查数据库：

```powershell
& "C:\Program Files\MySQL\MySQL Server 9.4\bin\mysql.exe" `
  -h 127.0.0.1 -P 3407 -u campus -pcampus campus_market `
  -e "SELECT COUNT(*) FROM users;"
```

不要使用 3307：当前 Windows 已排除 `3307-3406`。

## 五、常用验证

### 检查所有服务端口

```powershell
foreach ($port in 3407,16379,5672,9200,8080,5001,5173) {
  $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  if ($conn) { "$port = running" } else { "$port = stopped" }
}
```

### 测试登录接口

登录需要验证码。先访问登录页获取验证码，或请求：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/api/v1/auth/captcha
```

### 重新执行迁移

```powershell
cd D:\aWusheng\SDproject\backend
python -m flask --app app db upgrade
```

### 重新构建 Java

```powershell
cd D:\aWusheng\SDproject\server
mvn -q -DskipTests package
```

### 重新构建前端

```powershell
cd D:\aWusheng\SDproject\frontend
npm.cmd run build
```

如果 npm 包装器构建卡住，可使用：

```powershell
node .\node_modules\vite\bin\vite.js build --minify false
```

## 六、测试

Python：

```powershell
cd D:\aWusheng\SDproject\backend
python -m pytest -q
```

Java：

```powershell
cd D:\aWusheng\SDproject\server
mvn test
```

当前预期：

```text
Python: 80 passed
Java:   14 passed
```

前端：

```powershell
cd D:\aWusheng\SDproject\frontend
npm.cmd run build
```

## 七、Agent 功能入口

前端：

```text
/assistant     购物助手：快速问答、识图、商品分析、对比、加购、问商家
/admin         Skill 管理、Agent 接入、Agent 会话、上下文/操作日志
```

Agent API Key：

- 管理员进入 `/admin`
- 打开“Agent 接入”
- 选择 Agent 服务账号
- 创建 API Key
- 完整 Key 只显示一次

外部 MCP：

```text
POST http://127.0.0.1:8080/api/v1/mcp
Authorization: Bearer <Agent API Key>
```

当前 MCP 只读，不支持下单、支付和写操作。

## 八、微信小程序

小程序工程：

```text
wx_client/
```

启动：

1. 启动 Java、Python、MySQL、Redis、RabbitMQ、Elasticsearch
2. 微信开发者工具导入 `wx_client`
3. 开发阶段关闭“合法域名校验”
4. 点击编译/预览

小程序默认后端：

```text
http://127.0.0.1:8080
```

真机调试需要把 `wx_client/miniprogram/utils/config.ts` 改成电脑局域网 IP。

底部 tabBar：

```text
首页 / 发布 / 购物车 / 订单 / 我的
```

搜索保留在首页顶部，收藏放在“我的”。

已实现：

- 登录/注册
- 商品列表、分页搜索、详情
- 收藏
- 发布闲置、AI 识图填充、同品类价格参考
- 我的发布、编辑、删除
- 购物车
- 订单、模拟支付、取消订单、订单评价
- 消息
- 首页个性化推荐
- AI 购物助手
- AI 对话中的加购确认和卖家消息确认
- 我的统计、兴趣偏好、资料、修改密码、注销账号
- 深色模式手动切换

暂不包含：

- 管理员后台
- 邮箱验证/找回密码

## 九、已知限制

- 小程序已补齐交易、发布、推荐和 AI 助手，但仍需开发者工具和真机回归
- 小程序暂未实现邮箱验证、忘记密码和重置密码
- 旧 `agent_dialogues` 历史不迁移到新 Java 会话表
- Planner 目前是规则 Planner，不是完整的 LLM 自由规划
- `cart_add` 和 `seller_message` 必须用户确认
- 不支持下单/支付
- Python 数据服务仍保留部分旧业务路由，后续需要继续收口
- LLM 上游繁忙时会重试并回退规则；上游完全不可用时仍可能无法返回 AI 回复
- Java Compose 服务尚未做完整容器启动回归

## 十、Git 与密钥

不要提交：

- `backend/.env`
- 数据库备份
- 包含手机号、邮箱、密钥的日志

当前数据库目录和本地启动脚本：

```text
D:\aWusheng\mysql-data
scripts\start-mysql.ps1
```

## 十一、相关文档

- `docs/agent-skill-mcp.md`
- `docs/complex-agent.md`
- `docs/middleware.md`
- `docs/database/schema.md`
- `项目检查.md`
