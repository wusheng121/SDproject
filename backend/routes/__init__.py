# 新路由
from routes.product_routes import product_bp
from routes.admin_routes import admin_bp
from routes.user_routes import user_bp
from routes.behavior_routes import behavior_bp

# 导入推荐服务 Mock
from services.recommendation_service_mock import recommendation_bp

# TODO: 旧路由已注释，待删除
# from routes.action_routes import action_bp
# from routes.movie_geo_routes import geo_bp
# from routes.movie_routes import movie_bp


def register_blueprints(app):
    # 新路由
    app.register_blueprint(user_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(behavior_bp)
    app.register_blueprint(recommendation_bp)
    
    # TODO: 旧路由已停用
    # app.register_blueprint(movie_bp)
    # app.register_blueprint(geo_bp)
    # app.register_blueprint(action_bp)






















