import mysql.connector
from config import MYSQL_CONFIG

# -----------------------------
# Run any SQL query
# -----------------------------
def run_mysql(query):
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
