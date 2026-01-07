# 矩阵分解推荐系统（4步实现）

## 概述
本模块实现基于矩阵分解（Matrix Factorization）的协同过滤推荐系统，适用于策略 D（用户有充足行为数据，评分≥10）。

## 四步实现流程

### 步骤一：数据准备模块 ✅
**文件**: `prepare_data.py`

**功能**:
- 加载 MovieLens 评分数据（ratings.csv）
- 数据清洗与验证（检查缺失值、异常值）
- 划分训练集/测试集（支持随机划分或按时间划分）
- 保存处理后的数据

**运行方法**:
```bash
cd backend
python -m ml.prepare_data --input ../data/ml-latest-small/ratings.csv --output ../data/output1/
```

**参数说明**:
- `--input`: 输入评分文件路径（默认 `../data/ml-latest-small/ratings.csv`）
- `--output`: 输出目录（默认 `../data/output1/`）
- `--test-size`: 测试集比例（默认 0.2）
- `--split-method`: 划分方法，`random`（随机）或 `time`（按时间，推荐）
- `--random-state`: 随机种子（仅对 random 方法有效）

**输出**:
- `ratings_train.csv`: 训练集
- `ratings_test.csv`: 测试集
- `split_meta.txt`: 划分元数据（记录划分参数和统计信息）

---

### 步骤二：模型训练与评估模块 ✅
**文件**: `train_mf.py`

**功能**:
- 使用 ALS（交替最小二乘法）训练矩阵分解模型
- 在训练集上训练模型
- 在测试集上评估 RMSE/MAE
- 保存训练好的模型

**运行方法**:
```bash
cd backend
python -m ml.train_mf --train ../data/output1/ratings_train.csv --test ../data/output1/ratings_test.csv --output ../data/output2/
```

**参数说明**:
- `--train`: 训练集路径（步骤一生成）
- `--test`: 测试集路径（步骤一生成）
- `--output`: 输出目录（保存模型和报告）
- `--n-factors`: 隐因子数量（默认 50，课程项目推荐 20~100）
- `--n-epochs`: 训练轮数（默认 20，快速验证可用 10）
- `--lr`: 学习率（默认 0.01）
- `--reg`: 正则化系数（默认 0.02）
- `--cv`: 交叉验证折数（默认 0，即不做；设为 5 可做 5 折交叉验证）

**输出**:
- `als_model.pkl`: 训练好的模型（可用 pickle 加载）
- `evaluation_report.txt`: 评估报告（RMSE/MAE/参数）
- `predictions_sample.csv`: 预测样本（前 100 条，含真实值/预测值/误差）

**示例结果**（10 轮训练，20 隐因子）:
- 训练集 RMSE: 0.3941（过拟合严重）
- 测试集 RMSE: 1.1277 ⚠
- 测试集 MAE: 0.8786
- 过拟合程度: 186.1% ⚠⚠
- 训练耗时: ~11 秒

**结论**：该参数组合存在严重过拟合，需要调参！

**调参建议**：详见 `TUNING_GUIDE.md`

---

### 参数调优工具 ✅
**文件**: `tune_params.py`

**功能**:
- 网格搜索最佳超参数（n_factors, n_epochs, reg, learning_rate）
- 自动评估所有参数组合
- 输出最佳模型和性能对比表

**运行方法**（快速模式）:
```bash
cd backend
python -m ml.tune_params --train ../data/output1/ratings_train.csv --test ../data/output1/ratings_test.csv --output ../data/output3/ --quick
```

**完整模式**（更多参数组合，需要 ~1 小时）:
```bash
python -m ml.tune_params --train ../data/output1/ratings_train.csv --test ../data/output1/ratings_test.csv --output ../data/output3/
```

**输出**:
- `best_model.pkl`: 最佳模型
- `grid_search_results.csv`: 所有参数组合对比表
- `tuning_report.txt`: 调优报告

---

### 调参指南 📖
**文件**: `TUNING_GUIDE.md`

包含：
- 关键指标解读（RMSE/MAE/过拟合程度/覆盖率）
- 超参数调优策略（n_factors/reg/n_epochs/learning_rate）
- 调参实战案例（过拟合/欠拟合/理想状态）
- 推荐的调参流程

---

### 步骤三：模型集成模块 
**文件**: `recommender.py`

**功能**:
- 加载训练好的模型
- 提供 `get_recommendations(user_id, n=10)` 函数供 Web 后端调用
- 过滤用户已评分/收藏的电影
- 返回 Top-N 推荐结果

---

### 步骤四：API 接入模块 
**位置**: `backend/services/recommendation_service.py`（扩展现有函数）

**功能**:
- 在 `get_recommendations_for_user()` 的策略 D 分支中，调用 `recommender.py` 的服务
- 为前端提供推荐列表（集成到现有 `/api/recommendations` 接口）

---

## 依赖安装

确保安装了机器学习相关依赖：
```bash
cd backend
pip install -r requirements.txt
```

主要依赖：
- `pandas`: 数据处理
- `numpy`: 数值计算
- `scikit-learn`: 数据划分、预处理
- `scikit-surprise`: 协同过滤/矩阵分解

---

## 数据说明

本模块使用 **MovieLens ml-latest-small** 数据集：
- **ratings.csv**: 100,836 条评分记录
  - `userId`: 用户ID
  - `movieId`: 电影ID
  - `rating`: 评分（0.5~5.0）
  - `timestamp`: 时间戳

- **movies.csv**: 9,742 部电影
  - `movieId`: 电影ID
  - `title`: 标题
  - `genres`: 类型（用 `|` 分隔）

数据集下载：`https://grouplens.org/datasets/movielens/`

---

## 后续优化方向

1. **模型调优**：网格搜索最佳超参数（factors, lr, regularization）
2. **模型融合**：混合多个模型（SVD + NMF + 内容推荐）
3. **冷启动处理**：新用户/新电影的推荐策略
4. **实时更新**：增量训练，避免每次重新训练全量数据

