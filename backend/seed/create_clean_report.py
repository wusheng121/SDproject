"""
创建一个全新的干净TMDB报告，完全避免编码问题
"""

import pandas as pd
import argparse
from app import create_app
from models import Movie, MovieActor


def create_clean_report(output_path: str):
    """
    直接从数据库创建干净的报告，避免编码问题
    """
    app = create_app()
    
    with app.app_context():
        # 获取所有电影和TMDB增强状态
        movies = Movie.query.order_by(Movie.id.asc()).all()
        
        report_rows = []
        
        for movie in movies:
            movie_id = movie.id
            title = movie.title  # 使用数据库中的normalized标题
            release_year = movie.release_year
            
            # 检查TMDB增强状态
            has_description = bool(movie.description and movie.description.strip())
            has_poster = bool(movie.poster_url and movie.poster_url.strip())
            has_actors = MovieActor.query.filter_by(movie_id=movie_id).first() is not None
            
            # 判断状态
            if has_description or has_poster or has_actors:
                status = "updated"
                reason = "TMDB data enriched"
            else:
                status = "not_processed"
                reason = "not enriched yet"
            
            # 创建干净的记录
            clean_row = {
                'movie_id': movie_id,
                'title': title,
                'release_year': release_year,
                'status': status,
                'reason': reason,
                'has_description': int(has_description),
                'has_poster': int(has_poster),
                'has_actors': int(has_actors),
                'enrichment_complete': int(has_description and has_poster)
            }
            
            report_rows.append(clean_row)
        
        # 创建DataFrame
        clean_df = pd.DataFrame(report_rows)
        
        # 使用UTF-8编码保存
        clean_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        # 统计信息
        total_movies = len(report_rows)
        enriched_count = len([r for r in report_rows if r['status'] == 'updated'])
        complete_count = len([r for r in report_rows if r['enrichment_complete'] == 1])
        
        print(f"Clean TMDB report created: {output_path}")
        print(f"Total movies: {total_movies}")
        print(f"TMDB enriched: {enriched_count} ({enriched_count/total_movies*100:.1f}%)")
        print(f"Complete enrichment (description + poster): {complete_count} ({complete_count/total_movies*100:.1f}%)")
        print("Report features:")
        print("- Uses normalized titles from database")
        print("- UTF-8 encoding with BOM for Windows compatibility")
        print("- No encoding issues")
        print("- Clear status indicators")


def main():
    parser = argparse.ArgumentParser(description="Create a clean TMDB report from scratch")
    parser.add_argument("--output", default="../data/tmdb_enrich_report_clean.csv", 
                       help="Output CSV file path")
    args = parser.parse_args()
    
    create_clean_report(args.output)


if __name__ == "__main__":
    main()