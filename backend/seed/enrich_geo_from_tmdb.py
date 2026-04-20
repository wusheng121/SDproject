"""
用 TMDB 补全 movies 地理字段：
- Movie.country（英文国家名）
- Movie.latitude / Movie.longitude（国家中心点）

运行（在 backend 目录下，PowerShell）：
  $env:TMDB_API_KEY="你的key"
  python -m seed.enrich_geo_from_tmdb --limit 2000 --sleep 0.15

说明：
- 依赖本地离线国家中心点表：backend/data/country_centroids.json
- 只更新缺失地理字段（country/lat/lng 任一为空）
- TMDB 字段优先 production_countries，其次 origin_country
"""

import argparse
import json
import os
import time

from flask import current_app

from app import create_app
from extensions import db
from models import Movie
from services.tmdb_service import TMDBClient


def _load_centroids() -> dict:
    here = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(here, "..", "data", "country_centroids.json"))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _pick_country_iso(detail: dict) -> str | None:
    pcs = detail.get("production_countries") or []
    if pcs:
        iso = (pcs[0].get("iso_3166_1") or "").strip()
        if iso:
            return iso
    origins = detail.get("origin_country") or []
    if origins:
        iso = str(origins[0] or "").strip()
        if iso:
            return iso
    return None


def enrich_one(client: TMDBClient, centroids: dict, movie: Movie) -> bool:
    # 复用现有策略：用标题 + 年份 search，再 detail
    results = client.search_movie(movie.title, year=movie.release_year)
    if not results:
        return False

    picked = results[0]
    tmdb_id = picked.get("id")
    if not tmdb_id:
        return False

    detail = client.movie_detail(int(tmdb_id))
    iso = _pick_country_iso(detail or {})
    if not iso:
        return False

    c = centroids.get(iso)
    if not c:
        return False

    changed = False
    name = (c.get("name") or "").strip()
    lat = c.get("latitude")
    lng = c.get("longitude")

    if name and not (movie.country or "").strip():
        movie.country = name
        changed = True
    if lat is not None and movie.latitude is None:
        movie.latitude = float(lat)
        changed = True
    if lng is not None and movie.longitude is None:
        movie.longitude = float(lng)
        changed = True

    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=2000, help="最多处理多少部电影")
    parser.add_argument("--sleep", type=float, default=0.15, help="每次请求后休眠（避免触发限流）")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        api_key = current_app.config.get("TMDB_API_KEY", "")
        client = TMDBClient(api_key)
        centroids = _load_centroids()

        q = (
            Movie.query.filter(
                (Movie.country.is_(None))
                | (Movie.country == "")
                | (Movie.latitude.is_(None))
                | (Movie.longitude.is_(None))
            )
            .order_by(Movie.id.desc())
        )
        movies = q.limit(max(0, int(args.limit))).all()

        print(f"将处理 {len(movies)} 部电影（缺少 country/lat/lng）")

        updated = 0
        for i, m in enumerate(movies, start=1):
            try:
                changed = enrich_one(client, centroids, m)
                if changed:
                    updated += 1
                if i % 20 == 0:
                    db.session.commit()
                    print(f"进度 {i}/{len(movies)}，已更新 {updated}")
                time.sleep(max(0.0, float(args.sleep)))
            except Exception:
                db.session.rollback()
                continue

        db.session.commit()
        print(f"完成。Processed={len(movies)} Updated={updated}")


if __name__ == "__main__":
    main()

