import sqlite3
import logging

from werkzeug.security import check_password_hash, generate_password_hash

from app.utils.db_init import DB_PATH
from app.utils.validators import validate_password_strength

logger = logging.getLogger(__name__)


def create_user(email, password):
    """Insert a new user into the database. Returns True on success."""
    valid, msg = validate_password_strength(password)
    if not valid:
        logger.warning("Password policy violation for %s: %s", email, msg)
        return False, msg
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cur = conn.cursor()
        hashed = generate_password_hash(password, method="pbkdf2:sha256")
        cur.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed)
        )
        conn.commit()
        logger.info("Created user: %s", email)
        return True, ""
    except Exception as exc:
        logger.error("Error creating user %s: %s", email, exc)
        return False, "Could not create account. The email address may already be registered."
    finally:
        if conn:
            conn.close()


def login_user(email, password):
    """Verify credentials. Returns the user ID (int) on success, or None on failure."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, password FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        conn.close()
        if row and row[1] and check_password_hash(row[1], password):
            return row[0]
        return None
    except Exception as exc:
        logger.error("Error during login for %s: %s", email, exc)
        return None


def get_user_by_id(user_id):
    """Return a dict with user info for the given ID, or None if not found."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, name, picture, google_id FROM users WHERE id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None
    except Exception as exc:
        logger.error("Error fetching user %s: %s", user_id, exc)
        return None


def get_or_create_google_user(email, name, picture, google_id):
    """
    Find an existing user by google_id or email, update their Google profile
    data, and return their user ID.  Creates a new row if no match is found.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # 1) Look up by google_id first
        cur.execute("SELECT id FROM users WHERE google_id = ?", (google_id,))
        row = cur.fetchone()

        if row:
            user_id = row[0]
            cur.execute(
                "UPDATE users SET name = ?, picture = ? WHERE id = ?",
                (name, picture, user_id),
            )
        else:
            # 2) Fall back to matching by email (e.g. existing email/password account)
            cur.execute("SELECT id FROM users WHERE email = ?", (email,))
            row = cur.fetchone()
            if row:
                user_id = row[0]
                cur.execute(
                    "UPDATE users SET name = ?, picture = ?, google_id = ? WHERE id = ?",
                    (name, picture, google_id, user_id),
                )
            else:
                # 3) Brand-new Google user – password placeholder is empty string
                cur.execute(
                    "INSERT INTO users (email, password, name, picture, google_id) "
                    "VALUES (?, '', ?, ?, ?)",
                    (email, name, picture, google_id),
                )
                user_id = cur.lastrowid
                logger.info("Created Google user: %s", email)

        conn.commit()
        conn.close()
        return user_id
    except Exception as exc:
        logger.error("Error in get_or_create_google_user for %s: %s", email, exc)
        return None


def update_user_profile(user_id, name=None, picture=None):
    """Update display name and/or profile picture for a user."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if name is not None and picture is not None:
            cur.execute(
                "UPDATE users SET name = ?, picture = ? WHERE id = ?",
                (name, picture, user_id),
            )
        elif name is not None:
            cur.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
        elif picture is not None:
            cur.execute("UPDATE users SET picture = ? WHERE id = ?", (picture, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.error("Error updating profile for user %s: %s", user_id, exc)
        return False


def get_user_settings(user_id):
    """Return settings dict for the user, creating default row if absent."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.execute(
                "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,)
            )
            conn.commit()
            cur.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
        conn.close()
        return dict(row) if row else {"theme": "dark", "default_database": "mysql", "results_per_page": 100}
    except Exception as exc:
        logger.error("Error fetching settings for user %s: %s", user_id, exc)
        return {"theme": "dark", "default_database": "mysql", "results_per_page": 100}


def update_user_settings(user_id, theme=None, default_database=None, results_per_page=None):
    """Upsert user settings."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,)
        )
        if theme is not None:
            cur.execute("UPDATE user_settings SET theme = ? WHERE user_id = ?", (theme, user_id))
        if default_database is not None:
            cur.execute(
                "UPDATE user_settings SET default_database = ? WHERE user_id = ?",
                (default_database, user_id),
            )
        if results_per_page is not None:
            cur.execute(
                "UPDATE user_settings SET results_per_page = ? WHERE user_id = ?",
                (int(results_per_page), user_id),
            )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.error("Error updating settings for user %s: %s", user_id, exc)
        return False
