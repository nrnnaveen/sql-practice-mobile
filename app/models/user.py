import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = "database/users.db"


def create_user(email, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        hashed = generate_password_hash(password)
        cur.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def login_user(email, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE email=?", (email,))
        row = cur.fetchone()
        conn.close()
        if row and check_password_hash(row[0], password):
            return True
        return False
    except Exception:
        return False
