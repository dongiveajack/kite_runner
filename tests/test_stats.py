import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from unittest.mock import MagicMock, patch

# Mock sys dependencies
mock_psycopg2 = MagicMock()
sys.modules["psycopg2"] = mock_psycopg2
sys.modules["psycopg2.extras"] = MagicMock()

# Import
import src.database
import importlib

class TestRunningAverage(unittest.TestCase):
    def setUp(self):
        if 'src.database' in sys.modules:
            del sys.modules['src.database']
        import src.database

    @patch('src.database.psycopg2')
    def test_update_running_average_simple(self, mock_psycopg2):
        """Test simple recalculation logic."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock fetch candles -> Return 3 values (10, 10, 11) -> Avg 10.333...
        mock_cursor.fetchall.return_value = [[10.0], [10.0], [11.0]]
        
        # Call function
        src.database.update_running_average("TEST", [])
        
        # Verify SELECT called with LIMIT 200
        select_calls = [c for c in mock_cursor.execute.call_args_list if "SELECT closed FROM historical_candles" in c[0][0]]
        self.assertTrue(select_calls)
        self.assertIn("LIMIT 200", select_calls[0][0][0])
        
        # Verify Upsert (INSERT ... ON CONFLICT DO UPDATE)
        upsert_calls = [c for c in mock_cursor.execute.call_args_list if "INSERT INTO instrument_statistics" in c[0][0]]
        self.assertTrue(upsert_calls)
        
        # Expected avg = 31 / 3 = 10.33
        # Expected sum = 31.0
        params = upsert_calls[0][0][1]
        self.assertEqual(params[1], 31.0) # sum
        self.assertEqual(params[2], 10.33)  # avg rounded
        self.assertEqual(params[3], 3)     # count
        
        print("Simple Recalculation Test Passed.")

if __name__ == '__main__':
    unittest.main()

if __name__ == '__main__':
    unittest.main()
