"""
步骤一改进版：数据准备模块（修复冷启动问题）

改进点：
1. 按用户分组划分：确保每个用户的评分同时出现在训练集和测试集
2. 避免冷启动：测试集中的用户和电影在训练集中都有数据
3. 更符合推荐系统的真实评估场景

使用方法：
    python -m ml.prepare_data_v2 --input ../data/ml-latest-small/ratings.csv --output ../data/output1_fixed/
"""

import argparse
import os
from datetime import datetime

import pandas as pd
import numpy as np


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
    print(f"  - 每用户平均评分数: {df.groupby('userId').size().mean():.1f}")
    
    # 5. 评分数分布
    user_rating_counts = df.groupby('userId').size()
    print(f"  - 评分数分布:")
    print(f"    min: {user_rating_counts.min()}, max: {user_rating_counts.max()}")
    print(f"    median: {user_rating_counts.median():.0f}")
    print(f"    少于5条评分的用户: {(user_rating_counts < 5).sum()} 个")
    
    return df


def split_data_by_user(df, test_size=0.2, min_ratings=5, random_state=42):
    """
    按用户分组划分训练集和测试集（改进版，避免冷启动）
    
    策略：
    1. 对每个用户，将其评分按比例划分到训练集和测试集
    2. 评分数少于 min_ratings 的用户，全部放入训练集
    3. 这样可以确保测试集中的用户在训练集中都有数据
    
    Args:
        df: 清洗后的数据
        test_size: 测试集比例（默认 0.2）
        min_ratings: 最少评分数要求（少于此数的用户全部放训练集）
        random_state: 随机种子
    
    Returns:
        train_df, test_df: 训练集和测试集
    """
    print(f"\n[3/4] 按用户分组划分训练集/测试集")
    print(f"  - 测试集比例: {test_size}")
    print(f"  - 最少评分数要求: {min_ratings}")
    
    np.random.seed(random_state)
    
    train_list = []
    test_list = []
    
    cold_start_users = 0
    total_users = 0
    
    # 按用户分组
    grouped = df.groupby('userId')
    
    for user_id, user_data in grouped:
        total_users += 1
        n_ratings = len(user_data)
        
        if n_ratings < min_ratings:
            # 评分太少，全部放训练集，避免数据泄露
            train_list.append(user_data)
            cold_start_users += 1
        else:
            # 随机划分该用户的评分
            n_test = max(1, int(n_ratings * test_size))  # 至少1条到测试集
            n_train = n_ratings - n_test
            
            # 随机采样
            test_indices = user_data.sample(n=n_test, random_state=random_state).index
            train_indices = user_data.index.difference(test_indices)
            
            train_list.append(user_data.loc[train_indices])
            test_list.append(user_data.loc[test_indices])
    
    train_df = pd.concat(train_list, ignore_index=True)
    test_df = pd.concat(test_list, ignore_index=True) if test_list else pd.DataFrame()
    
    print(f"  - 总用户数: {total_users}")
    print(f"  - 评分少于{min_ratings}条的用户（仅在训练集）: {cold_start_users} ({cold_start_users/total_users*100:.1f}%)")
    print(f"  - 参与测试的用户: {len(test_list)} ({len(test_list)/total_users*100:.1f}%)")
    print(f"  - 训练集: {len(train_df)} 条 ({len(train_df)/(len(train_df)+len(test_df))*100:.1f}%)")
    print(f"  - 测试集: {len(test_df)} 条 ({len(test_df)/(len(train_df)+len(test_df))*100:.1f}%)")
    
    # 验证划分质量
    print(f"\n  评分分布验证:")
    print(f"  - 训练集平均评分: {train_df['rating'].mean():.3f}")
    print(f"  - 测试集平均评分: {test_df['rating'].mean():.3f}")
    
    # 验证冷启动情况
    print(f"\n  冷启动检验:")
    test_users_in_train = test_df['userId'].isin(train_df['userId']).sum()
    test_movies_in_train = test_df['movieId'].isin(train_df['movieId']).sum()
    print(f"  - 测试集用户在训练集出现: {test_users_in_train}/{len(test_df)} ({test_users_in_train/len(test_df)*100:.1f}%)")
    print(f"  - 测试集电影在训练集出现: {test_movies_in_train}/{len(test_df)} ({test_movies_in_train/len(test_df)*100:.1f}%)")
    
    # 计算冷启动预测数
    cold_start_count = len(test_df[
        ~test_df['userId'].isin(train_df['userId']) | 
        ~test_df['movieId'].isin(train_df['movieId'])
    ])
    print(f"  - 冷启动预测数: {cold_start_count}/{len(test_df)} ({cold_start_count/len(test_df)*100:.1f}%)")
    
    if cold_start_count / len(test_df) > 0.3:
        print(f"  [警告] 冷启动比例仍然较高（>{30}%）")
        print(f"  建议: 增加 min_ratings 参数或检查数据质量")
    else:
        print(f"  [OK] 冷启动比例在合理范围内")
    
    return train_df, test_df


