import mysql.connector
from config import MYSQL_CONFIG

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
def run_mysql(query):
    if not is_safe_query(query):
        return {"error": "This command is blocked for safety."}

    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query)

        # SELECT queries return rows
        if query.strip().lower().startswith("select"):
            columns = [col[0] for col in cursor.description]
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
def get_mysql_tables():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except Exception as e:
        return {"error": str(e)}
