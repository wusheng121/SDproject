from sqlalchemy import func

from extensions import db
from models import Favorite, Movie, MovieGenre, Rating


def get_recommendations_for_user(user_id: int, limit: int = 10):
    """
    推荐服务（课程项目：先做一个“可解释”的简化策略）

    策略：
    - 优先：统计用户历史高分(>=4)电影的类型偏好 → 推荐同类型里评分更高的电影
    - 兜底：全站平均评分更高的电影
    - 排除：用户已评分/已收藏的电影
    """
    limit = max(0, int(limit))
    if limit == 0:
        return []

    rated_ids = [r.movie_id for r in Rating.query.filter_by(user_id=user_id).all()]
    fav_ids = [f.movie_id for f in Favorite.query.filter_by(user_id=user_id).all()]
    exclude_ids = set(rated_ids + fav_ids)

    # 1) 找用户高分电影的 genre_id
    genre_rows = (
        db.session.query(MovieGenre.genre_id, func.count(MovieGenre.genre_id).label("cnt"))
        .join(Rating, Rating.movie_id == MovieGenre.movie_id)
        .filter(Rating.user_id == user_id, Rating.score >= 4)
        .group_by(MovieGenre.genre_id)
        .order_by(func.count(MovieGenre.genre_id).desc())
        .all()
    )
    preferred_genre_ids = [g.genre_id for g in genre_rows]

    rating_agg = (
        db.session.query(
            Rating.movie_id.label("movie_id"),
            func.avg(Rating.score).label("avg_score"),
            func.count(Rating.id).label("cnt"),
        )
        .group_by(Rating.movie_id)
        .subquery()
    )

    def to_item(row):
        m = row[0]
        avg_score = float(row[1] or 0)
        return {"id": m.id, "title": m.title, "release_year": m.release_year, "poster_url": m.poster_url, "rating_avg": round(avg_score, 2)}

    items = []

    # 2) 按偏好类型推荐
    if preferred_genre_ids:
        q = (
            db.session.query(Movie, rating_agg.c.avg_score)
            .join(MovieGenre, MovieGenre.movie_id == Movie.id)
            .outerjoin(rating_agg, rating_agg.c.movie_id == Movie.id)
            .filter(MovieGenre.genre_id.in_(preferred_genre_ids))
        )
        if exclude_ids:
            q = q.filter(~Movie.id.in_(exclude_ids))
        q = q.order_by(func.coalesce(rating_agg.c.avg_score, 0).desc(), Movie.release_year.desc().nullslast(), Movie.id.desc()).limit(limit)

        items = [to_item(r) for r in q.all()]

    # 3) 兜底：全站高分
    if len(items) < limit:
        q = db.session.query(Movie, rating_agg.c.avg_score).outerjoin(rating_agg, rating_agg.c.movie_id == Movie.id)
        if exclude_ids:
            q = q.filter(~Movie.id.in_(exclude_ids))
        q = q.order_by(func.coalesce(rating_agg.c.avg_score, 0).desc(), Movie.release_year.desc().nullslast(), Movie.id.desc()).limit(limit - len(items))
        items.extend([to_item(r) for r in q.all()])

    return items





