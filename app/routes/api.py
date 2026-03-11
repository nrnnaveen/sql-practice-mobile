"""REST API endpoints for bookmarks, query templates, and user settings."""
import sqlite3
import logging

from flask import Blueprint, jsonify, request, session

from app.utils.db_init import DB_PATH
from app.utils.decorators import login_required, rate_limit
from app.services.auth_service import get_user_settings, update_user_settings

api_bp = Blueprint("api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in query templates (read-only, shipped with the app)
# ---------------------------------------------------------------------------
QUERY_TEMPLATES = [
    {
        "id": 1,
        "name": "Basic SELECT",
        "description": "Select all columns from a table",
        "query": "SELECT *\nFROM table_name\nLIMIT 10;",
        "category": "basics",
    },
    {
        "id": 2,
        "name": "SELECT with WHERE",
        "description": "Filter rows using a condition",
        "query": "SELECT column1, column2\nFROM table_name\nWHERE column1 = 'value';",
        "category": "basics",
    },
    {
        "id": 3,
        "name": "ORDER BY",
        "description": "Sort results ascending or descending",
        "query": "SELECT *\nFROM table_name\nORDER BY column1 ASC\nLIMIT 20;",
        "category": "basics",
    },
    {
        "id": 4,
        "name": "INNER JOIN",
        "description": "Join two tables on a common key",
        "query": (
            "SELECT a.id, a.name, b.value\n"
            "FROM table_a a\n"
            "INNER JOIN table_b b ON a.id = b.a_id\n"
            "LIMIT 20;"
        ),
        "category": "joins",
    },
    {
        "id": 5,
        "name": "LEFT JOIN",
        "description": "Include all rows from the left table",
        "query": (
            "SELECT a.id, a.name, b.value\n"
            "FROM table_a a\n"
            "LEFT JOIN table_b b ON a.id = b.a_id\n"
            "LIMIT 20;"
        ),
        "category": "joins",
    },
    {
        "id": 6,
        "name": "GROUP BY with COUNT",
        "description": "Aggregate rows with GROUP BY",
        "query": (
            "SELECT column1, COUNT(*) AS total\n"
            "FROM table_name\n"
            "GROUP BY column1\n"
            "ORDER BY total DESC;"
        ),
        "category": "aggregation",
    },
    {
        "id": 7,
        "name": "GROUP BY with HAVING",
        "description": "Filter aggregated groups",
        "query": (
            "SELECT column1, COUNT(*) AS total\n"
            "FROM table_name\n"
            "GROUP BY column1\n"
            "HAVING total > 5\n"
            "ORDER BY total DESC;"
        ),
        "category": "aggregation",
    },
    {
        "id": 8,
        "name": "Subquery",
        "description": "Use a subquery in the WHERE clause",
        "query": (
            "SELECT *\n"
            "FROM table_name\n"
            "WHERE column1 IN (\n"
            "    SELECT column1 FROM other_table WHERE condition = 'value'\n"
            ");"
        ),
        "category": "advanced",
    },
    {
        "id": 9,
        "name": "CTE (WITH clause)",
        "description": "Define a common table expression",
        "query": (
            "WITH cte AS (\n"
            "    SELECT column1, COUNT(*) AS cnt\n"
            "    FROM table_name\n"
            "    GROUP BY column1\n"
            ")\n"
            "SELECT *\n"
            "FROM cte\n"
            "WHERE cnt > 1;"
        ),
        "category": "advanced",
    },
    {
        "id": 10,
        "name": "Window Function",
        "description": "Rank rows using a window function",
        "query": (
            "SELECT\n"
            "    column1,\n"
            "    column2,\n"
            "    ROW_NUMBER() OVER (PARTITION BY column1 ORDER BY column2 DESC) AS rn\n"
            "FROM table_name;"
        ),
        "category": "advanced",
    },
]


# ---------------------------------------------------------------------------
# Templates endpoints
# ---------------------------------------------------------------------------

@api_bp.route("/templates", methods=["GET"])
@login_required
def get_templates():
    """Return the list of built-in query templates."""
    category = request.args.get("category")
    if category:
        filtered = [t for t in QUERY_TEMPLATES if t["category"] == category]
    else:
        filtered = QUERY_TEMPLATES
    return jsonify({"templates": filtered})


# ---------------------------------------------------------------------------
# Bookmarks endpoints
# ---------------------------------------------------------------------------

@api_bp.route("/bookmarks", methods=["GET"])
@login_required
def list_bookmarks():
    """Return all bookmarks for the current user."""
    user_id = session["user_id"]
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, name, query, description, database_type, tags, created_at "
            "FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        conn.close()
        return jsonify({"bookmarks": [dict(r) for r in rows]})
    except Exception as exc:
        logger.error("Error listing bookmarks for user %s: %s", user_id, exc)
        return jsonify({"error": "Failed to retrieve bookmarks."}), 500


@api_bp.route("/bookmarks", methods=["POST"])
@login_required
@rate_limit
def create_bookmark():
    """Save a new bookmark for the current user."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    query = (data.get("query") or "").strip()
    description = (data.get("description") or "").strip()
    database_type = (data.get("database_type") or "mysql").strip()
    tags = (data.get("tags") or "").strip()

    if not name:
        return jsonify({"error": "Bookmark name is required."}), 400
    if not query:
        return jsonify({"error": "Query is required."}), 400
    if database_type not in ("mysql", "postgres"):
        return jsonify({"error": "Invalid database type."}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO bookmarks (user_id, name, query, description, database_type, tags)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, name, query, description, database_type, tags),
        )
        conn.commit()
        bookmark_id = cur.lastrowid
        conn.close()
        logger.info("User %s created bookmark %s", user_id, bookmark_id)
        return jsonify({"success": True, "id": bookmark_id}), 201
    except Exception as exc:
        logger.error("Error creating bookmark for user %s: %s", user_id, exc)
        return jsonify({"error": "Failed to save bookmark."}), 500


@api_bp.route("/bookmarks/<int:bookmark_id>", methods=["DELETE"])
@login_required
def delete_bookmark(bookmark_id):
    """Delete a bookmark owned by the current user."""
    user_id = session["user_id"]
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM bookmarks WHERE id = ? AND user_id = ?",
            (bookmark_id, user_id),
        )
        conn.commit()
        deleted = cur.rowcount
        conn.close()
        if not deleted:
            return jsonify({"error": "Bookmark not found."}), 404
        return jsonify({"success": True})
    except Exception as exc:
        logger.error("Error deleting bookmark %s for user %s: %s", bookmark_id, user_id, exc)
        return jsonify({"error": "Failed to delete bookmark."}), 500


# ---------------------------------------------------------------------------
# User settings endpoint
# ---------------------------------------------------------------------------

@api_bp.route("/settings", methods=["GET"])
@login_required
def get_settings():
    """Return the current user's settings."""
    user_id = session["user_id"]
    settings = get_user_settings(user_id)
    return jsonify({"settings": settings})


@api_bp.route("/settings", methods=["POST"])
@login_required
def save_settings():
    """Update the current user's settings."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    theme = data.get("theme")
    default_database = data.get("default_database")
    results_per_page = data.get("results_per_page")

    allowed_themes = ("dark", "light")
    allowed_dbs = ("mysql", "postgres")

    if theme is not None and theme not in allowed_themes:
        return jsonify({"error": f"Theme must be one of: {allowed_themes}"}), 400
    if default_database is not None and default_database not in allowed_dbs:
        return jsonify({"error": f"Database must be one of: {allowed_dbs}"}), 400
    if results_per_page is not None:
        try:
            rpp = int(results_per_page)
            if not (10 <= rpp <= 500):
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"error": "results_per_page must be an integer between 10 and 500."}), 400

    update_user_settings(
        user_id,
        theme=theme,
        default_database=default_database,
        results_per_page=results_per_page,
    )
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@api_bp.route("/health", methods=["GET"])
def health():
    """Basic health check endpoint."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
        db_status = "ok"
    except Exception:
        db_status = "error"
    return jsonify({"status": "ok", "db": db_status})
