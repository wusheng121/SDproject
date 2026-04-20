import os


def _parse_cors_origins(value: str):
    origins = [item.strip() for item in value.split(",") if item.strip()]
    return origins or ["*"]


class Config:
    # 课程项目：先用简单的 SECRET_KEY；生产环境请从环境变量读取
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # SQLite：默认放在 backend/instance/app.db（该目录会被 gitignore）
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    DB_PATH = os.environ.get("DB_PATH", os.path.join(INSTANCE_DIR, "app.db"))
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CORS：生产环境建议填前端域名，如 https://xxx.vercel.app
    CORS_ORIGINS = _parse_cors_origins(os.environ.get("CORS_ORIGINS", "*"))

    # JWT（示例）
    JWT_ALG = "HS256"
    JWT_EXPIRE_SECONDS = int(os.environ.get("JWT_EXPIRE_SECONDS", "86400"))

    # TMDB（用于补全简介/海报/演员）
    TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")




