import psycopg2

def load_table(conn, table_name):
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
    """, (table_name,))
    columns = [r[0] for r in cur.fetchall()]
    return columns
