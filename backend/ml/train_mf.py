"""
步骤二：模型训练与评估模块（简化版，基于 numpy/scipy）
功能：
1. 加载训练集/测试集（步骤一生成的数据）
2. 使用 ALS（交替最小二乘法）训练矩阵分解模型
3. 在测试集上评估 RMSE/MAE
4. 保存训练好的模型

使用方法：
    python -m ml.train_mf --train ../data/output1/ratings_train.csv --test ../data/output1/ratings_test.csv --output ../data/output2/

算法说明：
- ALS（Alternating Least Squares）：交替固定用户矩阵/物品矩阵，求解最小二乘问题
- 评分预测公式：r̂(u,i) = μ + b_u + b_i + q_i^T · p_u
  其中：μ=全局均值，b_u=用户偏差，b_i=物品偏差，p_u=用户隐向量，q_i=物品隐向量
"""

import argparse
import os
import pickle
import time
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix


class MatrixFactorizationALS:
    """
    基于 ALS（交替最小二乘法）的矩阵分解推荐模型
    
    参数：
        n_factors: 隐因子数量（默认 50）
        n_epochs: 训练轮数（默认 20）
        reg: 正则化系数（默认 0.02）
        learning_rate: 学习率（用于偏差项更新，默认 0.01）
    """
    
    def __init__(self, n_factors=50, n_epochs=20, reg=0.02, learning_rate=0.01, random_state=42):
        self.n_factors = n_factors
        self.n_epochs = n_epochs
        self.reg = reg
        self.learning_rate = learning_rate
        self.random_state = random_state
        
        # 模型参数（训练后会被赋值）
        self.global_mean = 0
        self.user_bias = None
        self.item_bias = None
        self.user_factors = None
        self.item_factors = None
        self.user_map = {}  # userId -> 内部索引
        self.item_map = {}  # movieId -> 内部索引
        
    def fit(self, train_df):
        """
        训练模型
        
        Args:
            train_df: 训练集 DataFrame，包含 userId, movieId, rating
        """
        np.random.seed(self.random_state)
        
        # 1. 构建用户/物品映射
        unique_users = train_df["userId"].unique()
        unique_items = train_df["movieId"].unique()
        self.user_map = {uid: idx for idx, uid in enumerate(unique_users)}
        self.item_map = {iid: idx for idx, iid in enumerate(unique_items)}
        
        n_users = len(self.user_map)
        n_items = len(self.item_map)
        
        # 2. 初始化参数
        self.global_mean = train_df["rating"].mean()
        self.user_bias = np.zeros(n_users)
        self.item_bias = np.zeros(n_items)
        self.user_factors = np.random.normal(0, 0.1, (n_users, self.n_factors))
        self.item_factors = np.random.normal(0, 0.1, (n_items, self.n_factors))
        
        # 3. 构建稀疏评分矩阵（用于 ALS）
        ratings = train_df["rating"].values
        user_indices = train_df["userId"].map(self.user_map).values
        item_indices = train_df["movieId"].map(self.item_map).values
        
        R = csr_matrix((ratings, (user_indices, item_indices)), shape=(n_users, n_items))
        R_T = R.T.tocsr()  # 转置矩阵（方便按物品迭代）
        
        # 4. ALS 迭代训练
        for epoch in range(self.n_epochs):
            # 4.1 固定 item_factors，更新 user_factors 和 user_bias
            for u in range(n_users):
                # 获取用户 u 评分过的物品
                item_ids = R.getrow(u).indices
                if len(item_ids) == 0:
                    continue
                
                r_u = R.getrow(u).data
                Q_u = self.item_factors[item_ids]  # (n_rated, n_factors)
                b_i_u = self.item_bias[item_ids]
                
                # 更新 user_factors[u]
                A = Q_u.T @ Q_u + self.reg * np.eye(self.n_factors)
                b = Q_u.T @ (r_u - self.global_mean - b_i_u - self.user_bias[u])
                self.user_factors[u] = np.linalg.solve(A, b)
                
                # 更新 user_bias[u]（使用梯度下降）
                pred = self.global_mean + self.user_bias[u] + b_i_u + Q_u @ self.user_factors[u]
                error = r_u - pred
                self.user_bias[u] += self.learning_rate * (error.sum() - self.reg * self.user_bias[u])
            
            # 4.2 固定 user_factors，更新 item_factors 和 item_bias
            for i in range(n_items):
                # 获取对物品 i 评分的用户
                user_ids = R_T.getrow(i).indices
                if len(user_ids) == 0:
                    continue
                
                r_i = R_T.getrow(i).data
                P_i = self.user_factors[user_ids]  # (n_raters, n_factors)
                b_u_i = self.user_bias[user_ids]
                
                # 更新 item_factors[i]
                A = P_i.T @ P_i + self.reg * np.eye(self.n_factors)
                b = P_i.T @ (r_i - self.global_mean - b_u_i - self.item_bias[i])
                self.item_factors[i] = np.linalg.solve(A, b)
                
                # 更新 item_bias[i]（使用梯度下降）
                pred = self.global_mean + b_u_i + self.item_bias[i] + P_i @ self.item_factors[i]
                error = r_i - pred
                self.item_bias[i] += self.learning_rate * (error.sum() - self.reg * self.item_bias[i])
            
            # 打印训练进度（每 5 轮一次）
            if (epoch + 1) % 5 == 0 or epoch == 0:
                train_rmse = self._compute_rmse(train_df)
                print(f"    Epoch {epoch+1}/{self.n_epochs}, Train RMSE: {train_rmse:.4f}")
    
    def predict(self, user_id, item_id):
        """
        预测单个评分
        
        Args:
            user_id: 用户ID
            item_id: 物品ID
            
        Returns:
            预测评分（0.5~5.0）
        """
        # 如果用户/物品不在训练集中，返回全局均值
        if user_id not in self.user_map or item_id not in self.item_map:
            return self.global_mean
        
        u = self.user_map[user_id]
        i = self.item_map[item_id]
        
        pred = self.global_mean + self.user_bias[u] + self.item_bias[i] + np.dot(self.user_factors[u], self.item_factors[i])
        
        # 裁剪到评分范围
        return np.clip(pred, 0.5, 5.0)
    
    def _compute_rmse(self, df):
        """计算 RMSE"""
        predictions = [self.predict(row["userId"], row["movieId"]) for _, row in df.iterrows()]
        errors = df["rating"].values - np.array(predictions)
        return np.sqrt(np.mean(errors ** 2))


