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




