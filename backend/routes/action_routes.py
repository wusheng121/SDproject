from flask import Blueprint, request

from auth import login_required
from extensions import db
from models import Favorite, Movie, Rating
from services.recommendation_service import get_recommendations_for_user
from utils.response import err, ok

action_bp = Blueprint("action_bp", __name__, url_prefix="/api")


def _get_strategy_info(user):
    """返回当前使用的推荐策略说明（用于前端展示/调试）"""
    rating_count = Rating.query.filter_by(user_id=user.id).count()
    preferred_genres = user.get_preferred_genres_list()

    if not preferred_genres:
        return {"strategy": "A", "description": "全局热门（无兴趣标签）"}
    if rating_count == 0:
        return {"strategy": "B", "description": "基于内容推荐（根据选定类型）"}
    if rating_count < 10:
        return {"strategy": "C", "description": f"轻量混合（评分数={rating_count}）"}
    return {"strategy": "D", "description": f"矩阵分解为主（评分数={rating_count}，待实现）"}


@action_bp.post("/action/favorite")
@login_required
def toggle_favorite(user):
    """
    POST /api/action/favorite
    body: { movie_id, favorite: true/false }
    """
    payload = request.get_json(silent=True) or {}
    movie_id = payload.get("movie_id")
    favorite = bool(payload.get("favorite", True))

    if not movie_id:
        return err("movie_id 不能为空", code=2001)

    movie = Movie.query.get(int(movie_id))
    if not movie:
        return err("电影不存在", code=2002, http_status=404)

    existing = Favorite.query.filter_by(user_id=user.id, movie_id=movie.id).first()
    if favorite:
        if not existing:
            db.session.add(Favorite(user_id=user.id, movie_id=movie.id))
            db.session.commit()
    else:
        if existing:
            db.session.delete(existing)
            db.session.commit()

    return ok({"movie_id": movie.id, "favorite": favorite}, "已更新收藏状态")


@action_bp.post("/action/rate")
@login_required
def rate_movie(user):
    """
    POST /api/action/rate
    body: { movie_id, score(1-5), comment? }
    """
    payload = request.get_json(silent=True) or {}
    movie_id = payload.get("movie_id")
    score = payload.get("score")
    comment = payload.get("comment")

    if not movie_id:
        return err("movie_id 不能为空", code=2101)
    if score is None:
        return err("score 不能为空", code=2102)

    try:
        score = int(score)
    except Exception:
        return err("score 必须是整数 1-5", code=2103)
    if score < 1 or score > 5:
        return err("score 必须在 1-5", code=2104)

    movie = Movie.query.get(int(movie_id))
    if not movie:
        return err("电影不存在", code=2105, http_status=404)

    existing = Rating.query.filter_by(user_id=user.id, movie_id=movie.id).first()
    if existing:
        existing.score = score
        existing.comment = comment
    else:
        db.session.add(Rating(user_id=user.id, movie_id=movie.id, score=score, comment=comment))
    db.session.commit()

    return ok(
        {
            "movie_id": movie.id,
            "score": score,
            "comment": comment,
        },
        "评分已提交",
    )


@action_bp.get("/recommendations")
@login_required
def recommendations(user):
    """
    GET /api/recommendations
    query: limit=10
    分阶段推荐：A(无标签热门)/B(有标签内容)/C(少量行为混合)/D(充足行为矩阵分解)
    """
    limit = int(request.args.get("limit", 10))
    items = get_recommendations_for_user(user=user, limit=limit)
    return ok({"user_id": user.id, "items": items, "strategy_info": _get_strategy_info(user)})




