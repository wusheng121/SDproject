from sqlalchemy import func

from extensions import db
from models import Favorite, Genre, Movie, MovieGenre, Rating, User

# 步骤四：导入机器学习推荐系统
try:
    from ml.recommender import Recommender
    
    # 全局推荐系统实例（应用启动时初始化）
    _ml_recommender = None
    
    def init_ml_recommender():
        """初始化机器学习推荐系统（在应用启动时调用一次）"""
        global _ml_recommender
        if _ml_recommender is None:
            try:
                import os
                # 获取项目根目录
                # __file__ 是 backend/services/recommendation_service.py
                # dirname(__file__) -> backend/services/
                # dirname(dirname(__file__)) -> backend/
                # dirname(dirname(dirname(__file__))) -> 项目根目录
                current_file = os.path.abspath(__file__)
                services_dir = os.path.dirname(current_file)  # backend/services/
                backend_dir = os.path.dirname(services_dir)    # backend/
                base_dir = os.path.dirname(backend_dir)         # 项目根目录
                
                _ml_recommender = Recommender(
                    hybrid_model_path=os.path.join(base_dir, 'data', 'output5', 'hybrid_model.pkl'),
                    movies_path=os.path.join(base_dir, 'data', 'ml-latest-small', 'movies.csv'),
                    ratings_path=os.path.join(base_dir, 'data', 'output1', 'ratings_train.csv')
                )
                print("[+] 机器学习推荐系统已初始化")
            except Exception as e:
                print(f"[-] 机器学习推荐系统初始化失败: {e}")
                print("  将使用基础推荐策略")
                _ml_recommender = None
        return _ml_recommender
    
    def get_ml_recommender():
        """获取机器学习推荐系统实例"""
        if _ml_recommender is None:
            return init_ml_recommender()
        return _ml_recommender
    
    ML_ENABLED = True
except ImportError as e:
    print(f"[-] 无法导入机器学习模块: {e}")
    print("  将使用基础推荐策略")
    ML_ENABLED = False
    _ml_recommender = None
    
    def get_ml_recommender():
        return None


def get_recommendations_for_user(user: User, limit: int = 10):
    """
    个性化推荐服务（分阶段策略）

    策略：
    A. 无兴趣标签 → 非个性化推荐（全局热门：按评分数+平均分排序）
    B. 有兴趣标签但无行为数据（评分=0）→ 基于内容推荐（根据选定类型推荐高分电影）
    C. 有兴趣标签且有少量行为数据（0<评分<10）→ 轻量混合（70%基于选定类型，30%基于用户高分类型）
    D. 行为数据充足（评分≥10）→ 矩阵分解为主（待实现）

    本次实现：A/B/C
    """
    limit = max(0, int(limit))
    if limit == 0:
        return []

    user_id = user.id
    rated_ids = [r.movie_id for r in Rating.query.filter_by(user_id=user_id).all()]
    fav_ids = [f.movie_id for f in Favorite.query.filter_by(user_id=user_id).all()]
    exclude_ids = set(rated_ids + fav_ids)

    rating_count = len(rated_ids)
    preferred_genres = user.get_preferred_genres_list()  # 用户选定的兴趣标签

    # 评分聚合子查询（全局复用）
    rating_agg = (
        db.session.query(
            Rating.movie_id.label("movie_id"),
            func.avg(Rating.score).label("avg_score"),
            func.count(Rating.id).label("rating_count"),
        )
        .group_by(Rating.movie_id)
        .subquery()
    )

    def to_item(row):
        m = row[0]
        avg_score = float(row[1] or 0) if len(row) > 1 else 0
        rating_cnt = int(row[2] or 0) if len(row) > 2 else 0
        return {
            "id": m.id,
            "title": m.title,
            "release_year": m.release_year,
            "poster_url": m.poster_url,
            "rating_avg": round(avg_score, 2),
            "rating_count": rating_cnt,
        }

    # ========== 策略 A：无兴趣标签 → 非个性化推荐（全局热门） ==========
    if not preferred_genres:
        return _recommend_global_popular(exclude_ids, rating_agg, to_item, limit)

    # ========== 策略 B：有兴趣标签但无行为数据 → 纯内容推荐 ==========
    if rating_count == 0:
        return _recommend_by_selected_genres(preferred_genres, exclude_ids, rating_agg, to_item, limit)

    # ========== 策略 C：有兴趣标签 + 少量行为数据（<10）→ 轻量混合 ==========
    if rating_count < 10:
        return _recommend_light_hybrid(user_id, preferred_genres, exclude_ids, rating_agg, to_item, limit)

    # ========== 策略 D：行为数据充足（≥10）→ 矩阵分解 ==========
    if ML_ENABLED:
        ml_recommender = get_ml_recommender()
        if ml_recommender is not None:
            return _recommend_ml_based(ml_recommender, user, exclude_ids, rating_agg, to_item, limit)
    
    # 如果ML模型不可用，降级为轻量混合
    return _recommend_light_hybrid(user_id, preferred_genres, exclude_ids, rating_agg, to_item, limit)


