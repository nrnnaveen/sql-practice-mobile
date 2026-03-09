from flask import Flask, render_template, request, redirect, session
from auth import create_user, login_user
from mysql_engine import run_mysql
from postgres_engine import run_postgres
from config import SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY


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

    result = None

    if request.method == "POST":

        db = request.form["database"]
        query = request.form["query"]

        if db == "mysql":
            result = run_mysql(query)

        elif db == "postgres":
            result = run_postgres(query)

    return render_template("editor.html", result=result)


@app.route("/logout")
def logout():

    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
