import psycopg2
from config import POSTGRES_CONFIG

def run_query(query):

    conn=psycopg2.connect(**POSTGRES_CONFIG)
    cursor=conn.cursor()

    cursor.execute(query)

    if query.lower().startswith("select"):

        columns=[desc[0] for desc in cursor.description]
        rows=cursor.fetchall()

        return columns,rows

    conn.commit()

    return [],[]
