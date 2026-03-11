import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

# Place the database file one level above this package (i.e. repo root/database/)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.environ.get("DB_DIR", os.path.join(_REPO_ROOT, "database"))
DB_PATH = os.path.join(DB_DIR, "users.db")


def _migrate(conn):
    """Add any new columns introduced after the initial schema."""
    cur = conn.cursor()
    existing = {row[1] for row in cur.execute("PRAGMA table_info(users)")}
    new_columns = [
        ("name", "TEXT"),
        ("picture", "TEXT"),
        ("google_id", "TEXT"),
    ]
    _allowed_cols = {"name", "picture", "google_id"}
    _allowed_types = {"TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"}
    for col, col_type in new_columns:
        if col not in existing:
            # Whitelist both column name and type before using in DDL
            if col not in _allowed_cols or col_type not in _allowed_types:
                logger.error("Refusing to migrate unknown column %s %s", col, col_type)
                continue
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
            logger.info("Migrated users table: added column %s", col)
    conn.commit()


def init_db():
    """Create the SQLite database and required tables if they do not already exist."""
    try:
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
            logger.info("Created database directory: %s", DB_DIR)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                email     TEXT UNIQUE NOT NULL,
                password  TEXT NOT NULL DEFAULT '',
                name      TEXT,
                picture   TEXT,
                google_id TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS query_history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                query         TEXT NOT NULL,
                database_type TEXT,
                executed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()
        # Run migrations for databases created before this schema version
        _migrate(conn)
        conn.close()
        logger.info("Database ready at %s", DB_PATH)
    except Exception as exc:
        logger.error("Error initialising database: %s", exc)
