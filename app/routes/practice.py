"""Practice mode blueprint.

Routes:
  GET  /practice/<db_type>                        → difficulty selector
  GET  /practice/<db_type>/<difficulty>            → first question (or resume)
  GET  /practice/<db_type>/<difficulty>/<int:qid>  → specific question
  POST /practice/<db_type>/<difficulty>/<int:qid>/run  → run query & record progress
  GET  /practice/<db_type>/<difficulty>/complete   → completion screen
"""
import logging
import sqlite3
import time

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.services.db_admin_service import get_user_db_info
from app.services.question_service import (
    get_difficulty_info,
    get_question,
    get_questions,
    get_supported_difficulties,
)
from app.services.progress_service import (
    get_progress,
    mark_question_complete,
    reset_progress,
)
from app.utils.db_init import DB_PATH

practice_bp = Blueprint("practice", __name__)
logger = logging.getLogger(__name__)

_VALID_DB_TYPES = {"mysql", "postgres"}
_VALID_DIFFICULTIES = {"beginner", "moderate", "master"}


def _require_auth():
    if "user_id" not in session:
        return redirect("/login")
    return None


def _run_sandbox_query(db_info: dict, query: str) -> dict:
    """Execute *query* against the user's sandbox and return result dict."""
    db_type = db_info.get("db_type", "mysql")
    try:
        if db_type == "mysql":
            import mysql.connector  # type: ignore
            conn = mysql.connector.connect(
                host=db_info["db_host"],
                port=db_info["db_port"],
                user=db_info["db_user"],
                password=db_info["db_password"],
                database=db_info["db_name"],
                connection_timeout=10,
            )
            cursor = conn.cursor()
            cursor.execute(query)
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                result = {"columns": columns, "rows": [list(r) for r in rows]}
            else:
                conn.commit()
                affected = cursor.rowcount
                result = {"message": f"Query executed successfully. Rows affected: {affected}"}
            cursor.close()
            conn.close()
            return result
        else:  # postgres
            import psycopg2  # type: ignore
            conn = psycopg2.connect(
                host=db_info["db_host"],
                port=db_info["db_port"],
                user=db_info["db_user"],
                password=db_info["db_password"],
                database=db_info["db_name"],
                connect_timeout=10,
            )
            cursor = conn.cursor()
            cursor.execute(query)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                result = {"columns": columns, "rows": [list(r) for r in rows]}
            else:
                conn.commit()
                affected = cursor.rowcount
                result = {"message": f"Query executed successfully. Rows affected: {affected}"}
            cursor.close()
            conn.close()
            return result
    except Exception as exc:
        logger.error("Practice sandbox query error (%s): %s", db_type, exc)
        return {"error": str(exc)}


