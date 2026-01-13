from src.kite_api import fetch_instruments
from src.database import save_instruments

if __name__ == "__main__":
    print("Fetching instruments...")
    instruments = fetch_instruments()
    
    if instruments:
        print(f"Fetched {len(instruments)} instruments.")
        print("Saving to database...")
        save_instruments(instruments)
    else:
        print("No instruments fetched.")
