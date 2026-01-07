import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from sqlalchemy import inspect, text
from werkzeug.exceptions import HTTPException

from config import Config
from extensions import cors, db
from routes import register_blueprints
from utils.response import err


def ensure_sqlite_schema(app):
    """
    开发环境自修复：如果 users 表缺少 preferred_genres 列，则自动添加。
    仅在 SQLite 下执行，避免生产环境误操作。
    """
    try:
        with app.app_context():
            engine = db.get_engine()
            if engine.url.get_backend_name() != "sqlite":
                return

            inspector = inspect(engine)
            columns = [col["name"] for col in inspector.get_columns("users")]
            if "preferred_genres" in columns:
                return

            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN preferred_genres TEXT"))
                conn.commit()
            print("✓ 已自动添加 users.preferred_genres 列")
    except Exception as e:
        print(f"⚠️ 自动修复 users.preferred_genres 列失败: {e}")


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # 确保 instance 目录存在（用于 SQLite）
    os.makedirs(app.config["INSTANCE_DIR"], exist_ok=True)

    # init extensions
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # SQLite 自修复缺失列（便于本地测试）
    ensure_sqlite_schema(app)

    # register blueprints
    register_blueprints(app)
    
    # 步骤四：初始化机器学习推荐系统（Flask 3 移除了 before_first_request）
    try:
        from services.recommendation_service import init_ml_recommender
        init_ml_recommender()
    except Exception as e:
        print(f"ML推荐系统初始化失败: {e}")
        print("将使用基础推荐策略")

    @app.get("/api/health")
    def health():
        return jsonify({"code": 0, "message": "ok", "data": {"status": "up"}})

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        # 统一错误响应：404/405/400 等都返回 JSON，且 code 非 0
        # e.code 是 HTTP 状态码
        return err(e.name, code=int(e.code) * 100, http_status=e.code)

    @app.errorhandler(Exception)
    def handle_exception(_e: Exception):
        # 统一 500（不要把内部异常细节直接暴露给前端）
        return err("Internal Server Error", code=50000, http_status=500)

    @app.cli.command("init-db")
    def init_db():
        """初始化数据库表（SQLite）。"""
        with app.app_context():
            db.create_all()
        print("Database initialized.")

    return app


if __name__ == "__main__":
    app = create_app()
    # 课程项目：启动时自动建表（方便第一次运行）
    with app.app_context():
        db.create_all()
    app.run(host="127.0.0.1", port=5000, debug=True)




