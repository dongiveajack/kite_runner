# Kite Historical Data & Algo Trading Engine

This project is a Python-based algorithmic trading engine designed to fetch historical futures data from the Zerodha Kite API, store it in a PostgreSQL database, and execute a moving average mean-reversion/trend-following strategy.

## 🚀 Features

*   **Robust Data Ingestion**: Automatically authenticates with Kite API and fetches 5-minute candle data for targeted instruments.
*   **PostgreSQL Storage**: Efficiently stores instrument metadata and historical candle data with duplicate handling (`ON CONFLICT` support).
*   **Dynamic Instrument Management**:
    *   Automatically fetches and updates the list of available Futures instruments.
    *   Filters for specific trading symbols (e.g., `NIFTY26%`).
*   **Algorithmic Analysis**:
    *   Calculates and maintains a running **200-period Simple Moving Average (SMA)**.
    *   Stores statistical indicators (`sum_200`, `avg_200`) in real-time.
*   **Order Execution Logic**:
    *   **Entry**: Opens a **SELL** position if price closes below the 200 SMA.
    *   **Stop Loss / Reversal**: Reverses to **BUY** if price closes back above the SMA.
    *   **Take Profit**: Automatically closes the position (BUY) if profit exceeds 20%.
*   **Modular Architecture**: Clean separation between Data Fetching, Analysis, and Execution stages.

## 🛠️ Tech Stack

*   **Language**: Python 3.13+
*   **Database**: PostgreSQL
*   **API**: Zerodha Kite Connect
*   **Libraries**: `requests`, `psycopg2`, `python-dotenv`

## 📂 Project Structure

```
.
├── main.py                     # Entry point (Orchestrator)
├── fetch_instruments_job.py    # Job to sync instrument master list
├── src/
│   ├── __init__.py
│   ├── config.py               # Environment configuration
│   ├── database.py             # DB connection, Schema, CRUD operations
│   ├── kite_api.py             # Kite API Wrapper
│   └── orders.py               # Order logic & Signal generation
├── tests/                      # Unit & Integration Tests
│   ├── test_database.py
│   ├── test_instruments.py
│   ├── test_main.py
│   ├── test_orders.py
│   ├── test_pipeline.py
│   └── test_stats.py
├── requirements.txt            # Python dependencies
└── .env                        # Secrets (API Keys & DB Creds)
```

## 📋 Prerequisites
*   **Python**: 3.13 or higher
*   **PostgreSQL**: 14 or higher
*   **Zerodha Kite Account**: API Key and Access Token required.

## ⚙️ Setup & Configuration

1.  **Clone the repository**
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```ini
    KITE_API_KEY=your_api_key
    KITE_AUTH_TOKEN=your_auth_token
    DB_HOST=localhost
    DB_NAME=kite_dn
    DB_USER=your_db_user
    DB_PASS=your_db_password
    DB_PORT=5432
    ```
4.  **Database Setup**:
    The application automatically creates the necessary tables (`instruments`, `historical_candles`, `instrument_statistics`, `orders`) on the first run. Ensure your PostgreSQL server is running and the database name exists.

## ▶️ Usage

### 1. Sync Instruments (One-time / Daily)
Fetch the master list of futures instruments:
```bash
python fetch_instruments_job.py
```

### 2. Run the Trading Engine
Execute the main pipeline (Fetch -> Analyze -> Trade):
```bash
python main.py
```

## 🧠 Strategy Logic

The core logic resides in `src/orders.py`.

1.  **Trend Detection**: Uses a 200-period SMA on 5-minute candles.
2.  **Signals**:
    *   **Short Entry**: Close < 200 SMA.
    *   **Trend Reversal**: Close > 200 SMA (Closes Short).
    *   **Deep Value**: Profit > 20% (Closes Short).

## ✅ Verification

Run the included test suites to verify system integrity:
```bash
```bash
python3 -m unittest discover tests
```
```
