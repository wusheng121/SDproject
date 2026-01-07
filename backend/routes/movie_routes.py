from sqlalchemy import func
from flask import Blueprint, request

from extensions import db
from auth import current_user
from models import Actor, Favorite, Genre, Movie, MovieActor, MovieGenre, Rating
from utils.response import err, ok

movie_bp = Blueprint("movie_bp", __name__, url_prefix="/api")


def _word_predicates(title: str):
    """
    以“单词”为单位做匹配，避免搜索 one 命中 stone。
    做法：对输入按空白切分，每个词要求命中（AND），单词边界用空格/开头/结尾/常见标点粗略限定。
    """
    words = [w.strip().lower() for w in title.split() if w.strip()]
    preds = []
    for w in words:
        # 常见分隔符组合（开头/中间/结尾）
        patterns = [
            f"{w}",  # 完全相等
            f"{w} %",  # 开头
            f"% {w} %",  # 中间
            f"% {w}",  # 结尾
            f"% {w}:%",
            f"% {w}-%",
            f"% {w},%",
            f"% {w}.%",
            f"% {w}!%",
            f"% {w}?%",
            f"% {w}'%",
        ]
        preds.append(db.or_(*[func.lower(Movie.title).like(p.lower()) for p in patterns]))
    return preds


@movie_bp.get("/movies")
def list_movies():
    """
    GET /api/movies
    query: page, page_size, genre, year, sort
    """
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 12))
    genre = request.args.get("genre")
    year = request.args.get("year")
    sort = request.args.get("sort", "hot")

    page = max(1, page)
    page_size = min(max(1, page_size), 50)

    rating_agg = (
        db.session.query(
            Rating.movie_id.label("movie_id"),
            func.avg(Rating.score).label("avg_score"),
            func.count(Rating.id).label("cnt"),
        )
        .group_by(Rating.movie_id)
        .subquery()
    )

    q = db.session.query(Movie, rating_agg.c.avg_score, rating_agg.c.cnt).outerjoin(rating_agg, rating_agg.c.movie_id == Movie.id)

    if year:
        try:
            y = int(year)
            q = q.filter(Movie.release_year == y)
        except Exception:
            pass

    if genre:
        q = q.join(MovieGenre, MovieGenre.movie_id == Movie.id).join(Genre, Genre.id == MovieGenre.genre_id).filter(Genre.name == genre)

    # sort：hot/new/rating（课程项目：hot 先按评分人数）
    if sort == "new":
        q = q.order_by(Movie.release_year.desc().nullslast(), Movie.id.desc())
    elif sort == "rating":
        q = q.order_by(func.coalesce(rating_agg.c.avg_score, 0).desc(), func.coalesce(rating_agg.c.cnt, 0).desc(), Movie.id.desc())
    else:  # hot
        q = q.order_by(func.coalesce(rating_agg.c.cnt, 0).desc(), func.coalesce(rating_agg.c.avg_score, 0).desc(), Movie.id.desc())

    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    # 批量取 genres
    movie_ids = [r[0].id for r in rows]
    genre_map = {mid: [] for mid in movie_ids}
    if movie_ids:
        grs = (
            db.session.query(MovieGenre.movie_id, Genre.name)
            .join(Genre, Genre.id == MovieGenre.genre_id)
            .filter(MovieGenre.movie_id.in_(movie_ids))
            .all()
        )
        for mid, gname in grs:
            genre_map.setdefault(mid, []).append(gname)

    items = []
    for m, avg_score, cnt in rows:
        items.append(
            {
                "id": m.id,
                "title": m.title,
                "release_year": m.release_year,
                "poster_url": m.poster_url,
                "genres": genre_map.get(m.id, []),
                "rating_avg": round(float(avg_score or 0), 2) if cnt else None,
                "rating_count": int(cnt or 0),
            }
        )

    return ok(
        {
            "page": page,
            "page_size": page_size,
            "total": total,
            "filters": {"genre": genre, "year": year, "sort": sort},
            "items": items,
        }
    )


