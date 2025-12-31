"""
生成TMDB数据补全报告，解决标题格式和编码问题

用法（在 backend 目录下）：
  python -m seed.generate_enrich_report --output ../data/tmdb_enrich_report.csv

功能：
- 检查哪些电影已经被TMDB补全
- 使用数据库中的normalized标题
- 解决中文乱码问题
"""

import argparse
import pandas as pd
from app import create_app
from models import Movie, Actor, MovieActor
from services.tmdb_service import TMDBClient
from flask import current_app


def generate_enrich_report(output_path: str):
    """
    生成TMDB补全情况报告
    """
    app = create_app()
    report_rows = []
    
    with app.app_context():
        api_key = current_app.config.get("TMDB_API_KEY", "")
        client = TMDBClient(api_key)
        
        # 获取所有电影
        movies = Movie.query.order_by(Movie.id.asc()).all()
        
        for movie in movies:
            movie_id = movie.id
            title = movie.title  # 使用数据库中的normalized标题
            release_year = movie.release_year
            
            # 检查该电影是否有TMDB补充的数据
            has_description = bool(movie.description and movie.description.strip())
            has_poster = bool(movie.poster_url and movie.poster_url.strip())
            has_actors = MovieActor.query.filter_by(movie_id=movie_id).first() is not None
            
            # 判断该电影是否被TMDB补全过
            tmdb_enriched = has_description or has_poster or has_actors
            
            if tmdb_enriched:
                # 尝试查找TMDB信息来做报告
                try:
                    results = client.search_movie(title, year=release_year)
                    if results:
                        picked = results[0]
                        tmdb_id = picked.get("id")
                        tmdb_title = picked.get("title", "")
                        release_date = picked.get("release_date", "")
                        status = "updated"
                        reason = ""
                    else:
                        tmdb_id = ""
                        tmdb_title = ""
                        release_date = ""
                        status = "no_match" 
                        reason = "search returned empty"
                except Exception as e:
                    tmdb_id = ""
                    tmdb_title = ""
                    release_date = ""
                    status = "error"
                    reason = str(e)
            else:
                tmdb_id = ""
                tmdb_title = ""
                release_date = ""
                status = "not_processed"
                reason = "not enriched yet"
            
            report_rows.append({
                "movie_id": movie_id,
                "title": title,  # 使用normalized标题
                "release_year": release_year,
                "status": status,
                "reason": reason,
                "tmdb_id": tmdb_id,
                "tmdb_title": tmdb_title,  # 正确的中文标题
                "tmdb_release_date": release_date,
                "has_description": int(has_description),
                "has_poster": int(has_poster),
                "has_actors": int(has_actors),
            })
    
    # 生成DataFrame并保存
    df = pd.DataFrame(report_rows)
    
    # 使用utf-8编码解决中文问题，支持Windows Excel打开
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    # 统计信息
    total_movies = len(report_rows)
    enriched_movies = len([r for r in report_rows if r["status"] == "updated"])
    print(f"Generated TMDB enrichment report for {total_movies} movies")
    print(f"Successfully enriched: {enriched_movies} movies")
    print(f"Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate TMDB enrichment report")
    parser.add_argument("--output", default="../data/tmdb_enrich_report.csv", 
                       help="Output CSV file path")
    args = parser.parse_args()
    
    generate_enrich_report(args.output)


if __name__ == "__main__":
    main()