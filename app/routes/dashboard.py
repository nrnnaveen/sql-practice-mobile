from flask import Blueprint, redirect, render_template, session

from app.services.auth_service import get_user_by_id

dashboard_bp = Blueprint("dashboard", __name__)


def _get_display_name(user, login_type):
    """Derive a greeting name from profile data or email."""
    if user.get("name"):
        # Use first word of full name (e.g. "John Doe" → "John")
        return user["name"].split()[0]
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

    return render_template(
        "dashboard.html",
        user=user,
        display_name=display_name,
        login_type=login_type,
    )
