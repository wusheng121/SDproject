import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from sqlalchemy import inspect, text
from werkzeug.exceptions import HTTPException

from config import Config
from extensions import cors, db
from routes import register_blueprints
from utils.response import err


# TODO: 旧的 Movie 表修复逻辑已删除，现在使用 Product 表


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # 确保 instance 目录存在（用于 SQLite）
    os.makedirs(app.config["INSTANCE_DIR"], exist_ok=True)

    # init extensions
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # 注册路由
    register_blueprints(app)
    
    # TODO: 推荐系统暂时使用 Mock 数据，真实算法留给组员实现
    # try:
    #     from services.recommendation_service import init_ml_recommender
    #     init_ml_recommender()
    # except Exception as e:
    #     print(f"ML推荐系统初始化失败: {e}")
    #     print("将使用基础推荐策略")

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


app = create_app()

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)




