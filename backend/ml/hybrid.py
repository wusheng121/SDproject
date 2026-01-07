"""
混合推荐系统：ALS协同过滤 + 基于内容推荐
采用加权融合策略

使用方法：
    python -m ml.hybrid --train ../data/output1/ratings_train.csv \
                        --test ../data/output1/ratings_test.csv \
                        --als-model ../data/output2_best/als_model.pkl \
                        --content-model ../data/output4/content_model.pkl \
                        --output ../data/output5/
"""

import argparse
import os
import pickle
from datetime import datetime

import numpy as np
import pandas as pd

# 导入 ALS 模型类（用于 pickle 反序列化）
from ml.train_mf import MatrixFactorizationALS
from ml.content_based import ContentBasedRecommender


class HybridRecommender:
    """
    混合推荐系统
    
    策略：
    - 融合ALS协同过滤和基于内容推荐的预测
    - 预测 = α · 协同过滤预测 + (1-α) · 内容推荐预测
    """
    
    def __init__(self, als_model, content_model, alpha=0.7):
        """
        Args:
            als_model: 训练好的ALS模型
            content_model: 训练好的基于内容的模型
            alpha: 协同过滤的权重（0-1），默认0.7
        """
        self.als_model = als_model
        self.content_model = content_model
        self.alpha = alpha
        
    def predict(self, user_id, movie_id):
        """
        预测用户对电影的评分
        
        Args:
            user_id: 用户ID
            movie_id: 电影ID
            
        Returns:
            预测评分 (0.5-5.0)
        """
        # 获取两个模型的预测
        als_pred = self.als_model.predict(user_id, movie_id)
        content_pred = self.content_model.predict(user_id, movie_id)
        
        # 加权融合
        hybrid_pred = self.alpha * als_pred + (1 - self.alpha) * content_pred
        
        return np.clip(hybrid_pred, 0.5, 5.0)
    
    def evaluate(self, test_df):
        """
        在测试集上评估混合模型
        
        Args:
            test_df: 测试集
            
        Returns:
            dict: 评估指标
        """
        predictions = []
        als_predictions = []
        content_predictions = []
        true_ratings = []
        
        for _, row in test_df.iterrows():
            # 混合预测
            pred = self.predict(row['userId'], row['movieId'])
            predictions.append(pred)
            
            # 单独记录两个模型的预测（用于分析）
            als_pred = self.als_model.predict(row['userId'], row['movieId'])
            content_pred = self.content_model.predict(row['userId'], row['movieId'])
            als_predictions.append(als_pred)
            content_predictions.append(content_pred)
            
            true_ratings.append(row['rating'])
        
        predictions = np.array(predictions)
        als_predictions = np.array(als_predictions)
        content_predictions = np.array(content_predictions)
        true_ratings = np.array(true_ratings)
        
        # 计算RMSE和MAE
        errors = true_ratings - predictions
        rmse = np.sqrt(np.mean(errors ** 2))
        mae = np.mean(np.abs(errors))
        
        # 分别计算两个模型的RMSE（用于对比）
        als_rmse = np.sqrt(np.mean((true_ratings - als_predictions) ** 2))
        content_rmse = np.sqrt(np.mean((true_ratings - content_predictions) ** 2))
        
        return {
            'hybrid_rmse': rmse,
            'hybrid_mae': mae,
            'als_rmse': als_rmse,
            'content_rmse': content_rmse,
            'predictions': predictions,
            'true_ratings': true_ratings
        }
    
    def tune_alpha(self, validation_df, alpha_range=None):
        """
        在验证集上调优融合权重 alpha
        
        Args:
            validation_df: 验证集（通常是测试集）
            alpha_range: alpha的候选值列表，默认 [0.5, 0.6, 0.7, 0.8, 0.9]
            
        Returns:
            best_alpha, best_rmse, results
        """
        if alpha_range is None:
            alpha_range = np.arange(0, 0.95, 0.05)
        
        print(f"\n调优融合权重 alpha (候选值: {len(alpha_range)} 个)")
        print(f"说明：alpha=0.5表示50% ALS + 50% 内容，alpha=1.0表示100% ALS\n")
        
        best_alpha = self.alpha
        best_rmse = float('inf')
        best_mae = float('inf')
        
        results = []
        
        for alpha in alpha_range:
            self.alpha = alpha
            metrics = self.evaluate(validation_df)
            rmse = metrics['hybrid_rmse']
            mae = metrics['hybrid_mae']
            
            results.append((alpha, rmse, mae))
            
            if rmse < best_rmse:
                best_rmse = rmse
                best_mae = mae
                best_alpha = alpha
            
            print(f"  alpha={alpha:.2f}: RMSE={rmse:.4f}, MAE={mae:.4f}")
        
        self.alpha = best_alpha
        print(f"\n✓ 最佳 alpha: {best_alpha:.2f} ({best_alpha*100:.0f}% ALS + {(1-best_alpha)*100:.0f}% 内容)")
        print(f"  最佳 RMSE: {best_rmse:.4f}")
        print(f"  最佳 MAE:  {best_mae:.4f}")
        
        return best_alpha, best_rmse, results


