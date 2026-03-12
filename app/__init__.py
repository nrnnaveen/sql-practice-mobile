import os
import logging
from datetime import timedelta

from flask import Flask
from authlib.integrations.flask_client import OAuth

oauth = OAuth()


def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )

    # Single source of truth for configuration
    from config import SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    app.secret_key = SECRET_KEY

    # Sessions should survive browser restarts (important for mobile users)
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

    # Google OAuth config (Authlib reads these from app.config)
    app.config["GOOGLE_CLIENT_ID"] = GOOGLE_CLIENT_ID
    app.config["GOOGLE_CLIENT_SECRET"] = GOOGLE_CLIENT_SECRET

    # Configure logging so deployment issues are visible in Railway logs
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Initialise Authlib OAuth
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    # Initialise the local SQLite users database (creates the file if absent)
    from app.utils.db_init import init_db
    init_db()

    # Register feature blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.editor import editor_bp
    from app.routes.profile import profile_bp
    from app.routes.api import api_bp
    from app.routes.practice import practice_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(editor_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(practice_bp)

    return app
