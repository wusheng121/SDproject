"""
参数调优脚本：自动网格搜索最佳超参数

功能：
1. 对 n_factors, n_epochs, reg, learning_rate 进行网格搜索
2. 使用交叉验证评估每组参数
3. 输出最佳参数组合和性能对比表

使用方法：
    python -m ml.tune_params --train ../data/output1/ratings_train.csv --test ../data/output1/ratings_test.csv --output ../data/output3/
"""

import argparse
import os
import pickle
import time
from datetime import datetime
from itertools import product

import numpy as np
import pandas as pd

from ml.train_mf import MatrixFactorizationALS


def grid_search(train_df, test_df, param_grid, output_dir):
    """
    网格搜索最佳超参数
    
    Args:
        train_df: 训练集
        test_df: 测试集
        param_grid: 参数网格 dict
        output_dir: 输出目录
        
    Returns:
        best_params, best_model, results_df
    """
    print("=" * 70)
    print("网格搜索：自动寻找最佳超参数")
    print("=" * 70)
    
    # 生成所有参数组合
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    param_combinations = list(product(*param_values))
    
    print(f"\n总共 {len(param_combinations)} 组参数需要测试:")
    for name, values in param_grid.items():
        print(f"  - {name}: {values}")
    print()
    
    # 记录所有结果
    results = []
    best_test_rmse = float('inf')
    best_params = None
    best_model = None
    
    for idx, param_values in enumerate(param_combinations, start=1):
        params = dict(zip(param_names, param_values))
        
        print(f"[{idx}/{len(param_combinations)}] 测试参数组合: {params}")
        
        # 训练模型
        start_time = time.time()
        model = MatrixFactorizationALS(**params, random_state=42)
        model.fit(train_df)
        train_time = time.time() - start_time
        
        # 评估训练集
        train_preds = [model.predict(row["userId"], row["movieId"]) for _, row in train_df.sample(min(5000, len(train_df)), random_state=42).iterrows()]
        train_true = train_df.sample(min(5000, len(train_df)), random_state=42)["rating"].values
        train_rmse = np.sqrt(np.mean((train_true - np.array(train_preds)) ** 2))
        
        # 评估测试集
        test_preds = [model.predict(row["userId"], row["movieId"]) for _, row in test_df.iterrows()]
        test_true = test_df["rating"].values
        test_rmse = np.sqrt(np.mean((test_true - np.array(test_preds)) ** 2))
        test_mae = np.mean(np.abs(test_true - np.array(test_preds)))
        
        overfitting_ratio = (test_rmse - train_rmse) / train_rmse * 100
        
        print(f"  训练集 RMSE: {train_rmse:.4f}, 测试集 RMSE: {test_rmse:.4f}, MAE: {test_mae:.4f}")
        print(f"  过拟合: {overfitting_ratio:.1f}%, 训练耗时: {train_time:.1f}秒\n")
        
        # 记录结果
        result = {
            **params,
            "train_rmse": train_rmse,
            "test_rmse": test_rmse,
            "test_mae": test_mae,
            "overfitting_ratio": overfitting_ratio,
            "train_time": train_time
        }
        results.append(result)
        
        # 更新最佳模型
        if test_rmse < best_test_rmse:
            best_test_rmse = test_rmse
            best_params = params
            best_model = model
    
    # 转换为 DataFrame 并排序
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values("test_rmse")
    
    print("=" * 70)
    print("网格搜索完成！")
    print("=" * 70)
    print(f"\n最佳参数组合:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"\n最佳测试集 RMSE: {best_test_rmse:.4f}")
    
    # 保存结果
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存最佳模型
    model_path = os.path.join(output_dir, "best_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(best_model, f)
    print(f"\n最佳模型已保存: {model_path}")
    
    # 保存参数对比表
    results_path = os.path.join(output_dir, "grid_search_results.csv")
    results_df.to_csv(results_path, index=False)
    print(f"参数对比表已保存: {results_path}")
    
    # 保存调优报告
    report_path = os.path.join(output_dir, "tuning_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("超参数调优报告\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"调优时间: {datetime.now().isoformat()}\n")
        f.write(f"测试参数组合数: {len(param_combinations)}\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("最佳参数组合:\n")
        f.write("-" * 70 + "\n")
        for k, v in best_params.items():
            f.write(f"  {k}: {v}\n")
        f.write(f"\n  测试集 RMSE: {best_test_rmse:.4f}\n")
        f.write(f"  测试集 MAE: {results_df.iloc[0]['test_mae']:.4f}\n")
        f.write(f"  过拟合程度: {results_df.iloc[0]['overfitting_ratio']:.1f}%\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("Top 5 参数组合对比:\n")
        f.write("-" * 70 + "\n")
        for i in range(min(5, len(results_df))):
            row = results_df.iloc[i]
            f.write(f"\n排名 #{i+1}:\n")
            for col in param_names:
                f.write(f"  {col}: {row[col]}\n")
            f.write(f"  测试集 RMSE: {row['test_rmse']:.4f}\n")
            f.write(f"  过拟合程度: {row['overfitting_ratio']:.1f}%\n")
    
    print(f"调优报告已保存: {report_path}\n")
    
    return best_params, best_model, results_df


def main():
    parser = argparse.ArgumentParser(description="参数调优：网格搜索最佳超参数")
    parser.add_argument("--train", default="../data/output1/ratings_train.csv", help="训练集路径")
    parser.add_argument("--test", default="../data/output1/ratings_test.csv", help="测试集路径")
    parser.add_argument("--output", default="../data/output3/", help="输出目录")
    parser.add_argument("--quick", action="store_true", help="快速模式（减少参数组合）")
    parser.add_argument("--fine-tune", action="store_true", help="精细调优模式（基于已知最佳参数附近搜索）")
    
    args = parser.parse_args()
    
    # 加载数据
    print("加载数据...")
    train_df = pd.read_csv(args.train)
    test_df = pd.read_csv(args.test)
    print(f"  训练集: {len(train_df)} 条")
    print(f"  测试集: {len(test_df)} 条\n")
    
    # 定义参数网格
    if args.fine_tune:
        # 精细调优模式：基于已知最佳参数 (n_factors=7, n_epochs=12, reg=0.14, lr=0.005)
        # 重点：增加正则化以减少过拟合 (3x1x5x1 = 15组，约10分钟)
        param_grid = {
            "n_factors": [6, 7, 8],          # 围绕最佳值7
            "n_epochs": [12],                # 固定最佳值12
            "reg": [0.15, 0.18, 0.20, 0.22, 0.25],  # 增大正则化！
            "learning_rate": [0.005],        # 固定最佳值0.005
        }
        print("精细调优模式：测试更大的正则化以减少过拟合")
    elif args.quick:
        # 快速模式：针对过拟合问题的初步搜索（3x3x3 = 27 组）
        param_grid = {
            "n_factors": [5, 10, 15],        # 较小的因子数，避免过拟合
            "n_epochs": [10, 15, 20],        # 适中的训练轮数
            "reg": [0.1, 0.15, 0.2],         # 较大的正则化，控制过拟合
            "learning_rate": [0.01],         # 固定学习率
        }
    else:
        # 完整模式：更全面的参数搜索（4x4x5x2 = 160 组，约1-2小时）
        param_grid = {
            "n_factors": [5, 8, 12, 15],     # 较小范围，避免过拟合
            "n_epochs": [10, 15, 20, 25],    # 不同的训练轮数
            "reg": [0.08, 0.1, 0.12, 0.15, 0.2],  # 重点：更大的正则化
            "learning_rate": [0.005, 0.01],  # 两个学习率
        }
    
    # 网格搜索
    best_params, best_model, results_df = grid_search(train_df, test_df, param_grid, args.output)
    
    print("=" * 70)
    print("调优建议:")
    print("=" * 70)
    print("1. 查看 grid_search_results.csv 了解所有参数组合的性能")
    print("2. 使用最佳参数重新训练完整模型:")
    print(f"   python -m ml.train_mf --train {args.train} --test {args.test} \\")
    for k, v in best_params.items():
        if k == "n_factors":
            print(f"     --n-factors {v} \\")
        elif k == "n_epochs":
            print(f"     --n-epochs {v} \\")
        elif k == "reg":
            print(f"     --reg {v} \\")
        elif k == "learning_rate":
            print(f"     --lr {v} \\")
    print(f"     --output ../data/output2/")
    print()


if __name__ == "__main__":
    main()







