from datetime import datetime

from extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    favorites = db.relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    ratings = db.relationship("Rating", back_populates="user", cascade="all, delete-orphan")


class Movie(db.Model, TimestampMixin):
    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), index=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    release_year = db.Column(db.Integer, index=True, nullable=True)
    poster_url = db.Column(db.String(500), nullable=True)

    genres = db.relationship("MovieGenre", back_populates="movie", cascade="all, delete-orphan")
    actors = db.relationship("MovieActor", back_populates="movie", cascade="all, delete-orphan")
    favorites = db.relationship("Favorite", back_populates="movie", cascade="all, delete-orphan")
    ratings = db.relationship("Rating", back_populates="movie", cascade="all, delete-orphan")


class Genre(db.Model):
    __tablename__ = "genres"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, index=True, nullable=False)

    movies = db.relationship("MovieGenre", back_populates="genre", cascade="all, delete-orphan")


class Actor(db.Model):
    __tablename__ = "actors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, index=True, nullable=False)

    movies = db.relationship("MovieActor", back_populates="actor", cascade="all, delete-orphan")


class MovieGenre(db.Model):
    __tablename__ = "movie_genres"

    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False)
    genre_id = db.Column(db.Integer, db.ForeignKey("genres.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("movie_id", "genre_id", name="uq_movie_genre"),
    )

    movie = db.relationship("Movie", back_populates="genres")
    genre = db.relationship("Genre", back_populates="movies")


class MovieActor(db.Model):
    __tablename__ = "movie_actors"

    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("actors.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("movie_id", "actor_id", name="uq_movie_actor"),
    )

    movie = db.relationship("Movie", back_populates="actors")
    actor = db.relationship("Actor", back_populates="movies")


class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "movie_id", name="uq_favorite_user_movie"),
    )

    user = db.relationship("User", back_populates="favorites")
    movie = db.relationship("Movie", back_populates="favorites")


class Rating(db.Model, TimestampMixin):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)  # 1~5
    comment = db.Column(db.String(500), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "movie_id", name="uq_rating_user_movie"),
    )

    user = db.relationship("User", back_populates="ratings")
    movie = db.relationship("Movie", back_populates="ratings")





