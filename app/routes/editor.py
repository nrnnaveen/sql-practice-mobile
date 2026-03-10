from flask import Blueprint, render_template, request, redirect, session
from app.services.mysql_service import run_mysql, get_mysql_tables
from app.services.postgres_service import run_postgres, get_postgres_tables

editor_bp = Blueprint('editor', __name__)


@editor_bp.route("/editor", methods=["GET", "POST"])
def editor():
    if "user" not in session:
        return redirect("/login")

    result = None
    if "history" not in session:
        session["history"] = []

    if request.method == "POST":
        db = request.form["database"]
        query = request.form["query"]
        history = session["history"]
        history.insert(0, query)
        session["history"] = history[:10]

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
