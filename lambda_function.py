import json
import logging
import os
from dotenv import load_dotenv

# Load environment variables for local testing
load_dotenv()

# Import core logic from main.py
from main import (
    ensure_target_instruments_exist,
    fetch_and_save_historical_data,
    update_sma_for_instruments,
    process_orders_for_instruments
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda Handler for the trading pipeline.
    """
    logger.info("Lambda execution started")
    
    try:
        # 1. Ensure Instruments
        # Using the same pattern as in main.py, or from env var if available
        PATTERN = os.getenv("INSTRUMENT_PATTERN", "NIFTY26%")
        logger.info(f"Step 1: Ensuring instruments for pattern {PATTERN}")
        targets = ensure_target_instruments_exist(PATTERN)
        
        # 2. Fetch Historical Data
        logger.info(f"Step 2: Fetching historical data for {len(targets)} instruments")
        updated_instruments = fetch_and_save_historical_data(targets)
        
        # 3. Update SMA
        logger.info(f"Step 3: Updating SMA for {len(updated_instruments)} instruments")
        update_sma_for_instruments(updated_instruments)
        
        # 4. Process Orders
        logger.info(f"Step 4: Processing orders")
        process_orders_for_instruments(updated_instruments)
        
        return {
            'statusCode': 200,
            'body': json.dumps('Pipeline completed successfully')
        }
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps(f"Execution Error: {str(e)}")
        }

if __name__ == "__main__":
    # Local Test
    print(lambda_handler({}, None))
