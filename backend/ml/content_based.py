"""
基于内容的推荐模型
利用电影特征（类型、年份等）进行推荐

使用方法：
    python -m ml.content_based --train ../data/output1/ratings_train.csv \
                                --test ../data/output1/ratings_test.csv \
                                --movies ../data/ml-latest-small/movies.csv \
                                --output ../data/output4/
"""

import argparse
import os
import pickle
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer


class ContentBasedRecommender:
    """
    基于内容的推荐模型
    
    策略：
    1. 为每部电影构建特征向量（类型、年份等）
    2. 计算用户的偏好向量（基于其评分过的电影）
    3. 预测 = 用户偏好 · 电影特征
    """
    
    def __init__(self):
        self.user_profiles = {}  # 用户偏好向量
        self.movie_features = {}  # 电影特征向量
        self.global_mean = 0
        self.user_mean = {}
        self.movie_mean = {}
        
    def _extract_movie_features(self, movies_df):
        """
        从电影数据中提取特征
        
        Args:
            movies_df: 包含 movieId, title, genres 的DataFrame
            
        Returns:
            dict: {movieId: feature_vector}
        """
        print("  提取电影特征...")
        
        # 1. 处理类型（genres）
        # 格式：'Action|Adventure|Sci-Fi'
        movies_df['genres_list'] = movies_df['genres'].str.split('|')
        
        # 使用 MultiLabelBinarizer 进行 one-hot 编码
        mlb = MultiLabelBinarizer()
        genres_encoded = mlb.fit_transform(movies_df['genres_list'])
        
        print(f"    - 类型数量: {len(mlb.classes_)}")
        print(f"    - 类型列表: {mlb.classes_[:10]}...")  # 显示前10个
        
        # 2. 提取年份（从标题中）
        # 格式：'Toy Story (1995)'
        movies_df['year'] = movies_df['title'].str.extract(r'\((\d{4})\)')
        movies_df['year'] = pd.to_numeric(movies_df['year'], errors='coerce')
        movies_df['year'] = movies_df['year'].fillna(movies_df['year'].median())
        
        # 归一化年份（1995-2020 → 0-1）
        year_min = movies_df['year'].min()
        year_max = movies_df['year'].max()
        movies_df['year_normalized'] = (movies_df['year'] - year_min) / (year_max - year_min)
        
        # 3. 构建特征向量
        # [genres_encoded, year_normalized]
        movie_features = {}
        for idx, row in movies_df.iterrows():
            movie_id = row['movieId']
            genre_vec = genres_encoded[idx]
            year_feat = np.array([row['year_normalized']])
            
            # 拼接特征
            feature_vec = np.concatenate([genre_vec, year_feat])
            movie_features[movie_id] = feature_vec
        
        print(f"    - 特征维度: {len(feature_vec)}")
        
        self.movie_features = movie_features
        return movie_features
    
    def fit(self, train_df, movies_df):
        """
        训练基于内容的推荐模型
        
        Args:
            train_df: 训练集 (userId, movieId, rating)
            movies_df: 电影数据 (movieId, title, genres)
        """
        print("\n训练基于内容的推荐模型...")
        
        # 1. 提取电影特征
        self._extract_movie_features(movies_df)
        
        # 2. 计算全局均值
        self.global_mean = train_df['rating'].mean()
        
        # 3. 计算用户/电影平均评分（作为偏差项）
        self.user_mean = train_df.groupby('userId')['rating'].mean().to_dict()
        self.movie_mean = train_df.groupby('movieId')['rating'].mean().to_dict()
        
        # 4. 为每个用户构建偏好向量
        print("  构建用户偏好向量...")
        
        for user_id in train_df['userId'].unique():
            user_ratings = train_df[train_df['userId'] == user_id]
            
            # 收集该用户评分过的电影的特征
            weighted_features = []
            weights = []
            
            for _, row in user_ratings.iterrows():
                movie_id = row['movieId']
                rating = row['rating']
                
                if movie_id in self.movie_features:
                    # 使用评分作为权重（高评分的电影权重更大）
                    # 归一化：(rating - global_mean)
                    weight = rating - self.global_mean
                    
                    weighted_features.append(self.movie_features[movie_id] * weight)
                    weights.append(abs(weight))
            
            if weighted_features:
                # 用户偏好 = 加权平均的电影特征
                user_profile = np.sum(weighted_features, axis=0)
                if np.sum(weights) > 0:
                    user_profile = user_profile / np.sum(weights)
                
                self.user_profiles[user_id] = user_profile
        
        print(f"  - 用户数: {len(self.user_profiles)}")
        print(f"  - 电影数: {len(self.movie_features)}")
    
    def predict(self, user_id, movie_id):
        """
        预测用户对电影的评分
        
        Args:
            user_id: 用户ID
            movie_id: 电影ID
            
        Returns:
            预测评分 (0.5-5.0)
        """
        # 情况1：用户和电影都有数据
        if user_id in self.user_profiles and movie_id in self.movie_features:
            user_vec = self.user_profiles[user_id]
            movie_vec = self.movie_features[movie_id]
            
            # 相似度（余弦相似度的简化版：点积）
            similarity = np.dot(user_vec, movie_vec)
            
            # 预测 = 全局均值 + 用户偏差 + 电影偏差 + 相似度
            user_bias = self.user_mean.get(user_id, 0) - self.global_mean
            movie_bias = self.movie_mean.get(movie_id, 0) - self.global_mean
            
            pred = self.global_mean + user_bias * 0.3 + movie_bias * 0.3 + similarity * 0.4
        
        # 情况2：只有电影数据（新用户）
        elif movie_id in self.movie_mean:
            pred = self.movie_mean[movie_id]
        
        # 情况3：只有用户数据（新电影）
        elif user_id in self.user_mean:
            pred = self.user_mean[user_id]
        
        # 情况4：完全冷启动
        else:
            pred = self.global_mean
        
        # 裁剪到评分范围
        return np.clip(pred, 0.5, 5.0)
    
    def evaluate(self, test_df):
        """
        在测试集上评估模型
        
        Args:
            test_df: 测试集
            
        Returns:
            dict: 评估指标 (RMSE, MAE)
        """
        predictions = []
        true_ratings = []
        
        for _, row in test_df.iterrows():
            pred = self.predict(row['userId'], row['movieId'])
            predictions.append(pred)
            true_ratings.append(row['rating'])
        
        predictions = np.array(predictions)
        true_ratings = np.array(true_ratings)
        
        errors = true_ratings - predictions
        rmse = np.sqrt(np.mean(errors ** 2))
        mae = np.mean(np.abs(errors))
        
        return {
            'rmse': rmse,
            'mae': mae,
            'predictions': predictions,
            'true_ratings': true_ratings
        }


