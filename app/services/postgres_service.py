import logging

import psycopg2

from config import POSTGRES_CONFIG

logger = logging.getLogger(__name__)


def run_postgres(query):
    """Execute a PostgreSQL query and return the results or an error dict."""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query)

        if query.strip().lower().startswith("select"):
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result = {"columns": columns, "rows": rows}
        else:
            conn.commit()
            result = {"message": "Query executed successfully"}

        cursor.close()
        conn.close()
        return result
    except Exception as exc:
        logger.error("PostgreSQL error: %s", exc)
        return {"error": str(exc)}


def get_postgres_tables():
    """Return a list of public table names in the configured PostgreSQL database."""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        )
        tables = [t[0] for t in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except Exception as exc:
        logger.error("PostgreSQL error fetching tables: %s", exc)
        return []
