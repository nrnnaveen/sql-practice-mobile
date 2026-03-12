from flask import Blueprint, jsonify, redirect, render_template, request, session

from app.services.auth_service import get_user_by_id
from app.services.db_admin_service import (
    create_user_database,
    get_user_db_info,
    is_username_available,
)

dashboard_bp = Blueprint("dashboard", __name__)


def _get_display_name(user, login_type):
    """Derive a greeting name from profile data or email."""
    name = user.get("name") or ""
    parts = name.split()
    if parts:
        # Use first word of full name (e.g. "John Doe" → "John")
        return parts[0]
    # Fall back: extract part before @ from email
    email = user.get("email", "")
    local = email.split("@")[0] if "@" in email else email
    return local.capitalize() if local else "there"


@dashboard_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user = get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return redirect("/login")

    login_type = session.get("login_type", "email")
    display_name = _get_display_name(user, login_type)

    # Smart detection: check if user already has a sandbox database
    db_info = get_user_db_info(session["user_id"])

    return render_template(
        "dashboard.html",
        user=user,
        display_name=display_name,
        login_type=login_type,
        db_info=db_info,  # None → show create form; dict → show existing DB info
    )


@dashboard_bp.route("/api/check-username")
def check_username():
    """Return whether a custom DB username is available."""
    if "user_id" not in session:
        return jsonify({"available": False, "error": "Not authenticated"}), 401
    username = request.args.get("username", "").strip()
    db_type = request.args.get("db_type", "mysql").strip()
    if not username:
        return jsonify({"available": False, "error": "Username is required"})
    available = is_username_available(db_type, username)
    return jsonify({"available": available})


@dashboard_bp.route("/api/create-database", methods=["POST"])
def create_database():
    """Create a per-user sandbox database (one-time operation)."""
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    user_id = session["user_id"]

    # Prevent duplicate creation
    if get_user_db_info(user_id) is not None:
        return jsonify({"success": False, "error": "You already have a database."}), 409

    data = request.get_json(silent=True) or {}
    db_type = data.get("db_type", "mysql").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required."}), 400

    try:
        info = create_user_database(user_id, db_type, username, password)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify({"success": True, "db_info": info})