def main():
    parser = argparse.ArgumentParser(description="基于内容的推荐模型")
    parser.add_argument("--train", default="../data/output1/ratings_train.csv", help="训练集路径")
    parser.add_argument("--test", default="../data/output1/ratings_test.csv", help="测试集路径")
    parser.add_argument("--movies", default="../data/ml-latest-small/movies.csv", help="电影数据路径")
    parser.add_argument("--output", default="../data/output4/", help="输出目录")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("基于内容的推荐模型")
    print("=" * 70)
    
    # 1. 加载数据
    print("\n[1/4] 加载数据")
    train_df = pd.read_csv(args.train)
    test_df = pd.read_csv(args.test)
    movies_df = pd.read_csv(args.movies)
    
    print(f"  训练集: {len(train_df)} 条")
    print(f"  测试集: {len(test_df)} 条")
    print(f"  电影数: {len(movies_df)} 部")
    
    # 2. 训练模型
    print("\n[2/4] 训练模型")
    model = ContentBasedRecommender()
    model.fit(train_df, movies_df)
    
    # 3. 评估模型
    print("\n[3/4] 评估模型")
    print("  测试集评估:")
    test_metrics = model.evaluate(test_df)
    print(f"    - RMSE: {test_metrics['rmse']:.4f}")
    print(f"    - MAE:  {test_metrics['mae']:.4f}")
    
    print("  训练集评估:")
    train_metrics = model.evaluate(train_df.sample(min(5000, len(train_df)), random_state=42))
    print(f"    - RMSE: {train_metrics['rmse']:.4f}")
    print(f"    - MAE:  {train_metrics['mae']:.4f}")
    
    # 4. 保存模型
    print("\n[4/4] 保存模型")
    os.makedirs(args.output, exist_ok=True)
    
    model_path = os.path.join(args.output, "content_model.pkl")
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"  模型已保存: {model_path}")
    
    # 保存评估报告
    report_path = os.path.join(args.output, "content_evaluation.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("基于内容的推荐模型评估报告\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"训练时间: {datetime.now().isoformat()}\n\n")
        
        f.write("测试集性能:\n")
        f.write(f"  RMSE: {test_metrics['rmse']:.4f}\n")
        f.write(f"  MAE:  {test_metrics['mae']:.4f}\n\n")
        
        f.write("训练集性能:\n")
        f.write(f"  RMSE: {train_metrics['rmse']:.4f}\n")
        f.write(f"  MAE:  {train_metrics['mae']:.4f}\n")
    
    print(f"  评估报告已保存: {report_path}")
    
    print("\n" + "=" * 70)
    print("基于内容的模型训练完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()






