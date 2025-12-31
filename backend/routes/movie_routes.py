from sqlalchemy import func
from flask import Blueprint, request

from extensions import db
from auth import current_user
from models import Actor, Favorite, Genre, Movie, MovieActor, MovieGenre, Rating
from utils.response import err, ok

movie_bp = Blueprint("movie_bp", __name__, url_prefix="/api")


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
    GET /api/movies/search?q=xxx
    """
    q = (request.args.get("q") or "").strip()
    if not q:
        return ok({"q": q, "items": []})

    like = f"%{q}%"

    movie_q = (
        db.session.query(Movie)
        .outerjoin(MovieGenre, MovieGenre.movie_id == Movie.id)
        .outerjoin(Genre, Genre.id == MovieGenre.genre_id)
        .outerjoin(MovieActor, MovieActor.movie_id == Movie.id)
        .outerjoin(Actor, Actor.id == MovieActor.actor_id)
        .filter(
            (Movie.title.ilike(like))
            | (Genre.name.ilike(like))
            | (Actor.name.ilike(like))
        )
        .distinct()
        .order_by(Movie.id.desc())
        .limit(50)
    )

    items = [{"id": m.id, "title": m.title, "release_year": m.release_year, "poster_url": m.poster_url} for m in movie_q.all()]
    return ok({"q": q, "items": items})




