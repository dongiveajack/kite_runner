import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock not-installed libraries
mock_psycopg2 = MagicMock()
sys.modules["psycopg2"] = mock_psycopg2
sys.modules["psycopg2.extras"] = MagicMock()

# Import after mocking
import src.database
import importlib

class TestDatabaseSave(unittest.TestCase):
    def setUp(self):
        # Force reload of src.database to use the fresh mock_psycopg2
        if 'src.database' in sys.modules:
            del sys.modules['src.database']
        import src.database
        importlib.invalidate_caches()
        
    @patch('src.database.psycopg2')
    @patch('src.database.execute_values')
    def test_save_historical_data(self, mock_execute_values, mock_psycopg2):
        # Mock DB connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Test data
        now = datetime.now()
        data = [
            {
                "timestamp": now,
                "closed": 100.5,
                "instrument_token": "123456",
                "trading_symbol": "TEST_SYMBOL"
            },
            {
                "timestamp": now,
                "closed": 101.0,
                "instrument_token": "123456",
                "trading_symbol": "TEST_SYMBOL"
            }
        ]

        print("Saving mock data to database...")
        src.database.save_historical_data(data)
        print("Done.")
        
        # Verify insertion
        insert_query = """
        INSERT INTO historical_candles (timestamp, closed, instrument_token, trading_symbol)
        VALUES %s
        ON CONFLICT (trading_symbol, timestamp) DO NOTHING;
        """
        
        mock_execute_values.assert_called_once()
        args = mock_execute_values.call_args
        self.assertIsNotNone(args)
        # args[0] is tuple of positional args: (cursor, query, values)
        # args[0][1] is query
        self.assertEqual(" ".join(args[0][1].split()), " ".join(insert_query.split()))
        
        # args[0][2] is values list
        self.assertEqual(len(args[0][2]), 2)
        self.assertEqual(args[0][2][0][0], now)
        self.assertEqual(args[0][2][0][1], 100.5)

        print("DB Verification Passed: Correctly used ON CONFLICT DO NOTHING")

if __name__ == '__main__':
    unittest.main()
