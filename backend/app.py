import logging
import os
import time
import uuid

from dotenv import load_dotenv
from flask import Flask, g, request
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from werkzeug.exceptions import HTTPException

from config import get_config
from extensions import cors, db, limiter, migrate
from routes import register_blueprints
from utils.logging import configure_logging
from utils.response import api_error

logger = logging.getLogger(__name__)


def create_app(config_name: str | None = None):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DATABASE_URL"]
    app.json.ensure_ascii = False

    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("mysql"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "connect_args": {"charset": "utf8mb4"},
        }
    elif ":memory:" in uri:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        }

    configure_logging(app)
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )
    limiter.init_app(app)

    try:
        from prometheus_flask_exporter import PrometheusMetrics

        PrometheusMetrics(app, group_by="endpoint")
    except Exception:
        logger.warning("prometheus exporter unavailable", exc_info=True)

    if app.config.get("SENTRY_DSN"):
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration

            sentry_sdk.init(
                dsn=app.config["SENTRY_DSN"],
                integrations=[FlaskIntegration()],
                traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                environment=app.config.get("APP_ENV"),
            )
        except Exception:
            logger.warning("sentry initialization failed", exc_info=True)

    register_blueprints(app)
    _register_request_hooks(app)
    _register_error_handlers(app)
    _register_health(app)
    _register_cli(app)
    return app


def _register_request_hooks(app):
    @app.before_request
    def start_request():
        g.trace_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        g.request_started = time.perf_counter()

    @app.after_request
    def finish_request(response):
        elapsed = (time.perf_counter() - getattr(g, "request_started", time.perf_counter())) * 1000
        response.headers["X-Request-ID"] = getattr(g, "trace_id", "-")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "latency_ms": round(elapsed, 2),
            },
        )
        return response


def _register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        code = (exc.name or "HTTP_ERROR").upper().replace(" ", "_")
        return api_error(code, exc.description or "请求失败", exc.code or 500)

    @app.errorhandler(Exception)
    def handle_exception(exc: Exception):
        logger.exception("unhandled exception")
        return api_error("INTERNAL_ERROR", "服务器内部错误", 500)


def _register_health(app):
    @app.get("/health/live")
    def health_live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def health_ready():
        checks = {"database": False, "redis": None}
        try:
            db.session.execute(text("SELECT 1"))
            checks["database"] = True
        except Exception:
            logger.exception("database readiness check failed")
        redis_url = app.config.get("REDIS_URL")
        if redis_url:
            try:
                import redis

                client = redis.Redis.from_url(redis_url, socket_connect_timeout=1)
                client.ping()
                checks["redis"] = True
            except Exception:
                logger.exception("redis readiness check failed")
                checks["redis"] = False
        ready = checks["database"] and checks["redis"] is not False
        return {"status": "ok" if ready else "degraded", "checks": checks}, (200 if ready else 503)


def _register_cli(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Create tables for local development only. Use Alembic in production."""
        db.create_all()
        print("Database tables created (development only).")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        from seed.init_products import seed_all

        seed_all()

    @app.cli.command("bootstrap-admin")
    def bootstrap_admin_command():
        from seed.bootstrap import bootstrap_admin

        bootstrap_admin()


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
