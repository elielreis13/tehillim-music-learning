from datetime import timedelta

from flask import Flask, session as flask_session
from .config import Config


def create_app(config=None) -> Flask:
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static",
        template_folder="templates",
    )
    app.config.from_object(Config)
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
    if config:
        app.config.update(config)

    @app.context_processor
    def inject_globals():
        from tehillim.content import groups_summary
        user_id = flask_session.get("user_id")
        current_user = {
            "id":         user_id,
            "email":      flask_session.get("email", ""),
            "name":       flask_session.get("name", ""),
            "is_teacher": flask_session.get("is_teacher", False),
        } if user_id else None
        return {
            "groups":       groups_summary(),
            "current_user": current_user,
        }

    from .auth    import bp as auth_bp
    from .modules import bp as modules_bp
    from .admin   import bp as admin_bp
    from .api     import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(modules_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
