"""
用 TMDB 补全 MovieLens 数据缺失字段：
- Movie.description（简介）
- Movie.poster_url（海报）
- Actor + MovieActor（演员）

运行（在 backend 目录下）：
  # 先设置环境变量（PowerShell）
  $env:TMDB_API_KEY="你的key"
  python -m seed.enrich_tmdb --limit 200

注意：
- TMDB 有请求频率限制，建议先 limit 小一点验证效果
"""

import argparse
import time

from flask import current_app

from app import create_app
from extensions import db
from models import Actor, Movie, MovieActor
from services.tmdb_service import TMDBClient


def enrich_one(client: TMDBClient, movie: Movie, actor_top_n: int = 8):
    results = client.search_movie(movie.title, year=movie.release_year)
    if not results:
        return False

    # 课程项目：先取第一个匹配结果（后续可做更严格的相似度匹配）
    picked = results[0]
    tmdb_id = picked.get("id")
    if not tmdb_id:
        return False

    detail = client.movie_detail(tmdb_id)
    credits = client.movie_credits(tmdb_id)

    overview = (detail.get("overview") or "").strip()
    poster_path = detail.get("poster_path")
    poster_url = client.poster_url(poster_path)

    changed = False
    if overview and not (movie.description or "").strip():
        movie.description = overview
        changed = True

    if poster_url and not (movie.poster_url or "").strip():
        movie.poster_url = poster_url
        changed = True

    cast = credits.get("cast") or []
    cast = cast[: max(0, int(actor_top_n))]

    for c in cast:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        actor = Actor.query.filter_by(name=name).first()
        if not actor:
            actor = Actor(name=name)
            db.session.add(actor)
            db.session.flush()

        if not MovieActor.query.filter_by(movie_id=movie.id, actor_id=actor.id).first():
            db.session.add(MovieActor(movie_id=movie.id, actor_id=actor.id))
            changed = True

    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100, help="最多处理多少部电影")
    parser.add_argument("--sleep", type=float, default=0.15, help="每次请求后休眠（避免触发限流）")
    parser.add_argument("--actor-top-n", type=int, default=8, help="每部电影最多导入多少演员")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        api_key = current_app.config.get("TMDB_API_KEY", "")
        client = TMDBClient(api_key)

        # 只补全缺字段的电影，按ID降序处理（最新添加的电影优先）
        q = Movie.query.filter((Movie.description.is_(None)) | (Movie.poster_url.is_(None))).order_by(Movie.id.desc())
        movies = q.limit(max(0, args.limit)).all()

        # 显示将要处理的电影（前5部）
        if movies:
            print(f"即将处理的电影（按ID降序，最新优先）:")
            for j, movie in enumerate(movies[:5], 1):
                print(f"  {j}. 《{movie.title}》 (ID: {movie.id}, 年份: {movie.release_year})")
            if len(movies) > 5:
                print(f"  以及还有 {len(movies) - 5} 部电影...")

        updated = 0
        for i, m in enumerate(movies, start=1):
            try:
                changed = enrich_one(client, m, actor_top_n=args.actor_top_n)
                if changed:
                    updated += 1
                if i % 20 == 0:
                    db.session.commit()
                time.sleep(max(0.0, float(args.sleep)))
            except Exception:
                # 单条失败不影响整体（课程项目用）
                db.session.rollback()
                continue

        db.session.commit()
        print(f"Processed: {len(movies)}, Updated: {updated}")


if __name__ == "__main__":
    main()



