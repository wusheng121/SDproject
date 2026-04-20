## 电影推荐系统（课程项目）- 快速开始

本仓库包含：
- **backend/**：Flask + SQLite（API 服务）
- **frontend/**：Vue 3 + Vite + Vue Router + Element Plus（前端页面）

## 在线部署（推荐：Vercel 前端 + Render 后端）

本项目已经适配为前后端分离部署：
- 前端部署到 **Vercel**
- 后端部署到 **Render**
- 部署完成后，老师和同学可以直接通过前端公网网址访问

### 一、部署前准备

1. 先将整个项目推送到 GitHub。
2. 确保前端和后端目录结构保持不变：
   - `frontend/`
   - `backend/`
3. 前端生产环境接口地址通过环境变量 `VITE_API_BASE_URL` 配置。
4. 后端跨域白名单通过环境变量 `CORS_ORIGINS` 配置。

### 二、部署后端到 Render

在 Render 中创建一个新的 **Web Service**，并选择当前仓库。

推荐配置如下：
- **Root Directory**: `backend`
- **Runtime**: `Python`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

后端环境变量建议配置：
- `SECRET_KEY`：随机字符串
- `JWT_EXPIRE_SECONDS`：`86400`
- `CORS_ORIGINS`：你的前端域名，例如 `https://your-project.vercel.app`
- `TMDB_API_KEY`：如果需要在线补全 TMDB 数据再配置

仓库根目录提供了可选的 Render 配置文件：
- `render.yaml`

后端部署完成后，记下你的公网地址，例如：
- `https://your-backend.onrender.com`

健康检查地址：
- `https://your-backend.onrender.com/api/health`

### 三、部署前端到 Vercel

在 Vercel 中导入当前仓库。

推荐配置如下：
- **Framework Preset**: `Vite`
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`

前端环境变量：
- `VITE_API_BASE_URL=https://your-backend.onrender.com/api`

项目已包含：
- `frontend/vercel.json`

它会将 Vue Router 的前端路由统一回退到 `index.html`，避免刷新页面时出现 404。

前端部署完成后，你会得到一个固定网址，例如：
- `https://your-project.vercel.app`

这个网址就是老师和同学访问的地址。

### 四、以后如何更新线上项目

如果你后续修改了项目，只需要：

```bash
git add .
git commit -m "update project"
git push
```

如果 Vercel 和 Render 已连接 GitHub：
- 平台会自动重新部署
- **网址通常不变**
- 访问到的内容会更新为最新版本

### 五、本地开发与线上部署的区别

本地开发时：
- 前端通过 `vite.config.js` 中的代理，把 `/api` 转发到 `http://127.0.0.1:5000`

线上部署时：
- 前端直接通过 `VITE_API_BASE_URL` 请求 Render 上的后端接口

### 六、示例环境变量文件

- 前端示例：`frontend/.env.example`
- 后端示例：`backend/.env.example`

### 七、说明

- Render 免费服务可能会休眠，首次访问可能需要等待几十秒唤醒。
- 如果你使用的是 Render 免费实例，答辩前建议先打开一次后端和前端链接，避免现场首次冷启动等待。

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

### 3) 机器学习模块（矩阵分解推荐系统）

**位置**: `backend/ml/`

**功能**: 基于矩阵分解（Matrix Factorization）的协同过滤推荐，适用于用户有充足行为数据（评分≥10）的场景（策略 D）。

**四步实现流程**:

1. **步骤一：数据准备** 
   ```bash
   cd backend
   python -m ml.prepare_data --input ..\data\ml-latest-small\ratings.csv --output ..\data\output1\
   ```
   生成 `ratings_train.csv` 和 `ratings_test.csv`（训练/测试集）

2. **步骤二：模型训练** 
   ```bash
   python -m ml.train_mf --train ..\data\output1\ratings_train.csv --test ..\data\output1\ratings_test.csv --output ..\data\output2\
   ```
   生成 `als_model.pkl`（训练好的 ALS 矩阵分解模型）
   
   **测试模型**：
   ```bash
   python -m ml.test_model --model ..\data\output2\als_model.pkl
   ```

3. **步骤三：模型集成** 
   
4. **步骤四：API 接入** 

详细文档：`backend/ml/README.md`




