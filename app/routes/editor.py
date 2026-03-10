import sqlite3
import logging

from flask import Blueprint, redirect, render_template, request, session

from app.services.mysql_service import run_mysql
from app.services.postgres_service import run_postgres
from app.utils.db_init import DB_PATH

editor_bp = Blueprint("editor", __name__)
logger = logging.getLogger(__name__)


def _save_history(user_id, query, db_type):
    """Persist a query to the query_history table for the given user."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO query_history (user_id, query, database_type) VALUES (?, ?, ?)",
            (user_id, query, db_type),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("Failed to save query history: %s", exc)


def _load_history(user_id, limit=20):
    """Return the most recent queries for a user, newest first."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT query, database_type FROM query_history "
            "WHERE user_id = ? ORDER BY executed_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        conn.close()
        return [{"query": r[0], "db_type": r[1]} for r in rows]
    except Exception as exc:
        logger.error("Failed to load query history: %s", exc)
        return []


@editor_bp.route("/editor", methods=["GET", "POST"])
def editor():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    result = None
    last_query = ""
    selected_db = "mysql"

    if request.method == "POST":
        selected_db = request.form.get("database", "mysql")
        query = request.form.get("query", "").strip()
        last_query = query
        if query:
            _save_history(user_id, query, selected_db)
        if selected_db == "mysql":
            result = run_mysql(query)
        elif selected_db == "postgres":
            result = run_postgres(query)

    history = _load_history(user_id)

    return render_template(
        "editor.html",
        result=result,
        history=history,
        last_query=last_query,
        selected_db=selected_db,
    )
