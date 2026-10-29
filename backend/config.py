import os


def _split_csv(value: str):
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me-0123456789abcdef")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}

    JWT_ALG = os.getenv("JWT_ALG", "HS256")
    JWT_ISSUER = os.getenv("JWT_ISSUER", "campus-market")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "campus-market-web")
    JWT_ACCESS_TTL_SECONDS = int(os.getenv("JWT_ACCESS_TTL_SECONDS", "900"))
    JWT_REFRESH_TTL_SECONDS = int(os.getenv("JWT_REFRESH_TTL_SECONDS", str(30 * 24 * 3600)))

    REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "cm_refresh")
    REFRESH_COOKIE_SECURE = _bool(os.getenv("REFRESH_COOKIE_SECURE"), False)
    REFRESH_COOKIE_SAMESITE = os.getenv("REFRESH_COOKIE_SAMESITE", "Lax")
    REFRESH_COOKIE_PATH = os.getenv("REFRESH_COOKIE_PATH", "/api/v1/auth")

    BCRYPT_COST = int(os.getenv("BCRYPT_COST", "12"))

    PHONE_ENC_KEY = os.getenv("PHONE_ENC_KEY", "")
    PHONE_HASH_KEY = os.getenv("PHONE_HASH_KEY", "")

    CORS_ORIGINS = _split_csv(os.getenv("CORS_ORIGINS", "http://localhost:5173"))
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_ENABLED = _bool(os.getenv("RATELIMIT_ENABLED"), True)
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "300 per minute")

    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = _bool(os.getenv("SMTP_USE_TLS"), False)
    MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@campus-market.local")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")

    # Dev defaults are intentionally local-only. Production config overrides these.
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://campus:campus@127.0.0.1:3307/campus_market?charset=utf8mb4",
    )
    REDIS_URL = os.getenv("REDIS_URL", "")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    SECRET_KEY = "test-secret-0123456789abcdef0123456789"
    DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    RATELIMIT_ENABLED = False
    RATELIMIT_STORAGE_URI = "memory://"
    BCRYPT_COST = 4
    REFRESH_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    DEBUG = False

    @classmethod
    def validate(cls):
        missing = []
        for key in ("DATABASE_URL", "REDIS_URL", "SECRET_KEY", "PHONE_ENC_KEY", "PHONE_HASH_KEY"):
            if not os.getenv(key):
                missing.append(key)
        if missing:
            raise RuntimeError(f"Missing required production configuration: {', '.join(missing)}")
        if len(os.getenv("SECRET_KEY", "")) < 32:
            raise RuntimeError("SECRET_KEY must be at least 32 bytes for HS256")
        if os.getenv("CORS_ORIGINS", "").strip() in {"", "*"}:
            raise RuntimeError("CORS_ORIGINS must be an explicit allowlist in production")


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    env = (name or os.getenv("APP_ENV") or "development").strip().lower()
    config_cls = CONFIG_MAP.get(env, DevelopmentConfig)
    if config_cls is ProductionConfig:
        config_cls.validate()
    return config_cls
