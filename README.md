## 电影推荐系统（课程项目）- 快速开始

本仓库包含：
- **backend/**：Flask + SQLite（API 服务）
- **frontend/**：Vue 3 + Vite + Vue Router + Element Plus（前端页面）

### 1) 启动后端（Flask）

进入后端目录并安装依赖：

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

启动服务（默认 `http://127.0.0.1:5000`）：

```bash
python app.py
```

接口健康检查：
- `GET /api/health`

可选：初始化演示数据（用于答辩展示）

```bash
python -m seed.seed_demo
```

导入真实电影数据（推荐 MovieLens）

- 先看说明：`data/README.md`
- 然后导入（在 backend 目录下执行）：

```bash
python -m seed.import_movielens --movies ..\data\movies.csv
```

补全电影数据（简介/海报/演员，使用 TMDB）

- 你需要先去 TMDB 申请 API Key（免费即可）：`https://www.themoviedb.org/settings/api`
- PowerShell 设置环境变量（在 backend 目录下执行）：

```bash
$env:TMDB_API_KEY="你的key"
python -m seed.enrich_tmdb --limit 200
```

### 2) 启动前端（Vue 3 + Vite）

进入前端目录并安装依赖：

```bash
cd frontend
npm install
```

启动开发服务器（默认 `http://127.0.0.1:5173`）：

```bash
npm run dev
```

说明：
- 前端已在 `vite.config.js` 配置了 **`/api` 代理**到后端 `http://127.0.0.1:5000`，因此前端请求直接写 `/api/...` 即可。

### 3) 你接下来要做什么（建议顺序）

- 完成注册/登录的真实逻辑（JWT / Session 任选其一）
- 完成 Movie/Genre/Actor 的数据导入（可写 `backend/seed/` 脚本）
- 把“收藏/评分”写入数据库并联调前端页面
- 最后补一个简单推荐策略（例如：基于用户评分的 TopN、或基于类型偏好的相似推荐）

### 4) 学习与开发指南

见：`docs/LEARNING_GUIDE.md`


