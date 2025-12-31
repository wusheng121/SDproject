"""
可选：初始化演示数据（课程项目建议准备一些电影数据，方便展示）

运行方式（在 backend 目录下）：
  python -m seed.seed_demo
"""

from extensions import db
from app import create_app
from models import Genre, Movie


def run():
    app = create_app()
    with app.app_context():
        db.create_all()

        sci_fi = Genre.query.filter_by(name="Sci-Fi").first() or Genre(name="Sci-Fi")
        drama = Genre.query.filter_by(name="Drama").first() or Genre(name="Drama")
        db.session.add_all([sci_fi, drama])
        db.session.commit()

        if not Movie.query.filter_by(title="Interstellar").first():
            m = Movie(
                title="Interstellar",
                description="A team of explorers travel through a wormhole in space...",
                release_year=2014,
                poster_url=None,
            )
            db.session.add(m)
            db.session.commit()

        print("seed done.")


if __name__ == "__main__":
    run()





