"""
REST API endpoints.

/api/health       – application health check (GET)
/api/export       – export last query result as CSV or JSON (POST)
/api/bookmarks    – list (GET) / add (POST) / delete (DELETE) bookmarks
/api/templates    – SQL template library (GET)
"""

import csv
import io
import json
import logging
import sqlite3

from flask import Blueprint, Response, jsonify, request, session

from app.services.cache_service import cache_stats
from app.utils.db_init import DB_PATH
from app.utils.decorators import login_required

api_bp = Blueprint("api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Query Templates  (pre-made SQL examples for learning)
# ---------------------------------------------------------------------------
_TEMPLATES = [
    {
        "id": 1,
        "title": "Select all rows",
        "sql": "SELECT * FROM your_table;",
        "category": "basics",
    },
    {
        "id": 2,
        "title": "Filter with WHERE",
        "sql": "SELECT * FROM your_table WHERE column = 'value';",
        "category": "basics",
    },
    {
        "id": 3,
        "title": "Count rows",
        "sql": "SELECT COUNT(*) AS total FROM your_table;",
        "category": "aggregation",
    },
    {
        "id": 4,
        "title": "Group and aggregate",
        "sql": "SELECT column, COUNT(*) AS cnt\nFROM your_table\nGROUP BY column\nORDER BY cnt DESC;",
        "category": "aggregation",
    },
    {
        "id": 5,
        "title": "JOIN two tables",
        "sql": (
            "SELECT a.id, a.name, b.value\n"
            "FROM table_a AS a\n"
            "INNER JOIN table_b AS b ON a.id = b.a_id;"
        ),
        "category": "joins",
    },
    {
        "id": 6,
        "title": "LEFT JOIN (include non-matching rows)",
        "sql": (
            "SELECT a.id, a.name, b.value\n"
            "FROM table_a AS a\n"
            "LEFT JOIN table_b AS b ON a.id = b.a_id;"
        ),
        "category": "joins",
    },
    {
        "id": 7,
        "title": "Subquery",
        "sql": (
            "SELECT *\n"
            "FROM your_table\n"
            "WHERE id IN (\n"
            "    SELECT id FROM other_table WHERE condition = 1\n"
            ");"
        ),
        "category": "advanced",
    },
    {
        "id": 8,
        "title": "Window function (row number)",
        "sql": (
            "SELECT *, ROW_NUMBER() OVER (PARTITION BY group_col ORDER BY sort_col) AS rn\n"
            "FROM your_table;"
        ),
        "category": "advanced",
    },
    {
        "id": 9,
        "title": "Create a table",
        "sql": (
            "CREATE TABLE IF NOT EXISTS employees (\n"
            "    id     INT PRIMARY KEY AUTO_INCREMENT,\n"
            "    name   VARCHAR(100) NOT NULL,\n"
            "    salary DECIMAL(10,2),\n"
            "    dept   VARCHAR(50)\n"
            ");"
        ),
        "category": "ddl",
    },
    {
        "id": 10,
        "title": "Insert rows",
        "sql": (
            "INSERT INTO employees (name, salary, dept)\n"
            "VALUES ('Alice', 75000, 'Engineering'),\n"
            "       ('Bob',   60000, 'Marketing');"
        ),
        "category": "dml",
    },
]


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@api_bp.route("/health")
def health():
    """Return application health status."""
    db_ok = True
    try:
        conn = sqlite3.connect(DB_PATH, timeout=2)
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        db_ok = False

    status = "ok" if db_ok else "degraded"
    return jsonify({
        "status": status,
        "db": "ok" if db_ok else "unavailable",
        "cache": cache_stats(),
    }), (200 if db_ok else 503)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
@api_bp.route("/export", methods=["POST"])
@login_required
def export_results():
    """
    Export query result data supplied in the request body.

    Expected JSON body::

        {
            "format": "csv" | "json",
            "columns": ["col1", "col2", ...],
            "rows": [[val, val, ...], ...]
        }
    """
    body = request.get_json(silent=True) or {}
    fmt = body.get("format", "json").lower()
    columns: list = body.get("columns", [])
    rows: list = body.get("rows", [])

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        if columns:
            writer.writerow(columns)
        for row in rows:
            writer.writerow([str(v) if v is not None else "" for v in row])
        csv_data = output.getvalue()
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=query_result.csv"},
        )
    else:
        records = [dict(zip(columns, row)) for row in rows]
        json_data = json.dumps(records, indent=2, default=str)
        return Response(
            json_data,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=query_result.json"},
        )


# ---------------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------------
def _ensure_bookmarks_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bookmarks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            query       TEXT NOT NULL,
            db_type     TEXT NOT NULL DEFAULT 'mysql',
            title       TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()


@api_bp.route("/bookmarks", methods=["GET"])
@login_required
def list_bookmarks():
    user_id = session["user_id"]
    try:
        conn = sqlite3.connect(DB_PATH)
        _ensure_bookmarks_table(conn)
        rows = conn.execute(
            "SELECT id, query, db_type, title, created_at "
            "FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        conn.close()
        bookmarks = [
            {"id": r[0], "query": r[1], "db_type": r[2], "title": r[3], "created_at": r[4]}
            for r in rows
        ]
        return jsonify(bookmarks)
    except Exception as exc:
        logger.error("Error listing bookmarks: %s", exc)
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/bookmarks", methods=["POST"])
@login_required
def add_bookmark():
    user_id = session["user_id"]
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    db_type = body.get("db_type", "mysql")
    title = body.get("title", "").strip() or None

    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        _ensure_bookmarks_table(conn)
        cur = conn.execute(
            "INSERT INTO bookmarks (user_id, query, db_type, title) VALUES (?, ?, ?, ?)",
            (user_id, query, db_type, title),
        )
        conn.commit()
        bookmark_id = cur.lastrowid
        conn.close()
        return jsonify({"id": bookmark_id, "message": "Bookmark saved"}), 201
    except Exception as exc:
        logger.error("Error adding bookmark: %s", exc)
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/bookmarks/<int:bookmark_id>", methods=["DELETE"])
@login_required
def delete_bookmark(bookmark_id: int):
    user_id = session["user_id"]
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "DELETE FROM bookmarks WHERE id = ? AND user_id = ?",
            (bookmark_id, user_id),
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Bookmark deleted"})
    except Exception as exc:
        logger.error("Error deleting bookmark: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Query Templates
# ---------------------------------------------------------------------------
@api_bp.route("/templates")
def get_templates():
    """Return the built-in SQL template library."""
    category = request.args.get("category")
    templates = _TEMPLATES
    if category:
        templates = [t for t in templates if t["category"] == category]
    return jsonify(templates)
