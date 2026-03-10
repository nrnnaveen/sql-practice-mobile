from flask import Blueprint, render_template, redirect, session

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")
