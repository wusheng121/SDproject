"""
使用简化TMDB服务进行数据补全，避免SSL问题
"""

import argparse
import time

from flask import current_app

from app import create_app
from extensions import db
from models import Actor, Movie, MovieActor
from services.tmdb_service_simple import TMDBClientSimple


def enrich_one(client: TMDBClientSimple, movie: Movie, actor_top_n: int = 8):
    try:
        results = client.search_movie(movie.title, year=movie.release_year)
        if not results:
            print(f"  ❌ {movie.title} - 搜索无结果")
            return False

        # 取第一个匹配结果
        picked = results[0]
        tmdb_id = picked.get("id")
        if not tmdb_id:
            print(f"  ❌ {movie.title} - 无TMDB ID")
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

        if changed:
            print(f"  ✅ {movie.title} - 补全成功")
        else:
            print(f"  ⚠️  {movie.title} - 无需更新")
            
        return changed
        
    except Exception as e:
        print(f"  ❌ {movie.title} - 处理失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100, help="最多处理多少部电影")
    parser.add_argument("--sleep", type=float, default=0.3, help="每次请求后休眠（避免触发限流）")
    parser.add_argument("--actor-top-n", type=int, default=5, help="每部电影最多导入多少演员")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        api_key = current_app.config.get("TMDB_API_KEY", "")
        client = TMDBClientSimple(api_key)

        # 只补全缺字段的电影，按ID降序处理（最新添加的电影优先）
        q = Movie.query.filter((Movie.description.is_(None)) | (Movie.poster_url.is_(None))).order_by(Movie.id.desc())
        movies = q.limit(max(0, args.limit)).all()

        print(f"🎬 TMDB数据补全开始 (总共 {len(movies)} 部电影)")
        print("=" * 50)

        updated = 0
        for i, m in enumerate(movies, start=1):
            print(f"[{i}/{len(movies)}] 处理: 《{m.title}》 (ID: {m.id})")
            
            try:
                changed = enrich_one(client, m, actor_top_n=args.actor_top_n)
                if changed:
                    updated += 1
                
                # 每处理10部电影提交一次
                if i % 10 == 0:
                    db.session.commit()
                    print(f"💾 已提交 {i} 部电影的更新")
                
                time.sleep(max(0.0, float(args.sleep)))
                
            except Exception as e:
                print(f"  ❗ 处理异常: {e}")
                db.session.rollback()
                continue

        db.session.commit()
        print("=" * 50)
        print(f"🎉 TMDB数据补全完成!")
        print(f"📊 统计: 处理 {len(movies)} 部, 成功更新 {updated} 部")
        print(f"📈 成功率: {updated/len(movies)*100:.1f}%" if movies else "N/A")


if __name__ == "__main__":
    main()