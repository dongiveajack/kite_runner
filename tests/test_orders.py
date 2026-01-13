import unittest
from unittest.mock import MagicMock, patch
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock sys dependencies
mock_psycopg2 = MagicMock()
sys.modules["psycopg2"] = mock_psycopg2

# Let's mock the functions imported by src.orders
import src.orders
import importlib

class TestOrderLogic(unittest.TestCase):
    def setUp(self):
        # Reload src.orders
        if 'src.orders' in sys.modules:
            del sys.modules['src.orders']
        import src.orders
    
    @patch('src.orders.get_open_sell_order')
    @patch('src.orders.create_order')
    @patch('src.orders.close_order')
    def test_process_order_logic_no_open_order_signal(self, mock_close, mock_create, mock_get_open):
        """Case A: No open order, Close < SMA -> SELL"""
        mock_get_open.return_value = None
        
        symbol = "TEST"
        current_close = 90.0
        avg_200 = 100.0
        
        current_close = 90.0
        avg_200 = 100.0
        
        src.orders.process_order_logic(symbol, current_close, avg_200)
        
        mock_create.assert_called_once_with("SELL", symbol, current_close)
        mock_close.assert_not_called()
        print("Test A Passed: SELL Signal generated.")

    @patch('src.orders.get_open_sell_order')
    @patch('src.orders.create_order')
    @patch('src.orders.close_order')
    def test_process_order_logic_no_open_order_no_signal(self, mock_close, mock_create, mock_get_open):
        """Case A (No Signal): No open order, Close >= SMA -> Do nothing"""
        mock_get_open.return_value = None
        
        mock_get_open.return_value = None
        
        src.orders.process_order_logic("TEST", 110.0, 100.0) # Close > SMA
        mock_create.assert_not_called()
        
        src.orders.process_order_logic("TEST", 100.0, 100.0) # Close == SMA
        mock_create.assert_not_called()
        print("Test A (No Signal) Passed.")

    @patch('src.orders.get_open_sell_order')
    @patch('src.orders.create_order')
    @patch('src.orders.close_order')
    def test_process_order_logic_reversal(self, mock_close, mock_create, mock_get_open):
        """Case B1: Open SELL exists, Close > SMA -> Reversal BUY"""
        mock_get_open.return_value = {"id": 1, "price": 110.0, "status": "created"}
        
        symbol = "TEST"
        current_close = 105.0 # < Entry but > SMA
        avg_200 = 100.0
        
        # We need to make sure internal logic doesn't fail if we mocked things strangely
        # The variables here are plain floats so > < operators work fine.
        # The issue is typically if create_order arguments are Mocks.
        
        src.orders.process_order_logic(symbol, current_close, avg_200)
        
        mock_create.assert_called_once_with("BUY", symbol, current_close, status="completed")
        mock_close.assert_called_once_with(1)
        print("Test B1 Passed: Reversal BUY generated.")

    @patch('src.orders.get_open_sell_order')
    @patch('src.orders.create_order')
    @patch('src.orders.close_order')
    def test_process_order_logic_take_profit(self, mock_close, mock_create, mock_get_open):
        """Case B2: Open SELL exists, Close < SMA, Profit >= 20% -> Take Profit BUY"""
        entry_price = 100.0
        mock_get_open.return_value = {"id": 1, "price": entry_price, "status": "created"}
        
        symbol = "TEST"
        avg_200 = 90.0
        
        # Scenario: Profit = 20%
        # (Entry - Close) / Entry = 0.20
        # 1 - Close/Entry = 0.20
        # Close/Entry = 0.80
        # Close = 80.0
        
        current_close = 80.0 
        # Check conditions: 
        # Close (80) < SMA (90) -> True
        # Profit (20%) >= 20% -> True
        
        src.orders.process_order_logic(symbol, current_close, avg_200)
        
        mock_create.assert_called_once_with("BUY", symbol, current_close, status="completed")
        mock_close.assert_called_once_with(1)
        print("Test B2 Passed: Take Profit BUY generated.")

    @patch('src.orders.get_open_sell_order')
    @patch('src.orders.create_order')
    @patch('src.orders.close_order')
    def test_process_order_logic_hold(self, mock_close, mock_create, mock_get_open):
        """Case B (Hold): Open SELL exists, Close < SMA, Profit < 20% -> Hold"""
        entry_price = 100.0
        mock_get_open.return_value = {"id": 1, "price": entry_price, "status": "created"}
        
        symbol = "TEST"
        avg_200 = 90.0
        current_close = 85.0 # Profit 15%
        
        current_close = 85.0 # Profit 15%
        
        src.orders.process_order_logic(symbol, current_close, avg_200)
        
        mock_create.assert_not_called()
        mock_close.assert_not_called()
        print("Test B (Hold) Passed.")

if __name__ == '__main__':
    unittest.main()