def _recommend_global_popular(exclude_ids, rating_agg, to_item, limit):
    """策略A：全局热门（按评分数+平均分综合排序）"""
    q = db.session.query(Movie, rating_agg.c.avg_score, rating_agg.c.rating_count).outerjoin(
        rating_agg, rating_agg.c.movie_id == Movie.id
    )
    if exclude_ids:
        q = q.filter(~Movie.id.in_(exclude_ids))
    # 综合热度排序：评分数*平均分（避免只有1个5分的电影排第一）
    q = q.order_by(
        (func.coalesce(rating_agg.c.rating_count, 0) * func.coalesce(rating_agg.c.avg_score, 0)).desc(),
        Movie.release_year.desc().nullslast(),
        Movie.id.desc(),
    ).limit(limit)
    return [to_item(r) for r in q.all()]


def _recommend_by_selected_genres(genre_names, exclude_ids, rating_agg, to_item, limit):
    """策略B：基于用户选定的类型推荐（纯内容）"""
    genre_ids = [g.id for g in Genre.query.filter(Genre.name.in_(genre_names)).all()]
    if not genre_ids:
        # 如果类型不存在，降级为全局热门
        return _recommend_global_popular(exclude_ids, rating_agg, to_item, limit)

    q = (
        db.session.query(Movie, rating_agg.c.avg_score, rating_agg.c.rating_count)
        .join(MovieGenre, MovieGenre.movie_id == Movie.id)
        .outerjoin(rating_agg, rating_agg.c.movie_id == Movie.id)
        .filter(MovieGenre.genre_id.in_(genre_ids))
    )
    if exclude_ids:
        q = q.filter(~Movie.id.in_(exclude_ids))
    q = q.order_by(
        func.coalesce(rating_agg.c.avg_score, 0).desc(),
        func.coalesce(rating_agg.c.rating_count, 0).desc(),
        Movie.release_year.desc().nullslast(),
    ).limit(limit)
    return [to_item(r) for r in q.all()]


