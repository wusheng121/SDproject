"""
测试脚本：加载并使用训练好的模型

使用方法：
    python -m ml.test_model --model ../data/output2/als_model.pkl
"""

import argparse
import pickle

import numpy as np

# 导入模型类（pickle 反序列化需要）
from ml.train_mf import MatrixFactorizationALS


def main():
    parser = argparse.ArgumentParser(description="测试加载并使用训练好的模型")
    parser.add_argument("--model", default="../data/output2/als_model.pkl", help="模型路径")
    args = parser.parse_args()

    print("=" * 60)
    print("测试脚本：加载并使用训练好的模型")
    print("=" * 60)

    # 1. 加载模型
    print(f"\n[1/3] 加载模型: {args.model}")
    with open(args.model, "rb") as f:
        model = pickle.load(f)
    
    print(f"  - 模型类型: {type(model).__name__}")
    print(f"  - 隐因子数量: {model.n_factors}")
    print(f"  - 训练用户数: {len(model.user_map)}")
    print(f"  - 训练物品数: {len(model.item_map)}")
    print(f"  - 全局平均评分: {model.global_mean:.3f}")

    # 2. 测试预测
    print(f"\n[2/3] 测试预测功能")
    
    # 选择几个训练集中的用户/电影进行测试
    test_cases = [
        (list(model.user_map.keys())[0], list(model.item_map.keys())[0]),
        (list(model.user_map.keys())[10], list(model.item_map.keys())[100]),
        (list(model.user_map.keys())[50], list(model.item_map.keys())[500]),
    ]
    
    for user_id, movie_id in test_cases:
        pred = model.predict(user_id, movie_id)
        print(f"  - 用户 {user_id}, 电影 {movie_id}: 预测评分 = {pred:.2f}")
    
    # 3. 测试 Top-N 推荐（为某个用户推荐评分最高的 N 部电影）
    print(f"\n[3/3] 测试 Top-10 推荐")
    
    test_user_id = list(model.user_map.keys())[0]
    print(f"  - 为用户 {test_user_id} 推荐 Top-10 电影...")
    
    # 计算该用户对所有电影的预测评分
    movie_ids = list(model.item_map.keys())
    predictions = [(movie_id, model.predict(test_user_id, movie_id)) for movie_id in movie_ids]
    
    # 按预测评分降序排序，取 Top-10
    top_10 = sorted(predictions, key=lambda x: x[1], reverse=True)[:10]
    
    for rank, (movie_id, pred_rating) in enumerate(top_10, start=1):
        print(f"    {rank}. 电影 {movie_id}: 预测评分 {pred_rating:.2f}")
    
    print("\n" + "=" * 60)
    print("测试完成！模型加载和预测功能正常")
    print("=" * 60)


if __name__ == "__main__":
    main()

