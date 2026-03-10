import psycopg2
from config import POSTGRES_CONFIG

# -----------------------------
# Run any SQL query
# -----------------------------
def run_postgres(query):
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
            # Other queries just commit
            conn.commit()
            result = {"message": "Query executed successfully"}

        cursor.close()
        conn.close()
        return result

    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# Get list of all tables
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
