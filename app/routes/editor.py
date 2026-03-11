import sqlite3
import logging

from flask import Blueprint, redirect, render_template, request, session

from app.services.query_service import execute_query
from app.utils.db_init import DB_PATH
from app.utils.decorators import rate_limit

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
@rate_limit(max_requests=10, window_seconds=60)
def editor(**kwargs):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    result = None
    last_query = ""
    selected_db = "mysql"

    # Rate limit exceeded – show error without running the query
    if kwargs.get("_rate_limited"):
        result = {"error": "Rate limit exceeded: max 10 queries per minute. Please wait."}

    elif request.method == "POST":
        selected_db = request.form.get("database", "mysql")
        query = request.form.get("query", "").strip()
        last_query = query
        page = int(request.form.get("page", 1))

        if query:
            result = execute_query(query, selected_db, page=page)
            # Only save to history when the query was accepted (no validation error)
            if "error" not in result:
                _save_history(user_id, query, selected_db)

    history = _load_history(user_id)

    return render_template(
        "editor.html",
        result=result,
        history=history,
        last_query=last_query,
        selected_db=selected_db,
    )
