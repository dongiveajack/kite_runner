from src.kite_api import fetch_kite_historical_data, fetch_instruments
from src.database import save_historical_data, save_instruments, get_instruments_by_pattern, update_running_average, get_latest_stats_and_close
from src.orders import process_order_logic
from datetime import datetime, timedelta, timezone
from typing import List, Dict

def ensure_target_instruments_exist(pattern: str) -> List[Dict]:
    """
    Ensures that instruments matching the pattern exist in the database.
    If not found, fetches from API, saves, and retries.
    """
    print(f"Checking for instruments matching pattern '{pattern}'...")
    target_instruments = get_instruments_by_pattern(pattern)
    
    if not target_instruments:
        print(f"No instruments found for pattern '{pattern}'. Fetching all instruments from Kite API...")
        try:
            all_instruments = fetch_instruments()
            if all_instruments:
                print(f"Fetched {len(all_instruments)} instruments from API.")
                
                # Filter instruments by pattern before saving
                import fnmatch
                # Convert SQL LIKE pattern (%) to fnmatch pattern (*)
                fnmatch_pattern = pattern.replace('%', '*')
                
                filtered_instruments = [
                    inst for inst in all_instruments 
                    if fnmatch.fnmatch(inst['trading_symbol'], fnmatch_pattern)
                ]
                
                print(f"Filtered down to {len(filtered_instruments)} instruments matching '{fnmatch_pattern}'. Saving to database...")
                save_instruments(filtered_instruments)
                
                # Retry fetching target instruments (should match what we just saved)
                target_instruments = get_instruments_by_pattern(pattern)
                print(f"Refetched target instruments: found {len(target_instruments)} matches.")
            else:
                print("Warning: No instruments fetched from API.")
        except Exception as e:
            print(f"Error fetching/saving instruments: {e}")
    else:
        print(f"Found {len(target_instruments)} instruments matching '{pattern}' in database.")
        
    return target_instruments

def fetch_and_save_historical_data(instruments: List[Dict]) -> List[Dict]:
    """
    Fetches historical data for the given list of instruments and saves to DB.
    Returns the list of instruments that were successfully processed.
    """
    if not instruments:
        print("No target instruments available to fetch data for.")
        return []

    print(f"Starting historical data fetch for {len(instruments)} instruments...")
    
    # Define time range: Current time to +5 minutes
    # AWS Lambda runs in UTC, so we must manually adjust to IST (UTC+5:30)
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    
    print(f"Current Time (IST): {now_ist}")

    from_date = (now_ist - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    to_date = (now_ist + timedelta(minutes=4)).strftime("%Y-%m-%d %H:%M:%S")
    # from_date = now.strftime("%Y-%m-%d %H:%M:%S")
    # to_date = (now + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    # from_date = "2026-01-12 13:00:00"
    # to_date = datetime.now()
    interval = "5minute"
    
    successful_instruments = []
    
    for instrument in instruments:
        token = instrument['instrument_token']
        symbol = instrument['trading_symbol']
        
        print(f"Fetching data for {symbol} ({token})...")
        try:
            candles = fetch_kite_historical_data(
                instrument_token=token,
                trading_symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )
            
            if candles:
                print(f"Fetched {len(candles)} candles for {symbol}. Saving to DB...")
                save_historical_data(candles)
                successful_instruments.append(instrument)
            else:
                print(f"No candles fetched for {symbol}.")
                
        except Exception as e:
            print(f"Failed to fetch/save data for {symbol}: {e}")
            
    print("Historical data fetch completed.")
    return successful_instruments

def update_sma_for_instruments(instruments: List[Dict]):
    """
    Updates the 200 SMA for the given list of instruments.
    Stage 2 of the pipeline.
    """
    if not instruments:
        print("No instruments to update SMA for.")
        return

    print(f"Starting SMA update for {len(instruments)} instruments...")
    
    for instrument in instruments:
        symbol = instrument['trading_symbol']
        try:
            print(f"Updating running average for {symbol}...")
            # We strictly need to "update" it based on the recent data.
            # update_running_average recalculates based on latest 200 candles in DB.
            update_running_average(symbol, []) 
        except Exception as e:
            print(f"Failed to update SMA for {symbol}: {e}")
            
    print("SMA update process completed.")


def process_orders_for_instruments(instruments: List[Dict]):
    """
    Processes trading orders for the given list of instruments.
    Stage 3 of the pipeline.
    """
    if not instruments:
        print("No instruments to process orders for.")
        return

    print(f"Starting order processing for {len(instruments)} instruments...")
    
    for instrument in instruments:
        symbol = instrument['trading_symbol']
        
        try:
            # Retrieve updated stats
            result = get_latest_stats_and_close(symbol)
            
            if result:
                latest_close, avg_200 = result
                print(f"Processing order logic for {symbol}. Close: {latest_close}, SMA: {avg_200}")
                process_order_logic(symbol, latest_close, avg_200)
            else:
                print(f"No sufficient data (stats/candles) found for {symbol}. Skipping orders.")
                    
        except Exception as e:
            print(f"Failed to process orders for {symbol}: {e}")
            
    print("Order processing completed.")

if __name__ == "__main__":
    # 1. Ensure Instruments
    PATTERN = "NIFTY26%"
    targets = ensure_target_instruments_exist(PATTERN)
    
    # 2. Fetch Historical Data
    updated_instruments = fetch_and_save_historical_data(targets)
    
    # 3. Update SMA
    update_sma_for_instruments(updated_instruments)
    
    # 4. Process Orders
    process_orders_for_instruments(updated_instruments)