def _recommend_light_hybrid(user_id, selected_genre_names, exclude_ids, rating_agg, to_item, limit):
    """策略C：轻量混合（70%基于选定类型 + 30%基于用户高分类型）"""
    # 先取70%来自选定类型
    content_limit = int(limit * 0.7)
    content_items = _recommend_by_selected_genres(selected_genre_names, exclude_ids, rating_agg, to_item, content_limit)

    # 已推荐的电影ID，避免重复
    recommended_ids = {item["id"] for item in content_items}
    exclude_ids = exclude_ids | recommended_ids

    # 再取30%来自用户历史高分电影的类型偏好（协同过滤思路）
    collab_limit = limit - len(content_items)
    if collab_limit > 0:
        genre_rows = (
            db.session.query(MovieGenre.genre_id, func.count(MovieGenre.genre_id).label("cnt"))
            .join(Rating, Rating.movie_id == MovieGenre.movie_id)
            .filter(Rating.user_id == user_id, Rating.score >= 4)
            .group_by(MovieGenre.genre_id)
            .order_by(func.count(MovieGenre.genre_id).desc())
            .all()
        )
        preferred_genre_ids = [g.genre_id for g in genre_rows]

        if preferred_genre_ids:
            q = (
                db.session.query(Movie, rating_agg.c.avg_score, rating_agg.c.rating_count)
                .join(MovieGenre, MovieGenre.movie_id == Movie.id)
                .outerjoin(rating_agg, rating_agg.c.movie_id == Movie.id)
                .filter(MovieGenre.genre_id.in_(preferred_genre_ids))
            )
            if exclude_ids:
                q = q.filter(~Movie.id.in_(exclude_ids))
            q = q.order_by(func.coalesce(rating_agg.c.avg_score, 0).desc(), Movie.release_year.desc().nullslast()).limit(
                collab_limit
            )
            collab_items = [to_item(r) for r in q.all()]
            content_items.extend(collab_items)

    return content_items


def _recommend_ml_based(ml_recommender, user: User, exclude_ids, rating_agg, to_item, limit):
    """
    策略D：基于机器学习的推荐（矩阵分解混合模型）
    
    使用训练好的混合推荐系统（ALS + 基于内容）生成个性化推荐
    """
    try:
        # 1. 使用ML模型生成推荐（预测评分）
        # 注意：这里的user_id是数据库ID，需要映射到训练集中的userId
        # 如果映射关系不一致，可能需要额外的映射表
        ml_recommendations = ml_recommender.get_recommendations(
            user_id=user.id,
            n=limit * 2,  # 先取2倍，因为可能需要过滤
            exclude_rated=True,
            diversity=True  # 启用多样性推荐
        )
        
        # 2. 将ML推荐结果转换为数据库电影对象
        results = []
        for rec in ml_recommendations:
            movie_id = rec['movie_id']
            
            # 跳过已评分/收藏的电影
            if movie_id in exclude_ids:
                continue
            
            # 从数据库查询电影信息
            movie = Movie.query.get(movie_id)
            if not movie:
                continue
            
            # 查询评分统计
            rating_stats = db.session.query(
                func.avg(Rating.score).label("avg_score"),
                func.count(Rating.id).label("rating_count")
            ).filter(Rating.movie_id == movie_id).first()
            
            avg_score = float(rating_stats[0] or 0) if rating_stats else 0
            rating_count = int(rating_stats[1] or 0) if rating_stats else 0
            
            results.append({
                "id": movie.id,
                "title": movie.title,
                "release_year": movie.release_year,
                "poster_url": movie.poster_url,
                "rating_avg": round(avg_score, 2),
                "rating_count": rating_count,
                "ml_predicted_rating": round(rec['predicted_rating'], 2),  # ML模型预测评分
            })
            
            if len(results) >= limit:
                break
        
        # 3. 如果ML推荐不足，用轻量混合策略补充
        if len(results) < limit:
            print(f"ML推荐数量不足({len(results)}/{limit})，使用混合策略补充")
            recommended_ids = {item["id"] for item in results}
            exclude_ids = exclude_ids | recommended_ids
            
            preferred_genres = user.get_preferred_genres_list()
            hybrid_items = _recommend_light_hybrid(
                user.id, 
                preferred_genres, 
                exclude_ids, 
                rating_agg, 
                to_item, 
                limit - len(results)
            )
            results.extend(hybrid_items)
        
        return results
        
    except Exception as e:
        print(f"ML推荐失败: {e}")
        # 降级为轻量混合策略
        preferred_genres = user.get_preferred_genres_list()
        return _recommend_light_hybrid(user.id, preferred_genres, exclude_ids, rating_agg, to_item, limit)





