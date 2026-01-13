import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dependencies
mock_kite = MagicMock()
mock_db = MagicMock()
mock_orders = MagicMock()

sys.modules["src.kite_api"] = mock_kite
sys.modules["src.kite_api"] = mock_kite
# Do not mock src.database or src.orders globally 

# Import main after mocking
import main

class TestPipeline(unittest.TestCase):

    @patch('main.fetch_kite_historical_data')
    @patch('main.save_historical_data')
    def test_fetch_and_save(self, mock_save, mock_fetch):
        """Stage 1: Fetch and Save"""
        mock_fetch.return_value = [{"closed": 100}]
        instruments = [{"trading_symbol": "TEST", "instrument_token": "123"}]
        
        updated = main.fetch_and_save_historical_data(instruments)
        
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]['trading_symbol'], 'TEST')
        mock_save.assert_called_once()
        print("Stage 1 (Fetch/Save) Verification Passed.")

    @patch('main.update_running_average')
    def test_update_sma(self, mock_update_avg):
        """Stage 2: Update SMA"""
        instruments = [{"trading_symbol": "TEST"}]
        
        main.update_sma_for_instruments(instruments)
        
        mock_update_avg.assert_called_once_with("TEST", [])
        print("Stage 2 (SMA Update) Verification Passed.")

    @patch('main.get_latest_stats_and_close')
    @patch('main.process_order_logic')
    def test_process_orders(self, mock_process_order, mock_get_stats):
        """Stage 3: Process Orders"""
        # Mock DB returns (latest_close, avg_200)
        mock_get_stats.return_value = (90.0, 100.0)
        
        instruments = [{"trading_symbol": "TEST"}]
        
        main.process_orders_for_instruments(instruments)
        
        # main.py imports process_order_logic from src.orders
        # Because we patch 'src.orders.process_order_logic', relying on main having imported it
        # If main does `from src.orders import process_order_logic`, patching `src.orders.process_order_logic`
        # updates the definition in `src.orders`, but main might have a reference to the OLD one?
        # NO. PATCH patches where it is LOOKED UP.
        # If main does `from src.orders import process_order_logic`, verifying main uses the patched version needs patching 'main.process_order_logic'
        
        mock_process_order.assert_called_once_with("TEST", 90.0, 100.0)
        print("Stage 3 (Order Logic) Verification Passed.")

if __name__ == '__main__':
    unittest.main()