def save_data(train_df, test_df, output_dir, params_info):
    """
    保存处理后的数据
    
    Args:
        train_df: 训练集
        test_df: 测试集
        output_dir: 输出目录
        params_info: 参数信息字典
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
        f.write(f"Data Split Metadata (User-based Split)\n")
        f.write(f"Created at: {datetime.now().isoformat()}\n")
        f.write(f"Split method: user-based (避免冷启动)\n")
        f.write(f"Parameters:\n")
        for k, v in params_info.items():
            f.write(f"  - {k}: {v}\n")
        f.write(f"\nStatistics:\n")
        f.write(f"  Train size: {len(train_df)}\n")
        f.write(f"  Test size: {len(test_df)}\n")
        f.write(f"  Train users: {train_df['userId'].nunique()}\n")
        f.write(f"  Test users: {test_df['userId'].nunique()}\n")
        f.write(f"  Train movies: {train_df['movieId'].nunique()}\n")
        f.write(f"  Test movies: {test_df['movieId'].nunique()}\n")
        f.write(f"  Train mean rating: {train_df['rating'].mean():.3f}\n")
        f.write(f"  Test mean rating: {test_df['rating'].mean():.3f}\n")
        
        # 冷启动统计
        test_users_in_train = test_df['userId'].isin(train_df['userId']).sum()
        test_movies_in_train = test_df['movieId'].isin(train_df['movieId']).sum()
        cold_start_count = len(test_df[
            ~test_df['userId'].isin(train_df['userId']) | 
            ~test_df['movieId'].isin(train_df['movieId'])
        ])
        f.write(f"\nCold Start Analysis:\n")
        f.write(f"  Test users in train: {test_users_in_train}/{len(test_df)} ({test_users_in_train/len(test_df)*100:.1f}%)\n")
        f.write(f"  Test movies in train: {test_movies_in_train}/{len(test_df)} ({test_movies_in_train/len(test_df)*100:.1f}%)\n")
        f.write(f"  Cold start predictions: {cold_start_count}/{len(test_df)} ({cold_start_count/len(test_df)*100:.1f}%)\n")
    
    print(f"  - 元数据已保存: {meta_path}")


def main():
    parser = argparse.ArgumentParser(
        description="步骤一改进版：数据准备模块（按用户分组划分，避免冷启动）"
    )
    parser.add_argument("--input", default="../data/ml-latest-small/ratings.csv", 
                       help="输入评分文件路径（ratings.csv）")
    parser.add_argument("--output", default="../data/output1_fixed/", 
                       help="输出目录（保存 train/test）")
    parser.add_argument("--test-size", type=float, default=0.2, 
                       help="测试集比例（默认 0.2）")
    parser.add_argument("--min-ratings", type=int, default=5, 
                       help="用户最少评分数要求（默认 5，少于此数全部放训练集）")
    parser.add_argument("--random-state", type=int, default=42, 
                       help="随机种子")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("步骤一改进版：数据准备模块（按用户分组划分）")
    print("=" * 70)
    
    # 1. 加载数据
    df = load_ratings(args.input)
    
    # 2. 清洗数据
    df = clean_data(df)
    
    # 3. 按用户分组划分训练/测试集
    train_df, test_df = split_data_by_user(
        df, 
        test_size=args.test_size, 
        min_ratings=args.min_ratings,
        random_state=args.random_state
    )
    
    # 4. 保存数据
    params_info = {
        "test_size": args.test_size,
        "min_ratings": args.min_ratings,
        "random_state": args.random_state,
    }
    save_data(train_df, test_df, args.output, params_info)
    
    print("\n" + "=" * 70)
    print("步骤一完成！可以进入步骤二（模型训练）")
    print("=" * 70)
    print("\n下一步:")
    print(f"  python -m ml.train_mf --train {args.output}ratings_train.csv \\")
    print(f"                        --test {args.output}ratings_test.csv \\")
    print(f"                        --output ../data/output2_fixed/ \\")
    print(f"                        --n-factors 50 --n-epochs 20 --reg 0.02")
    print()


if __name__ == "__main__":
    main()

