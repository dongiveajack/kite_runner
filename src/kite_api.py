import requests
import csv
import io
from datetime import date
from typing import List, Dict
from src.config import KITE_AUTH_TOKEN, KITE_API_KEY


def fetch_kite_historical_data(
    instrument_token: str = "12602626",
    trading_symbol: str = "ACC",
    interval: str = "5minute",
    from_date: str = "2026-01-13 13:00:00",
    to_date: str = "2026-01-14 15:20:00"
) -> List[Dict]:
    """
    Fetches historical candle data from Kite API and returns it as a list of dicts.
    """
    if not KITE_AUTH_TOKEN:
        raise ValueError("Environment variable KITE_AUTH_TOKEN is not set.")

    url = f"https://api.kite.trade/instruments/historical/{instrument_token}/{interval}"
    params = {
        "from": from_date,
        "to": to_date,
        "continuous": 0,
        "oi": 0
    }
    
    headers = {
        "X-Kite-Version": "3",
        "Authorization": f"token {KITE_AUTH_TOKEN}"
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "success":
            print(f"Error from API: {data.get('message', 'Unknown error')}")
            return []

        candles = data.get("data", {}).get("candles", [])
        
        # Format the response as a list of dicts with timestamp, closed value, token, and symbol
        formatted_data = [
            {
                "timestamp": candle[0],
                "closed": candle[4],
                "instrument_token": instrument_token,
                "trading_symbol": trading_symbol
            }
            for candle in candles
        ]
        
        return formatted_data

    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return []
    except (IndexError, KeyError, ValueError) as e:
        print(f"Data parsing failed: {e}")
        return []

def fetch_instruments() -> List[Dict]:
    """
    Fetches the instruments dump from Kite API and parses the CSV.
    Adds a 'date' field to each record.
    """
    if not KITE_API_KEY:
        raise ValueError("Environment variable KITE_AUTH_TOKEN is not set.")

    url = "https://api.kite.trade/instruments"
    headers = {
        "X-Kite-Version": "3",
        "Authorization": f"token {KITE_AUTH_TOKEN}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # requests automatically decodes gzip if Content-Encoding is set
        # If it doesn't, we might need gzip module, but standard Kite API usually works with requests text
        csv_content = response.text
        
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        current_date_str = date.today().isoformat()
        
        instruments = []
        for row in csv_reader:
            # We only need specific columns + current date
            if row.get("instrument_type") == "FUT":
                instruments.append({
                    "date": current_date_str,
                    "instrument_token": row.get("instrument_token"),
                    "trading_symbol": row.get("tradingsymbol"),
                    "name": row.get("name"),
                    "instrument_type": row.get("instrument_type"),
                    "exchange_token": row.get("exchange_token"),
                    "exchange": row.get("exchange")
                })
            
        return instruments

    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch instruments: {e}")
        return []
    except Exception as e:
        print(f"Error parsing instruments CSV: {e}")
        return []

if __name__ == "__main__":
    print(fetch_kite_historical_data())