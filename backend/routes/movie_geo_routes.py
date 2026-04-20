"""
GET /api/movies/geo — 地图页：带国家与经纬度的电影列表。
若库中无任何一条电影填写了 country + latitude + longitude，则返回内置 mock 数据。
"""

from urllib.parse import quote

from flask import Blueprint, request
from sqlalchemy import func

from extensions import db
from models import Genre, Movie, MovieGenre, Rating
from utils.response import ok

geo_bp = Blueprint("geo_bp", __name__, url_prefix="/api")

# mock 使用独立 id 段，避免与真实 movies.id 冲突导致误跳详情页
_MOCK_ID_BASE = 90000

# 20 部经典片假数据（美/日/法/英/中/韩/印），按 rating_count 在接口内统一排序
_MOCK_MOVIES_GEO_RAW = [
    ("The Godfather", "United States", -118.2437, 34.0522, 1972, "剧情", 4.52, 1850000),
    ("Citizen Kane", "United States", -73.9857, 40.7484, 1941, "剧情", 4.45, 920000),
    ("Pulp Fiction", "United States", -118.4679, 33.9850, 1994, "犯罪", 4.48, 2100000),
    ("Forrest Gump", "United States", -86.3077, 32.3668, 1994, "剧情", 4.55, 1980000),
    ("Schindler's List", "United States", 19.4803, 50.0647, 1993, "剧情", 4.60, 1120000),
    ("七武士", "Japan", 139.6917, 35.6895, 1954, "剧情", 4.58, 420000),
    ("千与千寻", "Japan", 139.5793, 35.6762, 2001, "动画", 4.62, 980000),
    ("罗生门", "Japan", 135.7681, 35.0116, 1950, "剧情", 4.50, 380000),
    ("天使爱美丽", "France", 2.3522, 48.8566, 2001, "爱情", 4.40, 890000),
    ("四百击", "France", 2.2945, 48.8584, 1959, "剧情", 4.42, 310000),
    ("阿拉伯的劳伦斯", "United Kingdom", -0.1276, 51.5074, 1962, "剧情", 4.46, 520000),
    ("猜火车", "United Kingdom", -3.1883, 55.9533, 1996, "剧情", 4.35, 610000),
    ("霸王别姬", "China", 116.4074, 39.9042, 1993, "剧情", 4.65, 720000),
    ("卧虎藏龙", "China", 121.4737, 31.2304, 2000, "武侠", 4.38, 540000),
    ("寄生虫", "South Korea", 126.9780, 37.5665, 2019, "剧情", 4.56, 1450000),
    ("老男孩", "South Korea", 126.9780, 37.5172, 2003, "惊悚", 4.33, 680000),
    ("阿育王", "India", 77.2090, 28.6139, 2001, "剧情", 4.20, 410000),
    ("三傻大闹宝莱坞", "India", 72.8777, 19.0760, 2009, "喜剧", 4.44, 1320000),
    ("地球脉动（纪录片）", "United Kingdom", -0.0991, 51.5155, 2006, "纪录", 4.70, 960000),
    ("花样年华", "China", 114.1694, 22.3193, 2000, "爱情", 4.41, 480000),
]


def _mock_items():
    items = []
    for i, row in enumerate(_MOCK_MOVIES_GEO_RAW):
        title, country, lon, lat, year, genre, avg_r, cnt = row
        items.append(
            {
                "id": _MOCK_ID_BASE + i + 1,
                "title": title,
                "country": country,
                "longitude": lon,
                "latitude": lat,
                "release_year": year,
                "genre": genre,
                "avg_rating": round(avg_r, 2),
                "rating_count": cnt,
                "poster_url": f"https://placehold.co/300x450/1a1a2e/eee?text={quote(title[:12])}",
            }
        )
    items.sort(key=lambda x: x["rating_count"], reverse=True)
    return items


def _has_real_geo_rows():
    return (
        db.session.query(Movie.id)
        .filter(
            Movie.country.isnot(None),
            Movie.country != "",
            Movie.latitude.isnot(None),
            Movie.longitude.isnot(None),
        )
        .first()
        is not None
    )


def _parse_year_bounds():
    yf = request.args.get("year_from", "1900")
    yt = request.args.get("year_to", "2024")
    try:
        year_from = int(yf)
        year_to = int(yt)
    except ValueError:
        year_from, year_to = 1900, 2024
    if year_from > year_to:
        year_from, year_to = year_to, year_from
    return year_from, year_to


@geo_bp.get("/movies/geo")
def movies_geo():
    year_from, year_to = _parse_year_bounds()
    genre = (request.args.get("genre") or "").strip() or None

    if not _has_real_geo_rows():
        items = _mock_items()
        items = [x for x in items if year_from <= x["release_year"] <= year_to]
        if genre:
            items = [x for x in items if x["genre"] == genre]
        items = items[:300]
        return ok({"items": items})

    rating_agg = (
        db.session.query(
            Rating.movie_id.label("movie_id"),
            func.avg(Rating.score).label("avg_score"),
            func.count(Rating.id).label("cnt"),
        )
        .group_by(Rating.movie_id)
        .subquery()
    )

    q = (
        db.session.query(Movie, rating_agg.c.avg_score, rating_agg.c.cnt)
        .outerjoin(rating_agg, rating_agg.c.movie_id == Movie.id)
        .filter(
            Movie.country.isnot(None),
            Movie.country != "",
            Movie.latitude.isnot(None),
            Movie.longitude.isnot(None),
            Movie.release_year.isnot(None),
            Movie.release_year >= year_from,
            Movie.release_year <= year_to,
        )
    )

    if genre:
        q = q.join(MovieGenre, MovieGenre.movie_id == Movie.id).join(Genre, Genre.id == MovieGenre.genre_id).filter(Genre.name == genre)

    q = q.order_by(func.coalesce(rating_agg.c.cnt, 0).desc(), Movie.id.desc()).limit(300)
    rows = q.all()

    movie_ids = [r[0].id for r in rows]
    genre_map = {mid: [] for mid in movie_ids}
    if movie_ids:
        grs = (
            db.session.query(MovieGenre.movie_id, Genre.name)
            .join(Genre, Genre.id == MovieGenre.genre_id)
            .filter(MovieGenre.movie_id.in_(movie_ids))
            .order_by(Genre.name.asc())
            .all()
        )
        for mid, gname in grs:
            genre_map.setdefault(mid, []).append(gname)

    items = []
    for m, avg_score, cnt in rows:
        glist = genre_map.get(m.id, [])
        primary_genre = sorted(glist)[0] if glist else ""
        rc = int(cnt or 0)
        av = float(avg_score or 0)
        items.append(
            {
                "id": m.id,
                "title": m.title,
                "country": m.country,
                "longitude": float(m.longitude),
                "latitude": float(m.latitude),
                "release_year": m.release_year,
                "genre": primary_genre,
                "avg_rating": round(av, 2) if rc else None,
                "rating_count": rc,
                "poster_url": m.poster_url,
            }
        )

    # 查询已按 rating_count 排序；limit 300 已在 SQL
    return ok({"items": items})
