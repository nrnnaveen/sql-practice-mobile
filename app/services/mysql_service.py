import logging

import mysql.connector

from config import MYSQL_CONFIG

logger = logging.getLogger(__name__)


def run_mysql(query):
    """Execute a MySQL query and return the results or an error dict."""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query)

        if query.strip().lower().startswith("select"):
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            result = {"columns": columns, "rows": rows}
        else:
            conn.commit()
            result = {"message": "Query executed successfully"}

        cursor.close()
        conn.close()
        return result
    except Exception as exc:
        logger.error("MySQL error: %s", exc)
        return {"error": str(exc)}


def get_mysql_tables():
    """Return a list of table names in the configured MySQL database."""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except Exception as exc:
        logger.error("MySQL error fetching tables: %s", exc)
        return []