def load_data(train_path, test_path):
    """
    加载训练集和测试集

    Args:
        train_path: 训练集 CSV 路径
        test_path: 测试集 CSV 路径

    Returns:
        train_df, test_df: pandas DataFrame
    """
    print(f"[1/5] 加载数据")
    print(f"  - 训练集: {train_path}")
    print(f"  - 测试集: {test_path}")

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    
    print(f"  - 训练集: {train_df['userId'].nunique()} 用户, {train_df['movieId'].nunique()} 电影, {len(train_df)} 评分")
    print(f"  - 测试集: {test_df['userId'].nunique()} 用户, {test_df['movieId'].nunique()} 电影, {len(test_df)} 评分")

    return train_df, test_df


def train_model(train_df, n_factors=50, n_epochs=20, reg=0.02, learning_rate=0.01):
    """
    训练矩阵分解模型

    Args:
        train_df: 训练集 DataFrame
        n_factors: 隐因子数量
        n_epochs: 训练轮数
        reg: 正则化系数
        learning_rate: 学习率

    Returns:
        trained_model: 训练好的模型, train_time: 训练耗时
    """
    print(f"\n[2/5] 训练模型: ALS（交替最小二乘法）")
    print(f"  - 隐因子数量: {n_factors}")
    print(f"  - 训练轮数: {n_epochs}")
    print(f"  - 正则化系数: {reg}")
    print(f"  - 学习率: {learning_rate}")

    # 训练模型
    start_time = time.time()
    model = MatrixFactorizationALS(
        n_factors=n_factors, 
        n_epochs=n_epochs, 
        reg=reg, 
        learning_rate=learning_rate,
        random_state=42
    )
    model.fit(train_df)
    train_time = time.time() - start_time

    print(f"  - 训练完成，耗时: {train_time:.2f} 秒")

    return model, train_time


