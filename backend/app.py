import os

from dotenv import load_dotenv
from flask import Flask, jsonify

from config import Config
from extensions import cors, db
from routes import register_blueprints


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # 确保 instance 目录存在（用于 SQLite）
    os.makedirs(app.config["INSTANCE_DIR"], exist_ok=True)

    # init extensions
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # register blueprints
    register_blueprints(app)

    @app.get("/api/health")
    def health():
        return jsonify({"code": 0, "message": "ok", "data": {"status": "up"}})

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



