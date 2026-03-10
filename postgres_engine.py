import psycopg2
from config import POSTGRES_CONFIG

# -----------------------------
# Block dangerous SQL commands
# -----------------------------
DANGEROUS_COMMANDS = ["drop", "alter", "truncate", "delete"]

def is_safe_query(query: str) -> bool:
    q = query.strip().lower()
    return not any(cmd in q for cmd in DANGEROUS_COMMANDS)

# -----------------------------
# Run any SQL query safely
# -----------------------------
def run_postgres(query):
    if not is_safe_query(query):
        return {"error": "This command is blocked for safety."}

    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query)

        # SELECT queries return rows
        if query.strip().lower().startswith("select"):
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result = {
                "columns": columns,
                "rows": rows
            }
        else:
            conn.commit()
            result = {"message": "Query executed successfully"}

        cursor.close()
        conn.close()
        return result

    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# Get list of all tables in DB
# -----------------------------
def get_postgres_tables():
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
        """)
        tables = [t[0] for t in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except Exception as e:
        return {"error": str(e)}
