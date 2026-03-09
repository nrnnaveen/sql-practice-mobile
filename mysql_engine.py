import mysql.connector
from config import MYSQL_CONFIG

def run_mysql(query):

    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        cursor.execute(query)

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
