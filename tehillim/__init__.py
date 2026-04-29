from flask import Flask
from .config import Config


def create_app(config=None) -> Flask:
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static",
        template_folder="templates",
    )
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    @app.context_processor
    def inject_supabase():
        return {
            "supabase_url": app.config["SUPABASE_URL"],
            "supabase_anon_key": app.config["SUPABASE_ANON_KEY"],
        }

    from .auth import bp as auth_bp
    from .modules import bp as modules_bp
    from .admin import bp as admin_bp
    from .api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(modules_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
