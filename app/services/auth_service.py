import sqlite3
import logging

from werkzeug.security import check_password_hash, generate_password_hash

from app.utils.db_init import DB_PATH

logger = logging.getLogger(__name__)


def create_user(email, password):
    """Insert a new user into the database. Returns True on success."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        hashed = generate_password_hash(password, method="pbkdf2:sha256")
        cur.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed)
        )
        conn.commit()
        conn.close()
        logger.info("Created user: %s", email)
        return True
    except Exception as exc:
        logger.error("Error creating user %s: %s", email, exc)
        return False


def login_user(email, password):
    """Verify credentials. Returns True if the email/password pair is valid."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        conn.close()
        if row and check_password_hash(row[0], password):
            return True
        return False
    except Exception as exc:
        logger.error("Error during login for %s: %s", email, exc)
        return False