def _save_history(user_id, query, db_type, elapsed, success, error_message=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """INSERT INTO query_history
               (user_id, query, database_type, execution_time, success, error_message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, query, db_type, elapsed, int(success), error_message),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("Failed to save practice query history: %s", exc)


def _load_history(user_id, limit=10):
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT query, database_type, execution_time, success "
            "FROM query_history WHERE user_id = ? ORDER BY executed_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        conn.close()
        return [
            {"query": r[0], "db_type": r[1], "execution_time": r[2], "success": bool(r[3])}
            for r in rows
        ]
    except Exception as exc:
        logger.error("Failed to load practice query history: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@practice_bp.route("/practice/<db_type>")
def select_difficulty(db_type):
    """Difficulty selector page."""
    redir = _require_auth()
    if redir:
        return redir

    if db_type not in _VALID_DB_TYPES:
        return redirect(url_for("dashboard.dashboard"))

    user_id = session["user_id"]
    sandbox_db = get_user_db_info(user_id, db_type)
    if sandbox_db is None:
        return redirect(url_for("dashboard.dashboard"))

    difficulties = get_supported_difficulties(db_type)
    diff_data = []
    for d in difficulties:
        questions = get_questions(db_type, d)
        progress = get_progress(user_id, db_type, d)
        completed_count = len(progress["completed_ids"])
        total = len(questions)
        info = get_difficulty_info(d)
        diff_data.append({
            "key": d,
            "label": info["label"],
            "emoji": info["emoji"],
            "color": info["color"],
            "total": total,
            "completed": completed_count,
            "current_question": progress["current_question"],
            "is_complete": completed_count >= total,
        })

    return render_template(
        "practice_select.html",
        db_type=db_type,
        db_name=sandbox_db["db_name"],
        difficulties=diff_data,
    )


@practice_bp.route("/practice/<db_type>/<difficulty>")
def practice_start(db_type, difficulty):
    """Redirect to the user's current question (resume or start)."""
    redir = _require_auth()
    if redir:
        return redir

    if db_type not in _VALID_DB_TYPES or difficulty not in _VALID_DIFFICULTIES:
        return redirect(url_for("dashboard.dashboard"))

    user_id = session["user_id"]
    sandbox_db = get_user_db_info(user_id, db_type)
    if sandbox_db is None:
        return redirect(url_for("dashboard.dashboard"))

    questions = get_questions(db_type, difficulty)
    if not questions:
        return redirect(url_for("practice.select_difficulty", db_type=db_type))

    progress = get_progress(user_id, db_type, difficulty)

    # If all questions complete, go to completion screen
    if len(progress["completed_ids"]) >= len(questions):
        return redirect(url_for("practice.practice_complete", db_type=db_type, difficulty=difficulty))

    return redirect(url_for(
        "practice.practice_question",
        db_type=db_type,
        difficulty=difficulty,
        qid=progress["current_question"],
    ))


@practice_bp.route("/practice/<db_type>/<difficulty>/<int:qid>", methods=["GET"])
def practice_question(db_type, difficulty, qid):
    """Render the practice question page."""
    redir = _require_auth()
    if redir:
        return redir

    if db_type not in _VALID_DB_TYPES or difficulty not in _VALID_DIFFICULTIES:
        return redirect(url_for("dashboard.dashboard"))

    user_id = session["user_id"]
    sandbox_db = get_user_db_info(user_id, db_type)
    if sandbox_db is None:
        return redirect(url_for("dashboard.dashboard"))

    questions = get_questions(db_type, difficulty)
    if not questions:
        return redirect(url_for("practice.select_difficulty", db_type=db_type))

    # Clamp qid to valid range
    if qid < 1:
        qid = 1
    if qid > len(questions):
        return redirect(url_for("practice.practice_complete", db_type=db_type, difficulty=difficulty))

    question = get_question(db_type, difficulty, qid)
    if question is None:
        return redirect(url_for("practice.select_difficulty", db_type=db_type))

    progress = get_progress(user_id, db_type, difficulty)
    completed_ids = progress["completed_ids"]
    diff_info = get_difficulty_info(difficulty)
    history = _load_history(user_id)

    return render_template(
        "practice_question.html",
        db_type=db_type,
        db_name=sandbox_db["db_name"],
        difficulty=difficulty,
        diff_info=diff_info,
        question=question,
        question_num=qid,
        total_questions=len(questions),
        completed_ids=completed_ids,
        is_completed=qid in completed_ids,
        history=history,
        result=None,
        last_query="",
    )


@practice_bp.route("/practice/<db_type>/<difficulty>/<int:qid>/run", methods=["POST"])
def practice_run(db_type, difficulty, qid):
    """Run the submitted query and return JSON results."""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    if db_type not in _VALID_DB_TYPES or difficulty not in _VALID_DIFFICULTIES:
        return jsonify({"error": "Invalid db_type or difficulty"}), 400

    user_id = session["user_id"]
    sandbox_db = get_user_db_info(user_id, db_type)
    if sandbox_db is None:
        return jsonify({"error": "Sandbox database not found"}), 404

    questions = get_questions(db_type, difficulty)
    question = get_question(db_type, difficulty, qid)
    if question is None:
        return jsonify({"error": "Question not found"}), 404

    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400

    start = time.time()
    raw_result = _run_sandbox_query(sandbox_db, query)
    elapsed = round(time.time() - start, 3)

    has_error = bool(raw_result.get("error"))
    _save_history(user_id, query, db_type, elapsed, not has_error,
                  raw_result.get("error") if has_error else None)

    if not has_error:
        # Mark question complete and advance progress
        progress = mark_question_complete(user_id, db_type, difficulty, qid, len(questions))
        raw_result["execution_time"] = elapsed
        raw_result["congratulations"] = True
        raw_result["next_question"] = progress["current_question"]
        raw_result["completed_ids"] = progress["completed_ids"]
        raw_result["all_complete"] = len(progress["completed_ids"]) >= len(questions)

        # Serialize rows to plain lists (tuples not JSON serialisable)
        if "rows" in raw_result:
            raw_result["rows"] = [list(r) for r in raw_result["rows"]]

    return jsonify(raw_result)


@practice_bp.route("/practice/<db_type>/<difficulty>/complete")
def practice_complete(db_type, difficulty):
    """Completion / certificate screen."""
    redir = _require_auth()
    if redir:
        return redir

    if db_type not in _VALID_DB_TYPES or difficulty not in _VALID_DIFFICULTIES:
        return redirect(url_for("dashboard.dashboard"))

    user_id = session["user_id"]
    sandbox_db = get_user_db_info(user_id, db_type)
    if sandbox_db is None:
        return redirect(url_for("dashboard.dashboard"))

    questions = get_questions(db_type, difficulty)
    progress = get_progress(user_id, db_type, difficulty)
    diff_info = get_difficulty_info(difficulty)

    # Determine next difficulty
    difficulties_order = ["beginner", "moderate", "master"]
    current_idx = difficulties_order.index(difficulty) if difficulty in difficulties_order else -1
    next_difficulty = None
    if current_idx >= 0 and current_idx + 1 < len(difficulties_order):
        next_difficulty = difficulties_order[current_idx + 1]

    return render_template(
        "practice_complete.html",
        db_type=db_type,
        db_name=sandbox_db["db_name"],
        difficulty=difficulty,
        diff_info=diff_info,
        total_questions=len(questions),
        completed_count=len(progress["completed_ids"]),
        next_difficulty=next_difficulty,
    )


@practice_bp.route("/practice/<db_type>/<difficulty>/reset", methods=["POST"])
def practice_reset(db_type, difficulty):
    """Reset progress for a difficulty level."""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    if db_type not in _VALID_DB_TYPES or difficulty not in _VALID_DIFFICULTIES:
        return jsonify({"error": "Invalid parameters"}), 400

    user_id = session["user_id"]
    reset_progress(user_id, db_type, difficulty)
    return jsonify({"success": True})
