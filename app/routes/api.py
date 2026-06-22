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

# Shared/generic templates (used when no db_type specified)
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

# MySQL-specific templates (use MySQL syntax: AUTO_INCREMENT, TINYINT, etc.)
QUERY_TEMPLATES_MYSQL = [
    {
        "id": 1,
        "name": "CREATE DATABASE",
        "description": "Create a new MySQL database",
        "query": "CREATE DATABASE IF NOT EXISTS my_practice_db;\nUSE my_practice_db;",
        "category": "ddl",
    },
    {
        "id": 2,
        "name": "CREATE TABLE",
        "description": "Create a table with MySQL syntax",
        "query": (
            "CREATE TABLE IF NOT EXISTS users (\n"
            "    id       INT PRIMARY KEY AUTO_INCREMENT,\n"
            "    name     VARCHAR(100) NOT NULL,\n"
            "    email    VARCHAR(200) UNIQUE,\n"
            "    age      INT,\n"
            "    active   TINYINT(1) DEFAULT 1,\n"
            "    created  DATETIME DEFAULT CURRENT_TIMESTAMP\n"
            ");"
        ),
        "category": "ddl",
    },
    {
        "id": 3,
        "name": "INSERT rows",
        "description": "Insert multiple rows into a table",
        "query": (
            "INSERT INTO users (name, email, age) VALUES\n"
            "    ('Alice', 'alice@example.com', 30),\n"
            "    ('Bob',   'bob@example.com',   25),\n"
            "    ('Carol', 'carol@example.com', 35);"
        ),
        "category": "dml",
    },
    {
        "id": 4,
        "name": "SELECT all",
        "description": "Select all rows from a table",
        "query": "SELECT * FROM users;",
        "category": "basics",
    },
    {
        "id": 5,
        "name": "SELECT with WHERE",
        "description": "Filter rows by condition",
        "query": "SELECT id, name, email FROM users WHERE age > 28 ORDER BY name ASC;",
        "category": "basics",
    },
    {
        "id": 6,
        "name": "UPDATE rows",
        "description": "Modify existing rows",
        "query": "UPDATE users SET active = 0 WHERE age < 26;",
        "category": "dml",
    },
    {
        "id": 7,
        "name": "DELETE rows",
        "description": "Remove rows matching a condition",
        "query": "DELETE FROM users WHERE active = 0;",
        "category": "dml",
    },
    {
        "id": 8,
        "name": "ALTER TABLE – add column",
        "description": "Add a new column to an existing table",
        "query": "ALTER TABLE users ADD COLUMN phone VARCHAR(20) AFTER email;",
        "category": "ddl",
    },
    {
        "id": 9,
        "name": "JOIN example",
        "description": "Join employees with orders",
        "query": (
            "SELECT e.name, o.order_date, p.name AS product, o.total_price\n"
            "FROM employees e\n"
            "INNER JOIN orders o ON e.id = o.employee_id\n"
            "INNER JOIN products p ON p.id = o.product_id\n"
            "ORDER BY o.order_date DESC\n"
            "LIMIT 10;"
        ),
        "category": "joins",
    },
    {
        "id": 10,
        "name": "GROUP BY aggregate",
        "description": "Count employees per department",
        "query": (
            "SELECT department, COUNT(*) AS headcount, AVG(salary) AS avg_salary\n"
            "FROM employees\n"
            "GROUP BY department\n"
            "ORDER BY headcount DESC;"
        ),
        "category": "aggregation",
    },
    {
        "id": 11,
        "name": "DROP TABLE",
        "description": "Remove a table (careful!)",
        "query": "DROP TABLE IF EXISTS users;",
        "category": "ddl",
    },
    {
        "id": 12,
        "name": "SHOW TABLES",
        "description": "List all tables in the current database",
        "query": "SHOW TABLES;",
        "category": "basics",
    },
]