def main():
    parser = argparse.ArgumentParser(description="混合推荐系统：ALS + 基于内容")
    parser.add_argument("--train", default="../data/output1/ratings_train.csv", help="训练集路径")
    parser.add_argument("--test", default="../data/output1/ratings_test.csv", help="测试集路径")
    parser.add_argument("--als-model", default="../data/output2_best/als_model.pkl", help="ALS模型路径")
    parser.add_argument("--content-model", default="../data/output4/content_model.pkl", help="内容模型路径")
    parser.add_argument("--output", default="../data/output5/", help="输出目录")
    parser.add_argument("--alpha", type=float, default=0.7, help="协同过滤权重（默认0.7）")
    parser.add_argument("--tune-alpha", action="store_true", help="是否自动调优alpha")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("混合推荐系统：ALS协同过滤 + 基于内容推荐")
    print("=" * 70)
    
    # 1. 加载数据和模型
    print("\n[1/4] 加载数据和模型")
    train_df = pd.read_csv(args.train)
    test_df = pd.read_csv(args.test)
    
    print(f"  训练集: {len(train_df)} 条")
    print(f"  测试集: {len(test_df)} 条")
    
    print(f"  加载ALS模型: {args.als_model}")
    with open(args.als_model, 'rb') as f:
        als_model = pickle.load(f)
    
    print(f"  加载内容模型: {args.content_model}")
    with open(args.content_model, 'rb') as f:
        content_model = pickle.load(f)
    
    # 2. 创建混合模型
    print(f"\n[2/4] 创建混合模型 (初始 alpha={args.alpha})")
    hybrid_model = HybridRecommender(als_model, content_model, alpha=args.alpha)
    
    # 3. 调优alpha（可选）
    if args.tune_alpha:
        print("\n[3/4] 调优融合权重（在测试集上）")
        best_alpha, best_rmse, tuning_results = hybrid_model.tune_alpha(test_df)
        print(f"  最优alpha: {best_alpha:.2f}")
    else:
        print(f"\n[3/4] 使用固定 alpha={args.alpha}")
    
    # 4. 评估混合模型
    print("\n[4/4] 评估混合模型")
    
    # 测试集评估
    print("\n  测试集评估:")
    test_metrics = hybrid_model.evaluate(test_df)
    
    print(f"    混合模型:")
    print(f"      - RMSE: {test_metrics['hybrid_rmse']:.4f}")
    print(f"      - MAE:  {test_metrics['hybrid_mae']:.4f}")
    
    print(f"\n    单独模型对比:")
    print(f"      ALS模型 RMSE:  {test_metrics['als_rmse']:.4f}")
    print(f"      内容模型 RMSE: {test_metrics['content_rmse']:.4f}")
    
    improvement_als = (test_metrics['als_rmse'] - test_metrics['hybrid_rmse']) / test_metrics['als_rmse'] * 100
    improvement_content = (test_metrics['content_rmse'] - test_metrics['hybrid_rmse']) / test_metrics['content_rmse'] * 100
    
    print(f"\n    提升效果:")
    print(f"      相比ALS: {improvement_als:+.1f}%")
    print(f"      相比内容: {improvement_content:+.1f}%")
    
    # 训练集评估（检测过拟合）
    print("\n  训练集评估（过拟合检测）:")
    train_sample = train_df.sample(min(5000, len(train_df)), random_state=42)
    train_metrics = hybrid_model.evaluate(train_sample)
    print(f"    - RMSE: {train_metrics['hybrid_rmse']:.4f}")
    print(f"    - MAE:  {train_metrics['hybrid_mae']:.4f}")
    
    overfitting = (test_metrics['hybrid_rmse'] - train_metrics['hybrid_rmse']) / train_metrics['hybrid_rmse'] * 100
    print(f"    - 过拟合程度: {overfitting:.1f}%")
    
    # 5. 保存结果
    print("\n[5/5] 保存结果")
    os.makedirs(args.output, exist_ok=True)
    
    # 保存混合模型
    model_path = os.path.join(args.output, "hybrid_model.pkl")
    with open(model_path, 'wb') as f:
        pickle.dump(hybrid_model, f)
    print(f"  混合模型已保存: {model_path}")
    
    # 保存评估报告
    report_path = os.path.join(args.output, "hybrid_evaluation.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("混合推荐系统评估报告\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"创建时间: {datetime.now().isoformat()}\n")
        f.write(f"融合策略: 加权平均\n")
        f.write(f"融合权重: α={hybrid_model.alpha:.2f} (ALS), {1-hybrid_model.alpha:.2f} (内容)\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("测试集性能\n")
        f.write("-" * 70 + "\n")
        f.write(f"混合模型:\n")
        f.write(f"  RMSE: {test_metrics['hybrid_rmse']:.4f}\n")
        f.write(f"  MAE:  {test_metrics['hybrid_mae']:.4f}\n\n")
        
        f.write(f"单独模型对比:\n")
        f.write(f"  ALS模型 RMSE:  {test_metrics['als_rmse']:.4f}\n")
        f.write(f"  内容模型 RMSE: {test_metrics['content_rmse']:.4f}\n\n")
        
        f.write(f"提升效果:\n")
        f.write(f"  相比ALS: {improvement_als:+.2f}%\n")
        f.write(f"  相比内容: {improvement_content:+.2f}%\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("训练集性能（过拟合检测）\n")
        f.write("-" * 70 + "\n")
        f.write(f"  RMSE: {train_metrics['hybrid_rmse']:.4f}\n")
        f.write(f"  MAE:  {train_metrics['hybrid_mae']:.4f}\n")
        f.write(f"  过拟合程度: {overfitting:.1f}%\n\n")
        
        # 如果进行了alpha调优，保存调优结果
        if args.tune_alpha:
            f.write("-" * 70 + "\n")
            f.write("Alpha调优结果（在测试集上）\n")
            f.write("-" * 70 + "\n")
            for alpha, rmse, mae in tuning_results:
                f.write(f"  alpha={alpha:.2f}: RMSE={rmse:.4f}, MAE={mae:.4f}\n")
            f.write(f"\n最优alpha: {best_alpha:.2f}\n")
    
    print(f"  评估报告已保存: {report_path}")
    
    print("\n" + "=" * 70)
    print("混合推荐系统构建完成！")
    print("=" * 70)
    print(f"\n🎉 最终测试集 RMSE: {test_metrics['hybrid_rmse']:.4f}")
    
    # 评级
    if test_metrics['hybrid_rmse'] < 0.85:
        print("   评级: ★★★★★ 优秀！")
    elif test_metrics['hybrid_rmse'] < 0.95:
        print("   评级: ★★★★☆ 良好！")
    elif test_metrics['hybrid_rmse'] < 1.05:
        print("   评级: ★★★☆☆ 合格")
    else:
        print("   评级: ★★☆☆☆ 需改进")


if __name__ == "__main__":
    main()

