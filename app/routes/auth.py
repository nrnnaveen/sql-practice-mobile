from flask import Blueprint, render_template, request, redirect, session
from app.services.auth_service import create_user, login_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/")
def home():
    return redirect("/login")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if create_user(email, password):
            return redirect("/login")
    return render_template("auth/signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if login_user(email, password):
            session["user"] = email
            return redirect("/dashboard")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
