import psycopg2
from config import POSTGRES_CONFIG

def run_postgres(query):

    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()

        cursor.execute(query)

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