def evaluate_model(model, test_df, train_df=None):
    """
    在测试集上评估模型（可选：同时评估训练集以检测过拟合）

    Args:
        model: 训练好的模型
        test_df: 测试集 DataFrame
        train_df: 训练集 DataFrame（可选，用于检测过拟合）

    Returns:
        metrics: 评估指标 (RMSE, MAE, Coverage 等)
    """
    print(f"\n[3/5] 评估模型")

    # 1. 测试集评估
    print("  测试集评估:")
    test_predictions = []
    test_true_ratings = []
    
    for _, row in test_df.iterrows():
        pred = model.predict(row["userId"], row["movieId"])
        test_predictions.append(pred)
        test_true_ratings.append(row["rating"])
    
    test_predictions = np.array(test_predictions)
    test_true_ratings = np.array(test_true_ratings)
    
    test_errors = test_true_ratings - test_predictions
    test_rmse = np.sqrt(np.mean(test_errors ** 2))
    test_mae = np.mean(np.abs(test_errors))
    
    print(f"    - RMSE (均方根误差): {test_rmse:.4f}")
    print(f"    - MAE  (平均绝对误差): {test_mae:.4f}")

    # 2. 训练集评估（检测过拟合）
    train_rmse = None
    train_mae = None
    if train_df is not None:
        print("  训练集评估（过拟合检测）:")
        train_predictions = []
        train_true_ratings = []
        
        # 采样评估（如果训练集太大，只评估一部分）
        sample_size = min(10000, len(train_df))
        train_sample = train_df.sample(n=sample_size, random_state=42)
        
        for _, row in train_sample.iterrows():
            pred = model.predict(row["userId"], row["movieId"])
            train_predictions.append(pred)
            train_true_ratings.append(row["rating"])
        
        train_predictions = np.array(train_predictions)
        train_true_ratings = np.array(train_true_ratings)
        
        train_errors = train_true_ratings - train_predictions
        train_rmse = np.sqrt(np.mean(train_errors ** 2))
        train_mae = np.mean(np.abs(train_errors))
        
        print(f"    - RMSE: {train_rmse:.4f}")
        print(f"    - MAE:  {train_mae:.4f}")
        
        # 过拟合程度
        overfitting_ratio = (test_rmse - train_rmse) / train_rmse * 100
        print(f"    - 过拟合程度: {overfitting_ratio:.1f}% (测试集RMSE比训练集高 {overfitting_ratio:.1f}%)")
        if overfitting_ratio > 50:
            print("      [警告] 存在较严重的过拟合！建议减少隐因子数量或增加正则化")
        elif overfitting_ratio > 20:
            print("      [提示] 存在轻度过拟合，可适当调整参数")
        else:
            print("      [OK] 过拟合程度较低")
    
    # 3. 覆盖率评估（能为多少测试用户/电影提供预测）
    test_users_in_train = test_df["userId"].isin(model.user_map).sum()
    test_items_in_train = test_df["movieId"].isin(model.item_map).sum()
    user_coverage = test_users_in_train / len(test_df) * 100
    item_coverage = test_items_in_train / len(test_df) * 100
    
    print(f"  覆盖率:")
    print(f"    - 用户覆盖率: {user_coverage:.1f}% ({test_users_in_train}/{len(test_df)})")
    print(f"    - 物品覆盖率: {item_coverage:.1f}% ({test_items_in_train}/{len(test_df)})")

    return {
        "test_rmse": test_rmse,
        "test_mae": test_mae,
        "train_rmse": train_rmse,
        "train_mae": train_mae,
        "overfitting_ratio": ((test_rmse - train_rmse) / train_rmse * 100) if train_rmse else None,
        "user_coverage": user_coverage,
        "item_coverage": item_coverage,
        "predictions": test_predictions,
        "true_ratings": test_true_ratings
    }


