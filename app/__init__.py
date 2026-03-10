import os
import sqlite3
from flask import Flask
from config import SECRET_KEY


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.secret_key = SECRET_KEY

    # Create local SQLite users database automatically
    if not os.path.exists("database"):
        os.makedirs("database")
    db_path = "database/users.db"
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
        )
        """)
        conn.commit()
        conn.close()

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.editor import editor_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(editor_bp)

    return app
