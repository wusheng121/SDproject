"""
导入 MovieLens movies.csv 到本项目数据库（SQLite）

用法（Windows PowerShell，在 backend 目录下）：
  python -m seed.import_movielens --movies ..\\data\\movies.csv

说明：
- MovieLens 的 movieId 会作为本项目 Movie.id（方便稳定引用）
- MovieLens 的标题常见格式为：`Great Gatsby, The (1974)`（把冠词放后面便于排序）
  本脚本会在写入数据库前做 normalize：还原为 `The Great Gatsby (1974)`。
- genres 会拆分并写入 Genre + MovieGenre
- description/poster_url/actors MovieLens 没有，保持为空
"""

import argparse
import re

import pandas as pd

from app import create_app
from extensions import db
from models import Genre, Movie, MovieGenre


TITLE_YEAR_RE = re.compile(r"^(?P<title>.*)\s+\((?P<year>\d{4})\)\s*$")
ARTICLES = {"a", "an", "the"}


def parse_title_year(raw_title: str):
    raw_title = (raw_title or "").strip()
    m = TITLE_YEAR_RE.match(raw_title)
    if not m:
        return raw_title, None
    title = m.group("title").strip()
    year = int(m.group("year"))
    return title, year


def normalize_article_title(title: str) -> str:
    """
    MovieLens 约定：把 A/An/The 移到最后，比如：
      "Great Gatsby, The" -> "The Great Gatsby"
      "Boy and His Dog, A" -> "A Boy and His Dog"
    """
    s = (title or "").strip()
    if "," not in s:
        return s
    main, suffix = [x.strip() for x in s.rsplit(",", 1)]
    if not main or not suffix:
        return s
    if suffix.lower() in ARTICLES:
        # 保留 MovieLens 原大小写（A/An/The）
        article = suffix[0].upper() + suffix[1:]
        return f"{article} {main}"
    return s


def import_movies(movies_csv_path: str, limit: int | None = None):
    df = pd.read_csv(movies_csv_path)
    if limit:
        df = df.head(int(limit))

    # 预加载已有 genre
    existing_genres = {g.name: g for g in Genre.query.all()}

    created_movies = 0
    export_rows = []
    for _, row in df.iterrows():
        movie_id = int(row["movieId"])
        raw_title = str(row["title"])
        genres_raw = str(row.get("genres", "") or "")

        title_part, year = parse_title_year(raw_title)
        normalized_title = normalize_article_title(title_part)
        changed = normalized_title != title_part

        movie = Movie.query.get(movie_id)
        if not movie:
            movie = Movie(id=movie_id, title=normalized_title, release_year=year, description=None, poster_url=None)
            db.session.add(movie)
            created_movies += 1
        else:
            # 如果之前导入过，允许更新 title/year
            movie.title = normalized_title
            movie.release_year = year

        export_rows.append(
            {
                "movieId": movie_id,
                "raw_title": raw_title,  # MovieLens 原始 title（含年份、含 “, The/A/An”）
                "raw_title_part": title_part,  # 去掉年份后的 title
                "db_title": normalized_title,  # 实际写入数据库的 title（不含年份）
                "release_year": year or "",
                "changed": int(changed),
                "db_display_title": f"{normalized_title} ({year})" if year else normalized_title,
                "genres": genres_raw,
            }
        )

        # genres
        if genres_raw and genres_raw != "(no genres listed)":
            genre_names = [g.strip() for g in genres_raw.split("|") if g.strip()]
        else:
            genre_names = []

        for gname in genre_names:
            g = existing_genres.get(gname)
            if not g:
                g = Genre(name=gname)
                db.session.add(g)
                db.session.flush()
                existing_genres[gname] = g

            # 关联表去重
            if not MovieGenre.query.filter_by(movie_id=movie_id, genre_id=g.id).first():
                db.session.add(MovieGenre(movie_id=movie_id, genre_id=g.id))

        if created_movies % 200 == 0:
            db.session.commit()

    db.session.commit()
    return created_movies, export_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--movies", required=True, help="movies.csv 路径")
    parser.add_argument("--limit", type=int, default=None, help="只导入前 N 条（调试用）")
    parser.add_argument("--export", default="..\\data\\movies_normalized_preview.csv", help="导出 title 规范化对照表（csv）")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        db.create_all()
        created, rows = import_movies(args.movies, limit=args.limit)
        if args.export:
            out_df = pd.DataFrame(rows)
            # utf-8-sig：Windows 下用 Excel 打开更友好
            out_df.to_csv(args.export, index=False, encoding="utf-8-sig")
            print(f"Exported preview: {args.export}")
        print(f"Imported movies: {created}")


if __name__ == "__main__":
    main()


