from flask import Blueprint, jsonify, request

movie_bp = Blueprint("movie_bp", __name__, url_prefix="/api")


def _ok(data=None, message="ok"):
    return jsonify({"code": 0, "message": message, "data": data})


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

    # mock 数据：后续替换为数据库分页查询
    items = [
        {
            "id": 1,
            "title": "Interstellar",
            "release_year": 2014,
            "poster_url": "https://example.com/poster/interstellar.jpg",
            "genres": ["Sci-Fi", "Drama"],
            "rating_avg": 4.6,
        },
        {
            "id": 2,
            "title": "Inception",
            "release_year": 2010,
            "poster_url": "https://example.com/poster/inception.jpg",
            "genres": ["Sci-Fi", "Action"],
            "rating_avg": 4.5,
        },
    ]

    return _ok(
        {
            "page": page,
            "page_size": page_size,
            "total": len(items),
            "filters": {"genre": genre, "year": year, "sort": sort},
            "items": items,
        }
    )


@movie_bp.get("/movies/<int:movie_id>")
def movie_detail(movie_id: int):
    """
    GET /api/movies/:id
    """
    # mock：后续从 Movie/Actor/Genre/Rating 查询组装
    return _ok(
        {
            "id": movie_id,
            "title": "Interstellar",
            "description": "A team of explorers travel through a wormhole in space...",
            "release_year": 2014,
            "poster_url": "https://example.com/poster/interstellar.jpg",
            "genres": ["Sci-Fi", "Drama"],
            "actors": ["Matthew McConaughey", "Anne Hathaway"],
            "rating_avg": 4.6,
            "rating_count": 1234,
        }
    )


@movie_bp.get("/movies/search")
def search_movies():
    """
    GET /api/movies/search?q=xxx
    """
    q = (request.args.get("q") or "").strip()
    # mock：后续根据 title/actor/genre 做 LIKE 查询
    return _ok(
        {
            "q": q,
            "items": [
                {"id": 2, "title": "Inception", "release_year": 2010, "poster_url": None},
            ],
        }
    )



