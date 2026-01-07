"""
步骤一：数据准备模块
功能：
1. 加载 MovieLens 评分数据
2. 数据清洗与验证
3. 划分训练集/测试集
4. 保存处理后的数据供模型训练使用

使用方法：
    python -m ml.prepare_data --input ../data/ml-latest-small/ratings.csv --output ../data/output1/
"""

import argparse
import os
from datetime import datetime

import pandas as pd
from sklearn.model_selection import train_test_split


def load_ratings(file_path):
    """
    加载评分数据

    Args:
        file_path: ratings.csv 文件路径

    Returns:
        DataFrame: 包含 userId, movieId, rating, timestamp 列
    """
    print(f"[1/4] 加载评分数据: {file_path}")
    df = pd.read_csv(file_path)
    print(f"  - 原始数据: {df.shape[0]} 条评分记录")
    print(f"  - 列名: {df.columns.tolist()}")
    return df


def clean_data(df):
    """
    数据清洗与验证

    Args:
        df: 原始评分数据

    Returns:
        DataFrame: 清洗后的数据
    """
    print("\n[2/4] 数据清洗与验证")

    # 1. 检查缺失值
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print(f"  - 发现缺失值: {missing[missing > 0].to_dict()}")
        df = df.dropna()
        print(f"  - 删除缺失值后剩余: {df.shape[0]} 条")
    else:
        print("  - 无缺失值 OK")

    # 2. 验证评分范围（通常是 0.5~5.0）
    rating_min = df["rating"].min()
    rating_max = df["rating"].max()
    print(f"  - 评分范围: [{rating_min}, {rating_max}]")

    # 3. 删除异常评分（如果有）
    valid_ratings = (df["rating"] >= 0.5) & (df["rating"] <= 5.0)
    invalid_count = (~valid_ratings).sum()
    if invalid_count > 0:
        print(f"  - 发现 {invalid_count} 条异常评分，已删除")
        df = df[valid_ratings]

    # 4. 统计信息
    print(f"  - 用户数: {df['userId'].nunique()}")
    print(f"  - 电影数: {df['movieId'].nunique()}")
    print(f"  - 平均评分: {df['rating'].mean():.2f}")
    print(f"  - 评分分布:\n{df['rating'].value_counts().sort_index()}")

    return df


def split_data(df, test_size=0.2, split_method="random", random_state=42):
    """
    划分训练集和测试集

    Args:
        df: 清洗后的数据
        test_size: 测试集比例（默认 0.2）
        split_method: 划分方法，'random'（随机划分）或 'time'（按时间划分）
        random_state: 随机种子

    Returns:
        train_df, test_df: 训练集和测试集
    """
    print(f"\n[3/4] 划分训练集/测试集 (方法: {split_method}, 测试集比例: {test_size})")

    if split_method == "time":
        # 按时间划分：最新的一部分作为测试集（更符合真实推荐场景）
        df_sorted = df.sort_values("timestamp")
        split_idx = int(len(df_sorted) * (1 - test_size))
        train_df = df_sorted.iloc[:split_idx].copy()
        test_df = df_sorted.iloc[split_idx:].copy()
        print(f"  - 按时间排序，前 {1-test_size:.0%} 作为训练集，后 {test_size:.0%} 作为测试集")
    else:
        # 随机划分
        train_df, test_df = train_test_split(df, test_size=test_size, random_state=random_state)
        print(f"  - 随机划分（random_state={random_state}）")

    print(f"  - 训练集: {train_df.shape[0]} 条")
    print(f"  - 测试集: {test_df.shape[0]} 条")

    # 验证划分是否合理（检查训练集和测试集的评分分布是否相似）
    print(f"  - 训练集平均评分: {train_df['rating'].mean():.3f}")
    print(f"  - 测试集平均评分: {test_df['rating'].mean():.3f}")

    return train_df, test_df


def save_data(train_df, test_df, output_dir):
    """
    保存处理后的数据

    Args:
        train_df: 训练集
        test_df: 测试集
        output_dir: 输出目录
    """
    print(f"\n[4/4] 保存处理后的数据: {output_dir}")

    os.makedirs(output_dir, exist_ok=True)

    train_path = os.path.join(output_dir, "ratings_train.csv")
    test_path = os.path.join(output_dir, "ratings_test.csv")

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"  - 训练集已保存: {train_path}")
    print(f"  - 测试集已保存: {test_path}")

    # 保存元数据（记录划分参数，便于追溯）
    meta_path = os.path.join(output_dir, "split_meta.txt")
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(f"Data Split Metadata\n")
        f.write(f"Created at: {datetime.now().isoformat()}\n")
        f.write(f"Train size: {train_df.shape[0]}\n")
        f.write(f"Test size: {test_df.shape[0]}\n")
        f.write(f"Train mean rating: {train_df['rating'].mean():.3f}\n")
        f.write(f"Test mean rating: {test_df['rating'].mean():.3f}\n")
    print(f"  - 元数据已保存: {meta_path}")


def main():
    parser = argparse.ArgumentParser(description="步骤一：数据准备模块（加载、清洗、划分、保存）")
    parser.add_argument("--input", default="../data/ml-latest-small/ratings.csv", help="输入评分文件路径（ratings.csv）")
    parser.add_argument("--output", default="../data/ml-latest-small/", help="输出目录（保存 train/test）")
    parser.add_argument("--test-size", type=float, default=0.2, help="测试集比例（默认 0.2）")
    parser.add_argument(
        "--split-method", choices=["random", "time"], default="time", help="划分方法：random（随机）或 time（按时间）"
    )
    parser.add_argument("--random-state", type=int, default=42, help="随机种子（仅对 random 方法有效）")

    args = parser.parse_args()

    print("=" * 60)
    print("步骤一：数据准备模块")
    print("=" * 60)

    # 1. 加载数据
    df = load_ratings(args.input)

    # 2. 清洗数据
    df = clean_data(df)

    # 3. 划分训练/测试集
    train_df, test_df = split_data(df, test_size=args.test_size, split_method=args.split_method, random_state=args.random_state)

    # 4. 保存数据
    save_data(train_df, test_df, args.output)

    print("\n" + "=" * 60)
    print("步骤一完成！可以进入步骤二（模型训练）")
    print("=" * 60)


if __name__ == "__main__":
    main()

