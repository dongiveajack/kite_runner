import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Optional
from src.config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT
from datetime import datetime

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database.
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

def create_table_if_not_exists(conn):
    """
    Creates the historical_candles table if it does not exist.
    """
    query = """
    CREATE TABLE IF NOT EXISTS historical_candles (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP WITH TIME ZONE,
        trading_symbol VARCHAR(50),
        closed DOUBLE PRECISION,
        instrument_token VARCHAR(50),
        CONSTRAINT unique_candle UNIQUE (trading_symbol, timestamp)
    );
    """
    with conn.cursor() as cur:
        cur.execute(query)

        # Check and add columns if they don't exist (simple migration)
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='historical_candles'")
        columns = [row[0] for row in cur.fetchall()]

        if 'instrument_token' not in columns:
            cur.execute("ALTER TABLE historical_candles ADD COLUMN instrument_token VARCHAR(50)")
        if 'trading_symbol' not in columns:
            cur.execute("ALTER TABLE historical_candles ADD COLUMN trading_symbol VARCHAR(50)")

    conn.commit()

def save_historical_data(data: List[Dict]):
    """
    Saves the list of candle data to the database, skipping duplicates.
    """
    if not data:
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        create_table_if_not_exists(conn)

        # Prepare list of tuples for insertion
        values = [(d['timestamp'], d['closed'], d['instrument_token'], d['trading_symbol']) for d in data]

        query = """
        INSERT INTO historical_candles (timestamp, closed, instrument_token, trading_symbol)
        VALUES %s
        ON CONFLICT (trading_symbol, timestamp) DO NOTHING;
        """

        with conn.cursor() as cur:
            execute_values(cur, query, values)

        conn.commit()
        print(f"Data saved to database. {len(values)} records processed (duplicates skipped).")

    except Exception as e:
        print(f"Failed to save data: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_instruments_table_if_not_exists(conn):
    """
    Creates the instruments table if it does not exist.
    """
    query = """
    CREATE TABLE IF NOT EXISTS instruments (
        date DATE,
        trading_symbol VARCHAR(255),
        instrument_token VARCHAR(50),
        name VARCHAR(255),
        instrument_type VARCHAR(50),
        exchange_token VARCHAR(50),
        exchange VARCHAR(50),
        PRIMARY KEY (date, trading_symbol)
    );
    """
    with conn.cursor() as cur:
        cur.execute(query)

        # Check and add instrument_type if not exists
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='instruments'")
        columns = [row[0] for row in cur.fetchall()]

        if 'instrument_type' not in columns:
            cur.execute("ALTER TABLE instruments ADD COLUMN instrument_type VARCHAR(50)")

    conn.commit()

def save_instruments(data: List[Dict], batch_size: int = 5000):
    """
    Saves the list of instruments to the database in batches.
    """
    if not data:
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        create_instruments_table_if_not_exists(conn)

        total_records = len(data)
        print(f"Starting insertion of {total_records} records in batches of {batch_size}...")

        with conn.cursor() as cur:
            # Process in batches
            for i in range(0, total_records, batch_size):
                batch = data[i:i + batch_size]

                # Prepare list of tuples for the current batch
                values = [(
                    d['date'],
                    d['trading_symbol'],
                    d['instrument_token'],
                    d['name'],
                    d['instrument_type'],
                    d['exchange_token'],
                    d['exchange']
                ) for d in batch]

                query = """
                INSERT INTO instruments (date, trading_symbol, instrument_token, name, instrument_type, exchange_token, exchange)
                VALUES %s
                ON CONFLICT (date, trading_symbol) DO NOTHING;
                """

                execute_values(cur, query, values)
                conn.commit() # Commit after each batch to manage transaction size

                print(f"Processed batch {i // batch_size + 1}: {len(values)} records.")

        print(f"All {total_records} instruments saved successfully.")

    except Exception as e:
        print(f"Failed to save instruments: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_statistics_table_if_not_exists(conn):
    """
    Creates the instrument_statistics table if it does not exist.
    """
    query = """
    CREATE TABLE IF NOT EXISTS instrument_statistics (
        trading_symbol VARCHAR(255) PRIMARY KEY,
        sum_200 DOUBLE PRECISION,
        avg_200 DOUBLE PRECISION,
        count INT
    );
    """
    with conn.cursor() as cur:
        cur.execute(query)
    conn.commit()

def update_running_average(trading_symbol: str, new_candles: List[Dict]):
    """
    Updates the running 200-period average for a trading symbol directly using DB storage.
    Simplified approach: Fetches the latest 200 candles and recalculates avg/sum.
    """
    conn = get_db_connection()
    if not conn:
        return

    try:
        create_statistics_table_if_not_exists(conn)

        with conn.cursor() as cur:
            # Fetch latest 200 candles
            cur.execute("""
                SELECT closed FROM historical_candles 
                WHERE trading_symbol = %s 
                ORDER BY timestamp DESC 
                LIMIT 200
            """, (trading_symbol,))

            rows = cur.fetchall()
            values = [r[0] for r in rows]

            count = len(values)
            if count == 0:
                return

            current_sum = sum(values)
            avg = round(current_sum / count, 2)

            # Upsert into instrument_statistics
            cur.execute("""
                INSERT INTO instrument_statistics (trading_symbol, sum_200, avg_200, count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (trading_symbol) 
                DO UPDATE SET 
                    sum_200 = EXCLUDED.sum_200,
                    avg_200 = EXCLUDED.avg_200,
                    count = EXCLUDED.count;
            """, (trading_symbol, current_sum, avg, count))

            print(f"Updated stats for {trading_symbol}: SMA(200) = {avg:.2f} (Count: {count})")

        conn.commit()

    except Exception as e:
        print(f"Failed to update running average for {trading_symbol}: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_latest_stats_and_close(trading_symbol: str):
    """
    Retrieves the latest 200 SMA stats and the most recent candle close price.
    Returns a tuple (latest_close, avg_200) or None if data is missing.
    """
    conn = get_db_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cur:
            # 1. Fetch avg_200
            cur.execute("SELECT avg_200 FROM instrument_statistics WHERE trading_symbol = %s", (trading_symbol,))
            stats_row = cur.fetchone()

            if not stats_row:
                return None

            avg_200 = stats_row[0]

            # 2. Fetch latest close
            cur.execute("""
                SELECT closed FROM historical_candles 
                WHERE trading_symbol = %s 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (trading_symbol,))
            price_row = cur.fetchone()

            if not price_row:
                return None

            latest_close = price_row[0]

            return latest_close, avg_200

    except Exception as e:
        print(f"Failed to get latest stats for {trading_symbol}: {e}")
        return None
    finally:
        conn.close()

def create_orders_table_if_not_exists(conn):
    """
    Creates the orders table if it does not exist.
    """
    query = """
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        order_type VARCHAR(10),
        trading_symbol VARCHAR(255),
        price DOUBLE PRECISION,
        status VARCHAR(20),
        created_at TIMESTAMP
    );
    """
    with conn.cursor() as cur:
        cur.execute(query)

        # Check and add columns if they don't exist
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='orders'")
        columns = [row[0] for row in cur.fetchall()]

        if 'close' not in columns:
            cur.execute("ALTER TABLE orders ADD COLUMN close DOUBLE PRECISION")
        if 'avg_200' not in columns:
            cur.execute("ALTER TABLE orders ADD COLUMN avg_200 DOUBLE PRECISION")

    conn.commit()

def create_order(order_type: str, trading_symbol: str, price: float, close: float = None, avg_200: float = None, status: str = "created"):
    """
    Creates a new order in the database.
    """
    conn = get_db_connection()
    if not conn:
        return None

    try:
        create_orders_table_if_not_exists(conn)

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO orders (order_type, trading_symbol, price, close, avg_200, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (order_type, trading_symbol, price, close, avg_200, status, datetime.now()))

            order_id = cur.fetchone()[0]
            conn.commit()
            print(f"Created {order_type} order for {trading_symbol} at {price}. ID: {order_id}")
            return order_id

    except Exception as e:
        print(f"Failed to create order for {trading_symbol}: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_open_sell_order(trading_symbol: str):
    """
    Returns the open SELL order for the given symbol if it exists.
    """
    conn = get_db_connection()
    if not conn:
        return None

    try:
        # Check if table exists first to avoid errors on fresh start
        create_orders_table_if_not_exists(conn)

        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, order_type, trading_symbol, price, status, created_at 
                FROM orders 
                WHERE trading_symbol = %s AND order_type = 'SELL' AND status = 'created'
                ORDER BY created_at DESC
                LIMIT 1
            """, (trading_symbol,))

            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "order_type": row[1],
                    "trading_symbol": row[2],
                    "price": row[3],
                    "status": row[4],
                    "created_at": row[5]
                }
            return None

    except Exception as e:
        print(f"Failed to get open order for {trading_symbol}: {e}")
        return None
    finally:
        conn.close()

def close_order(order_id: int):
    """
    Marks an order as completed.
    """
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE orders SET status = 'completed' WHERE id = %s", (order_id,))
            conn.commit()
            print(f"Closed order ID: {order_id}")

    except Exception as e:
        print(f"Failed to close order {order_id}: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_instruments_by_pattern(pattern: str, date_str: str = None) -> List[Dict]:
    """
    Fetches instruments matching a trading symbol pattern for a specific date.
    
    Args:
        pattern: SQL LIKE pattern (e.g. 'NIFTY26%')
        date_str: Date string (YYYY-MM-DD). Defaults to current date if None.
        
    Returns:
        List of dictionaries containing instrument details.
    """
    from datetime import date # Import locally to avoid circular deps or just top level if preferred

    if date_str is None:
        date_str = date.today().isoformat()

    conn = get_db_connection()
    if not conn:
        return []

    try:
        query = """
        SELECT date, trading_symbol, instrument_token, name, instrument_type, exchange_token, exchange
        FROM instruments
        WHERE trading_symbol LIKE %s;
        """

        with conn.cursor() as cur:
            cur.execute(query, (pattern,))
            rows = cur.fetchall()

            instruments = []
            for row in rows:
                instruments.append({
                    "date": row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                    "trading_symbol": row[1],
                    "instrument_token": row[2],
                    "name": row[3],
                    "instrument_type": row[4],
                    "exchange_token": row[5],
                    "exchange": row[6]
                })

            return instruments

    except Exception as e:
        print(f"Failed to fetch instruments by pattern: {e}")
        return []
    finally:
        conn.close()

def check_instruments_exist(date_str: str = None) -> bool:
    """
    Checks if instruments data exists for the given date.
    
    Args:
        date_str: Date string (YYYY-MM-DD). Defaults to current date if None.
        
    Returns:
        True if data exists, False otherwise.
    """
    from datetime import date

    if date_str is None:
        date_str = date.today().isoformat()

    conn = get_db_connection()
    if not conn:
        return False

    try:
        query = "SELECT 1 FROM instruments WHERE date = %s LIMIT 1;"

        with conn.cursor() as cur:
            cur.execute(query, (date_str,))
            result = cur.fetchone()
            return result is not None

    except Exception as e:
        print(f"Failed to check instruments existence: {e}")
        return False
    finally:
        conn.close()
