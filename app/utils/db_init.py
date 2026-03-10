import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

# Place the database file one level above this package (i.e. repo root/database/)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.environ.get("DB_DIR", os.path.join(_REPO_ROOT, "database"))
DB_PATH = os.path.join(DB_DIR, "users.db")


def init_db():
    """Create the SQLite database and users table if they do not already exist."""
    try:
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
            logger.info("Created database directory: %s", DB_DIR)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                email    TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()
        logger.info("Database ready at %s", DB_PATH)
    except Exception as exc:
        logger.error("Error initialising database: %s", exc)
