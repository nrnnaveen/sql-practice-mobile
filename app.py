from flask import Flask, render_template, request, redirect, session
from auth import create_user, login_user
from mysql_engine import run_mysql, get_mysql_tables
from postgres_engine import run_postgres, get_postgres_tables
from config import SECRET_KEY
import sqlite3
import os

app = Flask(__name__)
app.secret_key = SECRET_KEY

# -----------------------------
# Create database automatically
# -----------------------------
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
    print("Users database created")

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return redirect("/login")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if create_user(email, password):
            return redirect("/login")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = login_user(email, password)
        if user:
            session["user"] = email
            return redirect("/dashboard")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

@app.route("/editor", methods=["GET", "POST"])
def editor():
    if "user" not in session:
        return redirect("/login")

    result = None

    # initialize query history
    if "history" not in session:
        session["history"] = []

    if request.method == "POST":
        db = request.form["database"]
        query = request.form["query"]

        # save query to history
        history = session["history"]
        history.insert(0, query)
        session["history"] = history[:10]  # last 10 queries

        if db == "mysql":
            result = run_mysql(query)
        elif db == "postgres":
            result = run_postgres(query)

    return render_template(
        "editor.html",
        result=result,
        history=session.get("history", []),
        get_mysql_tables=get_mysql_tables,
        get_postgres_tables=get_postgres_tables
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