# PostgreSQL-specific templates (use PG syntax: SERIAL, TEXT, NOW(), etc.)
QUERY_TEMPLATES_PG = [
    {
        "id": 1,
        "name": "CREATE TABLE",
        "description": "Create a table with PostgreSQL syntax",
        "query": (
            "CREATE TABLE IF NOT EXISTS users (\n"
            "    id      SERIAL PRIMARY KEY,\n"
            "    name    VARCHAR(100) NOT NULL,\n"
            "    email   VARCHAR(200) UNIQUE,\n"
            "    age     INTEGER,\n"
            "    active  BOOLEAN DEFAULT TRUE,\n"
            "    created TIMESTAMPTZ DEFAULT NOW()\n"
            ");"
        ),
        "category": "ddl",
    },
    {
        "id": 2,
        "name": "INSERT rows",
        "description": "Insert multiple rows using PostgreSQL syntax",
        "query": (
            "INSERT INTO users (name, email, age) VALUES\n"
            "    ('Alice', 'alice@example.com', 30),\n"
            "    ('Bob',   'bob@example.com',   25),\n"
            "    ('Carol', 'carol@example.com', 35)\n"
            "RETURNING id, name;"
        ),
        "category": "dml",
    },
    {
        "id": 3,
        "name": "SELECT all",
        "description": "Select all rows from a table",
        "query": "SELECT * FROM users;",
        "category": "basics",
    },
    {
        "id": 4,
        "name": "SELECT with WHERE",
        "description": "Filter rows by condition",
        "query": "SELECT id, name, email FROM users WHERE age > 28 ORDER BY name ASC;",
        "category": "basics",
    },
    {
        "id": 5,
        "name": "UPDATE rows",
        "description": "Modify existing rows (PostgreSQL)",
        "query": "UPDATE users SET active = FALSE WHERE age < 26 RETURNING id, name;",
        "category": "dml",
    },
    {
        "id": 6,
        "name": "DELETE rows",
        "description": "Remove rows matching a condition",
        "query": "DELETE FROM users WHERE active = FALSE RETURNING id;",
        "category": "dml",
    },
    {
        "id": 7,
        "name": "ALTER TABLE – add column",
        "description": "Add a new column to an existing table",
        "query": "ALTER TABLE users ADD COLUMN phone TEXT;",
        "category": "ddl",
    },
    {
        "id": 8,
        "name": "JOIN example",
        "description": "Join employees with orders",
        "query": (
            "SELECT e.name, o.order_date, p.name AS product, o.total_price\n"
            "FROM employees e\n"
            "INNER JOIN orders o ON e.id = o.employee_id\n"
            "INNER JOIN products p ON p.id = o.product_id\n"
            "ORDER BY o.order_date DESC\n"
            "LIMIT 10;"
        ),
        "category": "joins",
    },
    {
        "id": 9,
        "name": "GROUP BY aggregate",
        "description": "Count employees per department",
        "query": (
            "SELECT department, COUNT(*) AS headcount, AVG(salary) AS avg_salary\n"
            "FROM employees\n"
            "GROUP BY department\n"
            "ORDER BY headcount DESC;"
        ),
        "category": "aggregation",
    },
    {
        "id": 10,
        "name": "CTE (WITH clause)",
        "description": "Use a common table expression",
        "query": (
            "WITH dept_stats AS (\n"
            "    SELECT department, COUNT(*) AS cnt, MAX(salary) AS max_sal\n"
            "    FROM employees\n"
            "    GROUP BY department\n"
            ")\n"
            "SELECT * FROM dept_stats WHERE cnt > 1 ORDER BY max_sal DESC;"
        ),
        "category": "advanced",
    },
    {
        "id": 11,
        "name": "Window Function (RANK)",
        "description": "Rank employees by salary within department",
        "query": (
            "SELECT name, department, salary,\n"
            "    RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank\n"
            "FROM employees;"
        ),
        "category": "advanced",
    },
    {
        "id": 12,
        "name": "DROP TABLE",
        "description": "Remove a table (careful!)",
        "query": "DROP TABLE IF EXISTS users;",
        "category": "ddl",
    },
]


# ---------------------------------------------------------------------------
# Templates endpoints
# ---------------------------------------------------------------------------

@api_bp.route("/templates", methods=["GET"])
@login_required
def get_templates():
    """Return the list of built-in query templates.

    Accepts optional query params:
    - ``category``: filter by category (e.g. 'basics', 'ddl', 'dml')
    - ``db_type``: 'mysql' or 'postgres' to get database-specific templates
    """
    category = request.args.get("category")
    db_type = request.args.get("db_type", "").strip().lower()

    if db_type == "mysql":
        templates = QUERY_TEMPLATES_MYSQL
    elif db_type in ("postgres", "postgresql"):
        templates = QUERY_TEMPLATES_PG
    else:
        templates = QUERY_TEMPLATES

    if category:
        templates = [t for t in templates if t["category"] == category]
    return jsonify({"templates": templates})


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
