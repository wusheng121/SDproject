from routes.admin_routes import admin_bp
from routes.agent_routes import agent_bp
from routes.assistant_ai_routes import assistant_ai_bp
from routes.assistant_routes import assistant_bp
from routes.auth_routes import auth_bp
from routes.behavior_routes import behavior_bp
from routes.behavior_v1_routes import behavior_v1_bp
from routes.product_routes import product_bp
from routes.trade_routes import trade_bp
from routes.user_v1_routes import user_v1_bp
from services.recommendation_service_mock import recommendation_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_v1_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(behavior_bp)
    app.register_blueprint(behavior_v1_bp)
    app.register_blueprint(trade_bp)
    app.register_blueprint(recommendation_bp)


def register_data_blueprints(app):
    """推荐、识图和工作区。业务接口由 Java 主服务处理，不注册。"""
    app.register_blueprint(assistant_ai_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(recommendation_bp)
