"""
更新TMDB补全脚本以生成正确的报告

这个脚本修复了两个主要问题：
1. 标题格式未同步normalized的问题
2. 中文标题乱码的编码问题

使用方法：
1. 运行修复后重新生成报告
2. 或者直接使用create_clean_report.py生成全新的报告
"""

import argparse
import pandas as pd
from app import create_app
from models import Movie, MovieActor
from services.tmdb_service import TMDBClient
from flask import current_app


def generate_comprehensive_report(output_path: str):
    """生成完整的TMDB补全报告"""
    app = create_app()
    
    with app.app_context():
        api_key = current_app.config.get("TMDB_API_KEY", "")
        client = TMDBClient(api_key)
        
        movies = Movie.query.order_by(Movie.id.asc()).all()
        report_rows = []
        
        for movie in movies:
            movie_id = movie.id
            title = movie.title  # 使用数据库中的normalized标题
            release_year = movie.release_year
            
            # 检查增强状态
            has_description = bool(movie.description and movie.description.strip())
            has_poster = bool(movie.poster_url and movie.poster_url.strip())
            has_actors = MovieActor.query.filter_by(movie_id=movie_id).first() is not None
            
            # 获取TMDB详细信息（仅对已增强的电影）
            if has_description or has_poster or has_actors:
                try:
                    results = client.search_movie(title, year=release_year)
                    if results:
                        picked = results[0]
                        tmdb_id = picked.get("id", "")
                        tmdb_title = picked.get("title", "")
                        tmdb_release_date = picked.get("release_date", "")
                        status = "updated"
                        reason = "TMDB data available"
                    else:
                        tmdb_id = tmdb_title = tmdb_release_date = ""
                        status = "enhanced_but_unmatched"
                        reason = "enhanced but no TMDB match found"
                except Exception as e:
                    tmdb_id = tmdb_title = tmdb_release_date = ""
                    status = "error"
                    reason = f"API error: {str(e)}"
            else:
                tmdb_id = tmdb_title = tmdb_release_date = ""
                status = "not_processed"
                reason = "not enriched yet"
            
            report_rows.append({
                'movie_id': movie_id,
                'title': title,
                'release_year': release_year,
                'status': status,
                'reason': reason,
                'tmdb_id': tmdb_id,
                'tmdb_title': tmdb_title,
                'tmdb_release_date': tmdb_release_date,
                'has_description': int(has_description),
                'has_poster': int(has_poster),
                'has_actors': int(has_actors),
                'language': 'zh-CN'
            })
        
        # 生成报告
        df = pd.DataFrame(report_rows)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        # 统计信息
        total = len(report_rows)
        updated = len([r for r in report_rows if r['status'] == 'updated'])
        print(f"Comprehensive report generated: {output_path}")
        print(f"Total movies: {total}, TMDB enriched: {updated}")
        
        return df


def main():
    parser = argparse.ArgumentParser(description="Generate comprehensive TMDB enrichment report")
    parser.add_argument("--output", default="../data/tmdb_enrich_report_final_version.csv", 
                       help="Output CSV file path")
    args = parser.parse_args()
    
    generate_comprehensive_report(args.output)


if __name__ == "__main__":
    main()