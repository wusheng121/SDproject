from flask import Blueprint, jsonify, request

from services.recommendation_service import get_recommendations_for_user

action_bp = Blueprint("action_bp", __name__, url_prefix="/api")


def _ok(data=None, message="ok"):
    return jsonify({"code": 0, "message": message, "data": data})


def _err(message="error", code=1, http_status=400):
    return jsonify({"code": code, "message": message, "data": None}), http_status


@action_bp.post("/action/favorite")
def toggle_favorite():
    """
    POST /api/action/favorite
    body: { movie_id, favorite: true/false }
    """
    payload = request.get_json(silent=True) or {}
    movie_id = payload.get("movie_id")
    favorite = bool(payload.get("favorite", True))

    if not movie_id:
        return _err("movie_id 不能为空", code=2001)

    # mock：后续根据 token 得到 user_id，然后写 Favorite 表
    return _ok({"movie_id": int(movie_id), "favorite": favorite}, "已更新收藏状态")


@action_bp.post("/action/rate")
def rate_movie():
    """
    POST /api/action/rate
    body: { movie_id, score(1-5), comment? }
    """
    payload = request.get_json(silent=True) or {}
    movie_id = payload.get("movie_id")
    score = payload.get("score")
    comment = payload.get("comment")

    if not movie_id:
        return _err("movie_id 不能为空", code=2101)
    if score is None:
        return _err("score 不能为空", code=2102)

    try:
        score = int(score)
    except Exception:
        return _err("score 必须是整数 1-5", code=2103)
    if score < 1 or score > 5:
        return _err("score 必须在 1-5", code=2104)

    # mock：后续写 Rating 表并返回新的平均分
    return _ok(
        {
            "movie_id": int(movie_id),
            "score": score,
            "comment": comment,
        },
        "评分已提交",
    )


@action_bp.get("/recommendations")
def recommendations():
    """
    GET /api/recommendations
    query: limit=10
    """
    limit = int(request.args.get("limit", 10))
    # mock：后续从 token 解析 user_id
    user_id = 1
    items = get_recommendations_for_user(user_id=user_id, limit=limit)
    return _ok({"user_id": user_id, "items": items})



