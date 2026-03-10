import os
import logging

from flask import Flask


def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )

    # Single source of truth for configuration
    from config import SECRET_KEY
    app.secret_key = SECRET_KEY

    # Configure logging so deployment issues are visible in Railway logs
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Initialise the local SQLite users database (creates the file if absent)
    from app.utils.db_init import init_db
    init_db()

    # Register feature blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.editor import editor_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(editor_bp)

    return app
