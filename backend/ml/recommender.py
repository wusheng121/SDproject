"""
步骤三：模型集成模块
功能：
1. 加载训练好的混合推荐模型
2. 提供推荐接口：get_recommendations(user_id, n=10)
3. 支持多种推荐场景（个性化推荐、冷启动、相似电影等）

使用方法：
    from ml.recommender import Recommender
    
    recommender = Recommender(
        hybrid_model_path='../data/output5/hybrid_model.pkl',
        movies_path='../data/ml-latest-small/movies.csv'
    )
    
    # 为用户推荐电影
    recommendations = recommender.get_recommendations(user_id=1, n=10)
"""

import pickle
from datetime import datetime
from typing import List, Dict, Tuple, Optional

import numpy as np
import pandas as pd

# 导入模型类（用于 pickle 反序列化）
from ml.hybrid import HybridRecommender
from ml.train_mf import MatrixFactorizationALS
from ml.content_based import ContentBasedRecommender


class Recommender:
    """
    推荐系统集成模块
    
    功能：
    - 个性化推荐：基于用户历史评分
    - 冷启动推荐：新用户推荐热门电影
    - 相似电影推荐：基于电影特征
    - 多样性推荐：避免推荐相似类型的电影
    """
    
    def __init__(self, 
                 hybrid_model_path: str = '../data/output5/hybrid_model.pkl',
                 movies_path: str = '../data/ml-latest-small/movies.csv',
                 ratings_path: str = '../data/output1/ratings_train.csv'):
        """
        初始化推荐系统
        
        Args:
            hybrid_model_path: 混合模型路径
            movies_path: 电影数据路径
            ratings_path: 评分数据路径（用于计算热门度）
        """
        print("初始化推荐系统...")
        
        # 1. 加载混合模型
        print(f"  加载混合模型: {hybrid_model_path}")
        with open(hybrid_model_path, 'rb') as f:
            self.hybrid_model = pickle.load(f)
        
        # 2. 加载电影数据
        print(f"  加载电影数据: {movies_path}")
        self.movies_df = pd.read_csv(movies_path)
        self.movie_id_to_title = dict(zip(
            self.movies_df['movieId'], 
            self.movies_df['title']
        ))
        
        # 3. 加载评分数据（用于统计）
        print(f"  加载评分数据: {ratings_path}")
        ratings_df = pd.read_csv(ratings_path)
        
        # 计算电影统计信息
        self._compute_movie_stats(ratings_df)
        
        print("推荐系统初始化完成！")
    
    def _compute_movie_stats(self, ratings_df: pd.DataFrame):
        """
        计算电影统计信息（用于热门推荐和排序）
        
        Args:
            ratings_df: 评分数据
        """
        movie_stats = ratings_df.groupby('movieId').agg({
            'rating': ['mean', 'count']
        }).reset_index()
        
        movie_stats.columns = ['movieId', 'avg_rating', 'rating_count']
        
        # 计算热门度分数（考虑评分和评分人数）
        # 使用贝叶斯平均：(R*v + C*m) / (v + m)
        # R: 平均评分, v: 评分数, C: 全局平均评分, m: 最小评分数阈值
        C = ratings_df['rating'].mean()
        m = 10  # 最少需要10个评分才算热门
        
        movie_stats['popularity_score'] = (
            movie_stats['avg_rating'] * movie_stats['rating_count'] + C * m
        ) / (movie_stats['rating_count'] + m)
        
        self.movie_stats = movie_stats.set_index('movieId').to_dict('index')
    
    def get_recommendations(self, 
                           user_id: int, 
                           n: int = 10,
                           exclude_rated: bool = True,
                           diversity: bool = False) -> List[Dict]:
        """
        为用户生成个性化推荐
        
        Args:
            user_id: 用户ID
            n: 推荐数量
            exclude_rated: 是否排除用户已评分的电影
            diversity: 是否启用多样性推荐（避免同类型电影扎堆）
            
        Returns:
            推荐列表，每个推荐包含：
            {
                'movie_id': 电影ID,
                'title': 电影标题,
                'predicted_rating': 预测评分,
                'genres': 电影类型,
                'avg_rating': 平均评分,
                'rating_count': 评分人数
            }
        """
        # 1. 获取用户已评分的电影
        als_model = self.hybrid_model.als_model
        rated_movies = set()
        
        if exclude_rated and user_id in als_model.user_map:
            # 从训练集中找到用户评分过的电影
            # 注意：这里简化处理，实际应该从数据库获取
            pass
        
        # 2. 获取候选电影（所有电影或未评分的电影）
        candidate_movies = [
            mid for mid in self.movies_df['movieId']
            if mid not in rated_movies
        ]
        
        # 3. 批量预测评分
        predictions = []
        for movie_id in candidate_movies:
            pred_rating = self.hybrid_model.predict(user_id, movie_id)
            predictions.append((movie_id, pred_rating))
        
        # 4. 排序并选择 Top-N
        predictions.sort(key=lambda x: x[1], reverse=True)
        top_n = predictions[:n * 2] if diversity else predictions[:n]  # 如果需要多样性，先取2倍
        
        # 5. 多样性处理（可选）
        if diversity:
            top_n = self._diversify_recommendations(top_n, n)
        else:
            top_n = top_n[:n]
        
        # 6. 构建推荐结果
        recommendations = []
        for movie_id, pred_rating in top_n:
            movie_info = self.movies_df[self.movies_df['movieId'] == movie_id].iloc[0]
            stats = self.movie_stats.get(movie_id, {})
            
            recommendations.append({
                'movie_id': int(movie_id),
                'title': movie_info['title'],
                'predicted_rating': float(pred_rating),
                'genres': movie_info['genres'],
                'avg_rating': stats.get('avg_rating', 0),
                'rating_count': stats.get('rating_count', 0),
                'popularity_score': stats.get('popularity_score', 0)
            })
        
        return recommendations
    
    def _diversify_recommendations(self, 
                                  predictions: List[Tuple[int, float]], 
                                  n: int) -> List[Tuple[int, float]]:
        """
        多样性推荐：避免推荐太多相同类型的电影
        
        Args:
            predictions: 预测结果列表 [(movie_id, rating), ...]
            n: 目标推荐数量
            
        Returns:
            多样化的推荐列表
        """
        selected = []
        genre_counts = {}
        
        for movie_id, rating in predictions:
            if len(selected) >= n:
                break
            
            # 获取电影类型
            movie_info = self.movies_df[self.movies_df['movieId'] == movie_id].iloc[0]
            genres = movie_info['genres'].split('|')
            
            # 检查类型多样性
            # 如果某个类型已经推荐了2部以上，降低优先级
            genre_penalty = sum(genre_counts.get(g, 0) for g in genres)
            
            if genre_penalty < 3:  # 阈值：同一类型不超过3部
                selected.append((movie_id, rating))
                for genre in genres:
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        return selected
    
    def get_popular_recommendations(self, n: int = 10) -> List[Dict]:
        """
        获取热门电影推荐（冷启动场景）
        
        Args:
            n: 推荐数量
            
        Returns:
            热门电影列表
        """
        # 按热门度分数排序
        popular_movies = sorted(
            self.movie_stats.items(),
            key=lambda x: x[1]['popularity_score'],
            reverse=True
        )[:n]
        
        recommendations = []
        for movie_id, stats in popular_movies:
            movie_info = self.movies_df[self.movies_df['movieId'] == movie_id].iloc[0]
            
            recommendations.append({
                'movie_id': int(movie_id),
                'title': movie_info['title'],
                'predicted_rating': stats['avg_rating'],
                'genres': movie_info['genres'],
                'avg_rating': stats['avg_rating'],
                'rating_count': stats['rating_count'],
                'popularity_score': stats['popularity_score']
            })
        
        return recommendations
    
    def get_similar_movies(self, movie_id: int, n: int = 10) -> List[Dict]:
        """
        获取相似电影推荐（基于内容）
        
        Args:
            movie_id: 电影ID
            n: 推荐数量
            
        Returns:
            相似电影列表
        """
        content_model = self.hybrid_model.content_model
        
        # 检查电影是否存在
        if movie_id not in content_model.movie_features:
            return []
        
        # 获取目标电影的特征向量
        target_features = content_model.movie_features[movie_id]
        
        # 计算与所有电影的相似度
        similarities = []
        for mid, features in content_model.movie_features.items():
            if mid == movie_id:
                continue
            
            # 余弦相似度
            similarity = np.dot(target_features, features) / (
                np.linalg.norm(target_features) * np.linalg.norm(features) + 1e-10
            )
            similarities.append((mid, similarity))
        
        # 排序并选择 Top-N
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_n = similarities[:n]
        
        # 构建推荐结果
        recommendations = []
        for mid, similarity in top_n:
            movie_info = self.movies_df[self.movies_df['movieId'] == mid].iloc[0]
            stats = self.movie_stats.get(mid, {})
            
            recommendations.append({
                'movie_id': int(mid),
                'title': movie_info['title'],
                'similarity': float(similarity),
                'genres': movie_info['genres'],
                'avg_rating': stats.get('avg_rating', 0),
                'rating_count': stats.get('rating_count', 0)
            })
        
        return recommendations
    
    def get_model_info(self) -> Dict:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        als_model = self.hybrid_model.als_model
        content_model = self.hybrid_model.content_model
        
        return {
            'model_type': 'Hybrid (ALS + Content-Based)',
            'alpha': self.hybrid_model.alpha,
            'als_weight': f"{self.hybrid_model.alpha * 100:.0f}%",
            'content_weight': f"{(1 - self.hybrid_model.alpha) * 100:.0f}%",
            'als_users': len(als_model.user_map),
            'als_movies': len(als_model.item_map),
            'content_movies': len(content_model.movie_features),
            'global_mean_rating': float(als_model.global_mean)
        }


