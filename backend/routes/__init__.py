from routes.action_routes import action_bp
from routes.movie_geo_routes import geo_bp
from routes.movie_routes import movie_bp
from routes.user_routes import user_bp


def register_blueprints(app):
    app.register_blueprint(user_bp)
    app.register_blueprint(movie_bp)
    app.register_blueprint(geo_bp)
    app.register_blueprint(action_bp)






















