import sqlite3

DB = "database/users.db"

def create_user(email, password):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users(email,password) VALUES (?,?)",
            (email, password)
        )
        conn.commit()
        return True

    except:
        return False

    finally:
        conn.close()


def login_user(email, password):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    )

    user = cur.fetchone()

    conn.close()

    return user