def main():
    """测试推荐系统"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试推荐系统")
    parser.add_argument("--model", default="../data/output5/hybrid_model.pkl", help="混合模型路径")
    parser.add_argument("--movies", default="../data/ml-latest-small/movies.csv", help="电影数据路径")
    parser.add_argument("--ratings", default="../data/output1/ratings_train.csv", help="评分数据路径")
    parser.add_argument("--user-id", type=int, default=1, help="测试用户ID")
    parser.add_argument("--movie-id", type=int, default=1, help="测试电影ID")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("推荐系统测试")
    print("=" * 70)
    
    # 1. 初始化推荐系统
    recommender = Recommender(
        hybrid_model_path=args.model,
        movies_path=args.movies,
        ratings_path=args.ratings
    )
    
    # 2. 显示模型信息
    print("\n" + "=" * 70)
    print("模型信息")
    print("=" * 70)
    info = recommender.get_model_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # 3. 测试个性化推荐
    print("\n" + "=" * 70)
    print(f"为用户 {args.user_id} 生成个性化推荐 (Top 10)")
    print("=" * 70)
    
    recommendations = recommender.get_recommendations(args.user_id, n=10)
    
    for idx, rec in enumerate(recommendations, 1):
        print(f"\n{idx}. {rec['title']}")
        print(f"   预测评分: {rec['predicted_rating']:.2f}")
        print(f"   类型: {rec['genres']}")
        print(f"   平均评分: {rec['avg_rating']:.2f} ({rec['rating_count']} 人评分)")
    
    # 4. 测试热门推荐
    print("\n" + "=" * 70)
    print("热门电影推荐 (Top 10)")
    print("=" * 70)
    
    popular = recommender.get_popular_recommendations(n=10)
    
    for idx, rec in enumerate(popular, 1):
        print(f"\n{idx}. {rec['title']}")
        print(f"   平均评分: {rec['avg_rating']:.2f}")
        print(f"   评分人数: {rec['rating_count']}")
        print(f"   类型: {rec['genres']}")
    
    # 5. 测试相似电影推荐
    print("\n" + "=" * 70)
    movie_title = recommender.movie_id_to_title.get(args.movie_id, "未知电影")
    print(f"与 [{movie_title}] 相似的电影 (Top 10)")
    print("=" * 70)
    
    similar = recommender.get_similar_movies(args.movie_id, n=10)
    
    for idx, rec in enumerate(similar, 1):
        print(f"\n{idx}. {rec['title']}")
        print(f"   相似度: {rec['similarity']:.3f}")
        print(f"   类型: {rec['genres']}")
        print(f"   平均评分: {rec['avg_rating']:.2f}")
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()

