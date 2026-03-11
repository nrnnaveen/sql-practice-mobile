import logging
import re
import sqlite3

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app import oauth
from app.services.auth_service import create_user, login_user, get_or_create_google_user
from app.utils.db_init import DB_PATH

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)

# Password must be ≥8 chars and contain at least one uppercase, one lowercase,
# one digit, and one special character.
_PW_MIN_LEN = 8
_PW_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$"
)


def _validate_password(password: str) -> str | None:
    """Return an error message, or None when the password is acceptable."""
    if len(password) < _PW_MIN_LEN:
        return f"Password must be at least {_PW_MIN_LEN} characters."
    if not _PW_PATTERN.match(password):
        return (
            "Password must contain at least one uppercase letter, "
            "one lowercase letter, one digit, and one special character."
        )
    return None


@auth_bp.route("/")
def home():
    return redirect("/login")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        pw_error = _validate_password(password)
        if pw_error:
            error = pw_error
        elif create_user(email, password):
            return redirect("/login")
        else:
            error = "Could not create account. The email address may already be registered."
    return render_template("signup.html", error=error)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user_id = login_user(email, password)
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        if user_id is not None:
            session.permanent = True
            session["user_id"] = user_id
            session["login_type"] = "email"
            if is_ajax:
                return jsonify({"success": True})
            return redirect("/dashboard")
        if is_ajax:
            return jsonify({"success": False, "error": "Invalid email or password."})
        error = "Invalid email or password."
    return render_template("login.html", error=error)


@auth_bp.route("/login/google")
def login_google():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/login/google/callback")
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo") or {}
        email = userinfo.get("email", "")
        name = userinfo.get("name", "")
        picture = userinfo.get("picture", "")
        google_id = userinfo.get("sub", "")

        if not email:
            return redirect(url_for("auth.login"))

        user_id = get_or_create_google_user(email, name, picture, google_id)
        if user_id is None:
            return redirect(url_for("auth.login"))

        session.permanent = True
        session["user_id"] = user_id
        session["login_type"] = "google"
        return redirect(url_for("dashboard.dashboard"))
    except Exception as exc:
        logger.error("Google OAuth callback error: %s", exc)
        return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
def logout():
    user_id = session.get("user_id")
    if user_id is not None:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM query_history WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("Failed to clear query history on logout for user %s: %s", user_id, exc)
    session.clear()
    return redirect("/login")
