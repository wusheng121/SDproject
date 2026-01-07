"""
步骤四集成测试脚本

测试机器学习推荐系统与Flask应用的集成
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import User, Rating
from services.recommendation_service import get_recommendations_for_user

# 导入ML模型类（用于 pickle 反序列化）
try:
    from ml.hybrid import HybridRecommender
    from ml.train_mf import MatrixFactorizationALS
    from ml.content_based import ContentBasedRecommender
except ImportError:
    pass  # 如果无法导入，测试会使用基础推荐策略

def test_ml_integration():
    """测试ML推荐系统集成"""
    print("=" * 70)
    print("步骤四：ML推荐系统集成测试")
    print("=" * 70)
    
    # 创建应用
    app = create_app()
    
    with app.app_context():
        # 查找一个有足够评分的用户（触发策略D）
        user_with_ratings = db.session.query(User).join(Rating).group_by(User.id).having(
            db.func.count(Rating.id) >= 10
        ).first()
        
        if not user_with_ratings:
            print("\n警告: 数据库中没有符合条件的用户（评分>=10）")
            print("   创建测试用户...")
            # 可以创建测试数据或使用现有用户
            users = User.query.limit(3).all()
            if not users:
                print("   数据库中没有用户，请先运行 seed_demo.py")
                return
            user_with_ratings = users[0]
        
        print(f"\n测试用户：")
        print(f"  ID: {user_with_ratings.id}")
        print(f"  用户名: {user_with_ratings.username}")
        print(f"  邮箱: {user_with_ratings.email}")
        
        # 获取用户评分数
        rating_count = Rating.query.filter_by(user_id=user_with_ratings.id).count()
        print(f"  评分数: {rating_count}")
        
        # 获取用户偏好
        preferred_genres = user_with_ratings.get_preferred_genres_list()
        print(f"  偏好类型: {preferred_genres if preferred_genres else '未设置'}")
        
        # 测试不同策略
        print("\n" + "=" * 70)
        print("测试推荐策略")
        print("=" * 70)
        
        # 根据评分数判断使用哪个策略
        if rating_count >= 10:
            print(f"\n[+] 符合策略D条件（评分数={rating_count}>=10）")
            print("  将使用机器学习推荐系统（混合模型）")
        elif rating_count > 0:
            print(f"\n[+] 符合策略C条件（0<评分数={rating_count}<10）")
            print("  将使用轻量混合策略")
        elif preferred_genres:
            print(f"\n[+] 符合策略B条件（有偏好但无评分）")
            print("  将使用基于内容推荐")
        else:
            print(f"\n[+] 符合策略A条件（无偏好无评分）")
            print("  将使用全局热门推荐")
        
        # 获取推荐
        print("\n获取推荐中...")
        try:
            recommendations = get_recommendations_for_user(user_with_ratings, limit=10)
            
            print(f"\n[+] 成功获取 {len(recommendations)} 条推荐")
            print("\n推荐结果：")
            print("=" * 70)
            
            for idx, rec in enumerate(recommendations, 1):
                print(f"\n{idx}. {rec['title']} ({rec.get('release_year', 'N/A')})")
                print(f"   ID: {rec['id']}")
                print(f"   平均评分: {rec['rating_avg']} ({rec['rating_count']} 人评分)")
                
                # 如果有ML预测评分，显示它
                if 'ml_predicted_rating' in rec:
                    print(f"   ML预测评分: {rec['ml_predicted_rating']}")
                
                if rec.get('poster_url'):
                    print(f"   海报: {rec['poster_url']}")
            
            print("\n" + "=" * 70)
            print("[+] 测试完成")
            print("=" * 70)
            
            # 统计信息
            ml_recs = [r for r in recommendations if 'ml_predicted_rating' in r]
            if ml_recs:
                print(f"\n[统计] ML推荐统计：")
                print(f"   使用ML模型的推荐: {len(ml_recs)}/{len(recommendations)}")
                print(f"   平均预测评分: {sum(r['ml_predicted_rating'] for r in ml_recs) / len(ml_recs):.2f}")
            else:
                print(f"\n[统计] 使用基础推荐策略（ML模型未使用）")
            
        except Exception as e:
            print(f"\n[-] 推荐失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_ml_integration()