def save_model(model, test_df, metrics, train_time, output_dir):
    """
    保存模型和评估报告

    Args:
        model: 训练好的模型
        test_df: 测试集 DataFrame
        metrics: 评估指标
        train_time: 训练耗时
        output_dir: 输出目录
    """
    print(f"\n[4/5] 保存模型: {output_dir}")

    os.makedirs(output_dir, exist_ok=True)

    # 保存模型（使用 pickle）
    model_path = os.path.join(output_dir, "als_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"  - 模型已保存: {model_path}")

    # 保存评估报告（增强版，包含调参建议）
    report_path = os.path.join(output_dir, "evaluation_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("模型训练与评估报告（ALS 矩阵分解）\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"训练时间: {datetime.now().isoformat()}\n")
        f.write(f"模型类型: ALS (Alternating Least Squares)\n")
        f.write(f"训练耗时: {train_time:.2f} 秒\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("1. 模型参数\n")
        f.write("-" * 70 + "\n")
        f.write(f"  - 隐因子数量 (n_factors): {model.n_factors}\n")
        f.write(f"  - 训练轮数 (n_epochs): {model.n_epochs}\n")
        f.write(f"  - 正则化系数 (reg): {model.reg}\n")
        f.write(f"  - 学习率 (learning_rate): {model.learning_rate}\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("2. 数据统计\n")
        f.write("-" * 70 + "\n")
        f.write(f"  - 训练用户数: {len(model.user_map)}\n")
        f.write(f"  - 训练物品数: {len(model.item_map)}\n")
        f.write(f"  - 全局平均评分: {model.global_mean:.3f}\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("3. 评估指标（训练集 vs 测试集）\n")
        f.write("-" * 70 + "\n")
        
        if metrics.get("train_rmse") is not None:
            f.write(f"训练集:\n")
            f.write(f"  - RMSE: {metrics['train_rmse']:.4f}\n")
            f.write(f"  - MAE:  {metrics['train_mae']:.4f}\n\n")
        
        f.write(f"测试集:\n")
        f.write(f"  - RMSE: {metrics['test_rmse']:.4f}\n")
        f.write(f"  - MAE:  {metrics['test_mae']:.4f}\n\n")
        
        if metrics.get("overfitting_ratio") is not None:
            f.write(f"过拟合分析:\n")
            f.write(f"  - 过拟合程度: {metrics['overfitting_ratio']:.1f}%\n")
            f.write(f"    (测试集RMSE比训练集高 {metrics['overfitting_ratio']:.1f}%)\n")
            if metrics['overfitting_ratio'] > 50:
                f.write(f"  - 诊断: [警告] 严重过拟合\n")
                f.write(f"  - 建议: 减少隐因子数量至 {max(10, model.n_factors // 2)} 或增加正则化至 {model.reg * 2:.3f}\n\n")
            elif metrics['overfitting_ratio'] > 20:
                f.write(f"  - 诊断: [提示] 轻度过拟合\n")
                f.write(f"  - 建议: 适当减少隐因子或增加正则化\n\n")
            else:
                f.write(f"  - 诊断: [OK] 过拟合程度较低\n\n")
        
        f.write(f"覆盖率:\n")
        f.write(f"  - 用户覆盖率: {metrics['user_coverage']:.1f}%\n")
        f.write(f"  - 物品覆盖率: {metrics['item_coverage']:.1f}%\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("4. 模型质量评估\n")
        f.write("-" * 70 + "\n")
        f.write("推荐系统典型指标基准（MovieLens）:\n")
        f.write("  - 优秀: RMSE < 0.85, MAE < 0.65\n")
        f.write("  - 良好: RMSE 0.85~0.95, MAE 0.65~0.75\n")
        f.write("  - 合格: RMSE 0.95~1.05, MAE 0.75~0.85\n")
        f.write("  - 需改进: RMSE > 1.05, MAE > 0.85\n\n")
        
        if metrics['test_rmse'] < 0.85:
            f.write(f"当前模型评级: ★★★★★ 优秀\n")
        elif metrics['test_rmse'] < 0.95:
            f.write(f"当前模型评级: ★★★★☆ 良好\n")
        elif metrics['test_rmse'] < 1.05:
            f.write(f"当前模型评级: ★★★☆☆ 合格\n")
        else:
            f.write(f"当前模型评级: ★★☆☆☆ 需改进\n")
        
        f.write("\n" + "-" * 70 + "\n")
        f.write("5. 调参建议\n")
        f.write("-" * 70 + "\n")
        f.write("参数调整方向:\n")
        
        # 基于当前结果给出具体建议
        if metrics['test_rmse'] > 1.05:
            f.write("  当前问题: 模型性能不足\n")
            f.write("  建议操作:\n")
            if metrics.get('overfitting_ratio', 0) > 30:
                f.write("    1. 减少过拟合:\n")
                f.write(f"       - 减少 n_factors 至 {max(10, model.n_factors // 2)}\n")
                f.write(f"       - 增加 reg 至 {min(0.1, model.reg * 2):.3f}\n")
            else:
                f.write("    1. 增强模型能力:\n")
                f.write(f"       - 增加 n_factors 至 {min(200, model.n_factors * 2)}\n")
                f.write(f"       - 增加 n_epochs 至 {model.n_epochs + 10}\n")
            f.write("    2. 运行参数调优脚本:\n")
            f.write("       python -m ml.tune_params --train ... --test ...\n")
        else:
            f.write("  当前模型性能已达到合格/良好水平\n")
            f.write("  可选优化:\n")
            f.write("    - 运行网格搜索寻找更优参数\n")
            f.write("    - 尝试模型融合（ALS + 内容推荐）\n")

    print(f"  - 评估报告已保存: {report_path}")

    # 保存预测样本（前 100 条）
    predictions_path = os.path.join(output_dir, "predictions_sample.csv")
    sample_size = min(100, len(test_df))
    pred_df = pd.DataFrame({
        "userId": test_df["userId"].iloc[:sample_size],
        "movieId": test_df["movieId"].iloc[:sample_size],
        "true_rating": metrics["true_ratings"][:sample_size],
        "pred_rating": metrics["predictions"][:sample_size],
        "error": np.abs(metrics["true_ratings"][:sample_size] - metrics["predictions"][:sample_size])
    })
    pred_df.to_csv(predictions_path, index=False)
    print(f"  - 预测样本已保存: {predictions_path}")


def cross_validation(train_path, cv=5, **model_params):
    """
    （可选）K 折交叉验证

    Args:
        train_path: 训练集路径
        cv: 折数
        model_params: 模型超参数

    Returns:
        cv_results: 交叉验证结果 (平均 RMSE/MAE)
    """
    print(f"\n[可选] {cv} 折交叉验证（在训练集上）")

    train_df = pd.read_csv(train_path)
    
    # 简单随机划分（真实场景应按用户划分避免数据泄露）
    from sklearn.model_selection import KFold
    kfold = KFold(n_splits=cv, shuffle=True, random_state=42)
    
    rmse_list = []
    mae_list = []
    
    for fold, (train_idx, val_idx) in enumerate(kfold.split(train_df), start=1):
        print(f"  Fold {fold}/{cv}...", end=" ")
        
        fold_train = train_df.iloc[train_idx]
        fold_val = train_df.iloc[val_idx]
        
        # 训练模型
        model = MatrixFactorizationALS(**model_params, random_state=42)
        model.fit(fold_train)
        
        # 评估
        preds = [model.predict(row["userId"], row["movieId"]) for _, row in fold_val.iterrows()]
        true_ratings = fold_val["rating"].values
        
        errors = true_ratings - np.array(preds)
        rmse = np.sqrt(np.mean(errors ** 2))
        mae = np.mean(np.abs(errors))
        
        rmse_list.append(rmse)
        mae_list.append(mae)
        
        print(f"RMSE: {rmse:.4f}, MAE: {mae:.4f}")
    
    print(f"\n  平均 RMSE: {np.mean(rmse_list):.4f} (±{np.std(rmse_list):.4f})")
    print(f"  平均 MAE:  {np.mean(mae_list):.4f} (±{np.std(mae_list):.4f})")
    
    return {"rmse_mean": np.mean(rmse_list), "rmse_std": np.std(rmse_list),
            "mae_mean": np.mean(mae_list), "mae_std": np.std(mae_list)}


def main():
    parser = argparse.ArgumentParser(description="步骤二：模型训练与评估模块（ALS 矩阵分解）")
    parser.add_argument("--train", default="../data/output1/ratings_train.csv", help="训练集路径")
    parser.add_argument("--test", default="../data/output1/ratings_test.csv", help="测试集路径")
    parser.add_argument("--output", default="../data/output2/", help="输出目录（保存模型和报告）")
    parser.add_argument("--n-factors", type=int, default=50, help="隐因子数量（默认 50）")
    parser.add_argument("--n-epochs", type=int, default=20, help="训练轮数（默认 20）")
    parser.add_argument("--lr", type=float, default=0.01, help="学习率（默认 0.01）")
    parser.add_argument("--reg", type=float, default=0.02, help="正则化系数（默认 0.02）")
    parser.add_argument("--cv", type=int, default=0, help="是否进行交叉验证（0=否，>0=折数）")

    args = parser.parse_args()

    print("=" * 60)
    print("步骤二：模型训练与评估模块（ALS 矩阵分解）")
    print("=" * 60)

    # 模型超参数
    model_params = {
        "n_factors": args.n_factors,
        "n_epochs": args.n_epochs,
        "reg": args.reg,
        "learning_rate": args.lr,
    }

    # （可选）交叉验证
    if args.cv > 0:
        cross_validation(args.train, cv=args.cv, **model_params)
        print("\n交叉验证完成，继续训练最终模型...\n")

    # 1. 加载数据
    train_df, test_df = load_data(args.train, args.test)

    # 2. 训练模型
    model, train_time = train_model(
        train_df, 
        n_factors=args.n_factors,
        n_epochs=args.n_epochs,
        reg=args.reg,
        learning_rate=args.lr
    )

    # 3. 评估模型
    metrics = evaluate_model(model, test_df, train_df=train_df)

    # 4. 保存模型
    save_model(model, test_df, metrics, train_time, args.output)

    print("\n" + "=" * 60)
    print(f"步骤二完成！模型已保存到: {args.output}")
    print("可以进入步骤三（模型集成）")
    print("=" * 60)


if __name__ == "__main__":
    main()

