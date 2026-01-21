from src.database import get_db_connection
try:
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM instruments WHERE trading_symbol LIKE 'NIFTY26%'")
            print(f"Deleted {cur.rowcount} rows.")
        conn.commit()
        conn.close()
except Exception as e:
    print(e)
