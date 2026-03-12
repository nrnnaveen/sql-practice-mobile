import csv
import io
import json
import sqlite3
import time
import logging

from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
)

from app.services.mysql_service import run_mysql
from app.services.postgres_service import run_postgres
from app.services.db_admin_service import get_user_db_info
from app.utils.db_init import DB_PATH
from app.utils.validators import validate_query
from app.utils.decorators import rate_limit

editor_bp = Blueprint("editor", __name__)
logger = logging.getLogger(__name__)

# Maximum rows returned to the browser per page by default
DEFAULT_RESULTS_PER_PAGE = 100


def _save_history(user_id, query, db_type, execution_time=None, success=True, error_message=None):
    """Persist a query to the query_history table for the given user."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """INSERT INTO query_history
               (user_id, query, database_type, execution_time, success, error_message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, query, db_type, execution_time, int(success), error_message),
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
            "SELECT query, database_type, execution_time, success "
            "FROM query_history "
            "WHERE user_id = ? ORDER BY executed_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        conn.close()
        return [
            {"query": r[0], "db_type": r[1], "execution_time": r[2], "success": bool(r[3])}
            for r in rows
        ]
    except Exception as exc:
        logger.error("Failed to load query history: %s", exc)
        return []


def _get_user_settings(user_id):
    """Return user settings dict with defaults if not found."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception as exc:
        logger.error("Failed to load user settings: %s", exc)
    return {"theme": "dark", "default_database": "mysql", "results_per_page": DEFAULT_RESULTS_PER_PAGE}


def _run_sandbox_query(db_info: dict, query: str) -> dict:
    """Execute *query* against the user's personal sandbox database.

    Supports MySQL and PostgreSQL.  No SQL restrictions apply – the user has
    full privileges on their own database.
    """
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
                result = {"columns": columns, "rows": rows}
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
                result = {"columns": columns, "rows": rows}
            else:
                conn.commit()
                affected = cursor.rowcount
                result = {"message": f"Query executed successfully. Rows affected: {affected}"}
            cursor.close()
            conn.close()
            return result
    except Exception as exc:
        logger.error("Sandbox query error (%s): %s", db_type, exc)
        return {"error": str(exc)}


def _run_editor(db_type_filter: str = None):
    """Shared logic for all editor routes.

    If *db_type_filter* is 'mysql' or 'postgres', the editor is locked to the
    user's sandbox database of that type (or redirects to dashboard if not
    created yet).  If ``None``, the original single-DB behaviour is used.
    """
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    result = None
    last_query = ""
    settings = _get_user_settings(user_id)
    page = 1
    total_rows = 0
    has_more = False

    # Determine the sandbox DB to use
    if db_type_filter:
        sandbox_db = get_user_db_info(user_id, db_type_filter)
        if sandbox_db is None:
            # User hasn't created this type of DB yet – send them to dashboard
            return redirect("/dashboard")
        selected_db = db_type_filter
    else:
        sandbox_db = get_user_db_info(user_id)
        selected_db = sandbox_db["db_type"] if sandbox_db else settings.get("default_database", "mysql")

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        last_query = query
        page = int(request.form.get("page", 1))
        per_page = int(settings.get("results_per_page", DEFAULT_RESULTS_PER_PAGE))

        if not sandbox_db and not db_type_filter:
            selected_db = request.form.get("database", selected_db)

        if query:
            if sandbox_db:
                # Sandbox mode: the user has their own isolated database, so all SQL
                # commands (INSERT, UPDATE, DELETE, DROP, CREATE, …) are allowed.
                # There is no shared data at risk – queries run only against the user's
                # personal sandbox that was provisioned exclusively for them.
                start_time = time.time()
                raw_result = _run_sandbox_query(sandbox_db, query)
                elapsed = round(time.time() - start_time, 3)
            else:
                # Shared mode: enforce read-only restrictions
                is_valid, validation_error = validate_query(query)
                if not is_valid:
                    result = {"error": validation_error}
                    _save_history(user_id, query, selected_db, success=False, error_message=validation_error)
                    raw_result = None
                    elapsed = 0.0
                else:
                    start_time = time.time()
                    if selected_db == "mysql":
                        raw_result = run_mysql(query)
                    elif selected_db == "postgres":
                        raw_result = run_postgres(query)
                    else:
                        raw_result = {"error": "Unknown database type."}
                    elapsed = round(time.time() - start_time, 3)

            if raw_result is not None:
                error_msg = raw_result.get("error") if raw_result else None
                _save_history(
                    user_id, query, selected_db,
                    execution_time=elapsed,
                    success=(error_msg is None),
                    error_message=error_msg,
                )

                # Paginate rows
                if raw_result and raw_result.get("rows"):
                    all_rows = raw_result["rows"]
                    total_rows = len(all_rows)
                    start = (page - 1) * per_page
                    end = start + per_page
                    raw_result["rows"] = all_rows[start:end]
                    has_more = end < total_rows

                result = raw_result
                if result and not result.get("error"):
                    result["execution_time"] = elapsed

    history = _load_history(user_id)

    return render_template(
        "editor.html",
        result=result,
        history=history,
        last_query=last_query,
        selected_db=selected_db,
        sandbox_db=sandbox_db,
        db_type_filter=db_type_filter,
        theme=settings.get("theme", "dark"),
        page=page,
        total_rows=total_rows,
        has_more=has_more,
        results_per_page=int(settings.get("results_per_page", DEFAULT_RESULTS_PER_PAGE)),
    )


@editor_bp.route("/editor", methods=["GET", "POST"])
@rate_limit
def editor():
    return _run_editor(db_type_filter=None)


@editor_bp.route("/editor/mysql", methods=["GET", "POST"])
@rate_limit
def editor_mysql():
    """MySQL-specific sandbox editor."""
    return _run_editor(db_type_filter="mysql")


@editor_bp.route("/editor/postgresql", methods=["GET", "POST"])
@rate_limit
def editor_postgresql():
    """PostgreSQL-specific sandbox editor."""
    return _run_editor(db_type_filter="postgres")


@editor_bp.route("/editor/export", methods=["POST"])
@rate_limit
def export_results():
    """Export the current query results as CSV or JSON."""
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    export_format = request.form.get("format", "csv").lower()
    query = request.form.get("query", "").strip()
    selected_db = request.form.get("database", "mysql")

    if not query:
        return jsonify({"error": "No query provided."}), 400

    sandbox_db = get_user_db_info(user_id, selected_db) or get_user_db_info(user_id)
    if sandbox_db:
        raw_result = _run_sandbox_query(sandbox_db, query)
    else:
        is_valid, validation_error = validate_query(query)
        if not is_valid:
            return jsonify({"error": validation_error}), 400

        if selected_db == "mysql":
            raw_result = run_mysql(query)
        elif selected_db == "postgres":
            raw_result = run_postgres(query)
        else:
            return jsonify({"error": "Unknown database type."}), 400

    if raw_result.get("error"):
        return jsonify({"error": raw_result["error"]}), 400

    columns = raw_result.get("columns", [])
    rows = raw_result.get("rows", [])

    if export_format == "json":
        data = [dict(zip(columns, row)) for row in rows]
        return Response(
            json.dumps(data, indent=2, default=str),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=results.json"},
        )
    else:  # default CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=results.csv"},
        )

