import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB="database/users.db"

def create_user(email,password):

    conn=sqlite3.connect(DB)
    cur=conn.cursor()

    cur.execute(
    "INSERT INTO users(email,password) VALUES (?,?)",
    (email,generate_password_hash(password))
    )

    conn.commit()
    conn.close()


def check_login(email,password):

    conn=sqlite3.connect(DB)
    cur=conn.cursor()

    cur.execute("SELECT password FROM users WHERE email=?",(email,))
    user=cur.fetchone()

    conn.close()

    if user and check_password_hash(user[0],password):
        return True

    return False
