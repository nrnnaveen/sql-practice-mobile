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

    # ── users table ─────────────────────────────────────────────────────────
    existing_users = {row[1] for row in cur.execute("PRAGMA table_info(users)")}
    user_columns = [
        ("name", "TEXT"),
        ("picture", "TEXT"),
        ("google_id", "TEXT"),
    ]
    _allowed_user_cols = {"name", "picture", "google_id"}
    _allowed_types = {"TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"}
    for col, col_type in user_columns:
        if col not in existing_users:
            if col not in _allowed_user_cols or col_type not in _allowed_types:
                logger.error("Refusing to migrate unknown column %s %s", col, col_type)
                continue
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
            logger.info("Migrated users table: added column %s", col)

    # ── query_history table ──────────────────────────────────────────────────
    existing_qh = {row[1] for row in cur.execute("PRAGMA table_info(query_history)")}
    qh_columns = [
        ("execution_time", "REAL"),
        ("success", "INTEGER"),
        ("error_message", "TEXT"),
    ]
    _allowed_qh_cols = {"execution_time", "success", "error_message"}
    for col, col_type in qh_columns:
        if col not in existing_qh:
            if col not in _allowed_qh_cols or col_type not in _allowed_types:
                logger.error("Refusing to migrate unknown column %s %s", col, col_type)
                continue
            cur.execute(f"ALTER TABLE query_history ADD COLUMN {col} {col_type}")
            logger.info("Migrated query_history table: added column %s", col)

    conn.commit()


def init_db():
    """Create the SQLite database and required tables if they do not already exist."""
    try:
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
            logger.info("Created database directory: %s", DB_DIR)

        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
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
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                query          TEXT NOT NULL,
                database_type  TEXT,
                execution_time REAL,
                success        INTEGER NOT NULL DEFAULT 1,
                error_message  TEXT,
                executed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_query_history_user
            ON query_history (user_id, executed_at DESC)
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bookmarks (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                name          TEXT NOT NULL,
                query         TEXT NOT NULL,
                description   TEXT,
                database_type TEXT NOT NULL DEFAULT 'mysql',
                tags          TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id          INTEGER PRIMARY KEY,
                theme            TEXT NOT NULL DEFAULT 'dark',
                default_database TEXT NOT NULL DEFAULT 'mysql',
                results_per_page INTEGER NOT NULL DEFAULT 100,
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