@movie_bp.get("/movies/<int:movie_id>")
def movie_detail(movie_id: int):
    """
    GET /api/movies/:id
    """
    m = Movie.query.get(movie_id)
    if not m:
        return err("电影不存在", code=40401, http_status=404)

    genres = (
        db.session.query(Genre.name)
        .join(MovieGenre, MovieGenre.genre_id == Genre.id)
        .filter(MovieGenre.movie_id == movie_id)
        .all()
    )
    actors = (
        db.session.query(Actor.name)
        .join(MovieActor, MovieActor.actor_id == Actor.id)
        .filter(MovieActor.movie_id == movie_id)
        .all()
    )

    agg = db.session.query(func.avg(Rating.score), func.count(Rating.id)).filter(Rating.movie_id == movie_id).first()
    avg_score = float(agg[0] or 0)
    cnt = int(agg[1] or 0)

    # 如果用户已登录，则返回“我是否收藏/我的评分”
    user = current_user()
    is_favorited = None
    my_rating = None
    if user:
        is_favorited = Favorite.query.filter_by(user_id=user.id, movie_id=m.id).first() is not None
        r = Rating.query.filter_by(user_id=user.id, movie_id=m.id).first()
        if r:
            my_rating = {"score": r.score, "comment": r.comment, "updated_at": r.updated_at.isoformat() if r.updated_at else None}

    return ok(
        {
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "release_year": m.release_year,
            "poster_url": m.poster_url,
            "genres": [x[0] for x in genres],
            "actors": [x[0] for x in actors],
            "rating_avg": round(avg_score, 2) if cnt else None,
            "rating_count": cnt,
            "is_favorited": is_favorited,
            "my_rating": my_rating,
        }
    )


@movie_bp.get("/movies/search")
def search_movies():
    """
    GET /api/movies/search
    支持多条件：title / genre / actor（均可选，至少一项非空）
    多条件采用 AND 交集：例如同时填 title 与 genre，则需同时满足。
    """
    title = (request.args.get("title") or "").strip()
    genre = (request.args.get("genre") or "").strip()
    actor = (request.args.get("actor") or "").strip()
    q = (request.args.get("q") or "").strip()  # 兼容老前端

    if not any([title, genre, actor, q]):
        return ok({"items": []})

    movie_q = (
        db.session.query(Movie)
        .outerjoin(MovieGenre, MovieGenre.movie_id == Movie.id)
        .outerjoin(Genre, Genre.id == MovieGenre.genre_id)
        .outerjoin(MovieActor, MovieActor.movie_id == Movie.id)
        .outerjoin(Actor, Actor.id == MovieActor.actor_id)
    )

    filters = []

    # 标题：按单词边界匹配，多个词采用 AND（交集）
    if title:
        word_preds = _word_predicates(title)
        if word_preds:
            filters.append(db.and_(*word_preds))

    # 类型：精确/模糊匹配名称
    if genre:
        filters.append(Genre.name.ilike(f"%{genre}%"))

    # 演员：模糊匹配
    if actor:
        filters.append(Actor.name.ilike(f"%{actor}%"))

    # 兼容老的 q：如果只有 q，允许它在三处任一匹配；如果还有其他条件，则 q 也要求匹配
    if q:
        q_pred = (
            (Movie.title.ilike(f"%{q}%"))
            | (Genre.name.ilike(f"%{q}%"))
            | (Actor.name.ilike(f"%{q}%"))
        )
        filters.append(q_pred)

    if filters:
        movie_q = movie_q.filter(db.and_(*filters))

    movie_q = movie_q.distinct().order_by(Movie.id.desc()).limit(50)

    items = [{"id": m.id, "title": m.title, "release_year": m.release_year, "poster_url": m.poster_url} for m in movie_q.all()]
    return ok({"items": items})


@movie_bp.get("/genres")
def list_genres():
    """
    GET /api/genres
    返回所有类型名称列表（供前端下拉选择）
    """
    names = [g.name for g in Genre.query.order_by(Genre.name.asc()).all()]
    return ok({"items": names})




