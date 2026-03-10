from flask import Blueprint, redirect, render_template, request, session

from app.services.auth_service import create_user, login_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def home():
    return redirect("/login")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if create_user(email, password):
            return redirect("/login")
        error = "Could not create account. The email address may already be registered."
    return render_template("signup.html", error=error)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if login_user(email, password):
            session["user"] = email
            return redirect("/dashboard")
        error = "Invalid email or password."
    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
