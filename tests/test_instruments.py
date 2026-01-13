import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from io import StringIO
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import date

# Mock imports
mock_psycopg2 = MagicMock()
sys.modules["psycopg2"] = mock_psycopg2
sys.modules["psycopg2.extras"] = MagicMock()

# Import after mocking
from src.kite_api import fetch_instruments
import src.database
import importlib

class TestInstruments(unittest.TestCase):
    def setUp(self):
        # Force reload
        if 'src.database' in sys.modules:
            del sys.modules['src.database']
        import src.database
    
    @patch('requests.get')
    def test_fetch_instruments(self, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        # Sample CSV content
        csv_data = """instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange
123456,789,ACC,ACC Ltd,1000.0,,0,0.05,1,FUT,NSE,NSE
654321,987,INFY,Infosys,1500.0,,0,0.05,1,EQ,NSE,NSE
"""
        mock_response.text = csv_data
        mock_get.return_value = mock_response
        
        # Set env var
        with patch.dict('os.environ', {'KITE_API_KEY': 'test_token'}):
            instruments = fetch_instruments()
            
        self.assertEqual(len(instruments), 1)
        self.assertEqual(instruments[0]['trading_symbol'], 'ACC')
        self.assertEqual(instruments[0]['instrument_token'], '123456')
        self.assertEqual(instruments[0]['instrument_type'], 'FUT')

    @patch('src.database.psycopg2')
    @patch('src.database.execute_values')
    def test_save_instruments(self, mock_execute_values, mock_psycopg2):
        # Mock DB
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Test Data
        current_date = date.today().isoformat()
        data = [
            {
                "date": current_date,
                "instrument_token": "123456",
                "trading_symbol": "ACC",
                "name": "ACC Ltd",
                "instrument_type": "EQ",
                "exchange_token": "789",
                "exchange": "NSE"
            }
        ]
        
        src.database.save_instruments(data)
        
        # Verify INSERT for single item
        insert_query = """
        INSERT INTO instruments (date, trading_symbol, instrument_token, name, instrument_type, exchange_token, exchange)
        VALUES %s
        ON CONFLICT (date, trading_symbol) DO NOTHING;
        """
        
        args = mock_execute_values.call_args
        self.assertIsNotNone(args)
        # Normalize whitespace for comparison
        self.assertEqual(" ".join(args[0][1].split()), " ".join(insert_query.split()))
        self.assertEqual(args[0][2], [
            (current_date, "ACC", "123456", "ACC Ltd", "EQ", "789", "NSE")
        ])
        
        print("Instruments Verification Passed.")
        
        # --- Test Batching ---
        # New Test Data for Batching
        data_batch = [
            {"date": current_date, "trading_symbol": "A", "instrument_token": "1", "name": "A", "instrument_type": "EQ", "exchange_token": "1", "exchange": "NSE"},
            {"date": current_date, "trading_symbol": "B", "instrument_token": "2", "name": "B", "instrument_type": "EQ", "exchange_token": "2", "exchange": "NSE"}
        ]
        
        # Reset mock to clear previous calls
        mock_execute_values.reset_mock()
        
        src.database.save_instruments(data_batch, batch_size=1)
        
        # Should be called twice (once per item)
        self.assertEqual(mock_execute_values.call_count, 2)
        print("Batching Verification Passed.")

    @patch('src.database.psycopg2')
    def test_get_instruments_by_pattern(self, mock_psycopg2):
        # Mock DB
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Test Data
        current_date_str = date.today().isoformat()
        
        # Mock return data from DB (tuple of values)
        # date, trading_symbol, instrument_token, name, instrument_type, exchange_token, exchange
        mock_rows = [
            (date.today(), "NIFTY26JANFUT", "123", "NIFTY 26 JAN FUT", "FUT", "1", "NFO"),
            (date.today(), "NIFTY26FEBFUT", "456", "NIFTY 26 FEB FUT", "FUT", "2", "NFO")
        ]
        mock_cursor.fetchall.return_value = mock_rows
        
        # Call function
        pattern = "NIFTY26%"
        results = src.database.get_instruments_by_pattern(pattern)
        
        # Verify Query
        expected_query = """
        SELECT date, trading_symbol, instrument_token, name, instrument_type, exchange_token, exchange
        FROM instruments
        WHERE trading_symbol LIKE %s AND date = %s;
        """
        
        # Check execution
        args = mock_cursor.execute.call_args
        self.assertIsNotNone(args, "Execute was not called")
        self.assertEqual(" ".join(args[0][0].split()), " ".join(expected_query.split()))
        self.assertEqual(args[0][1], (pattern, current_date_str))
        
        # Verify Results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['trading_symbol'], "NIFTY26JANFUT")
        self.assertEqual(results[0]['date'], current_date_str)
        self.assertEqual(results[1]['trading_symbol'], "NIFTY26FEBFUT")
        
        print("Pattern Fetch Verification Passed.")

if __name__ == '__main__':
    unittest.main()
