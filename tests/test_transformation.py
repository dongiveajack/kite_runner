import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from src.kite_api import fetch_kite_historical_data
from unittest.mock import patch, MagicMock

def test_transformation():
    mock_response_data = {
        "status": "success",
        "data": {
            "candles": [
                ["2026-01-13T13:00:00+0530", 25710.1, 25713.9, 25681, 25695, 171275],
                ["2026-01-13T13:05:00+0530", 25695, 25711.9, 25690.2, 25711.1, 65650]
            ]
        }
    }

    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response

        # Set dummy env var
        import os
        os.environ["KITE_AUTH_TOKEN"] = "dummy_token"

        result = fetch_kite_historical_data(
            instrument_token="12602626",
            trading_symbol="ACC",
            interval="5minute", 
            from_date="2026-01-13 13:00:00", 
            to_date="2026-01-14 15:20:00"
        )
        
        expected = [
            {
                "timestamp": "2026-01-13T13:00:00+0530",
                "closed": 25695,
                "instrument_token": "12602626",
                "trading_symbol": "ACC"
            },
            {
                "timestamp": "2026-01-13T13:05:00+0530",
                "closed": 25711.1,
                "instrument_token": "12602626",
                "trading_symbol": "ACC"
            }
        ]

        assert result == expected
        print("Verification test PASSED: Data transformation logic is correct.")

if __name__ == "__main__":
    try:
        test_transformation()
    except Exception as e:
        print(f"Verification test FAILED: {e}")
        exit(1)
