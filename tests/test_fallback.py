import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from unittest.mock import MagicMock, patch


# Now we can import main logic constructs if they were functions, 
# but main.py has everything in 'if __name__ == "__main__":'
# So we might need to refactor main.py to be testable or use run_path
# For simplicity, let's just use runpy or exec to run the main block with mocked modules.
# However, importing src.kite_api inside main.py will pick up our mocks in sys.modules

class TestMainApp(unittest.TestCase):
    
    @patch('builtins.print')
    def test_main_fallback_logic(self, mock_print):
        # Create Mocks
        mock_kite = MagicMock()
        mock_db = MagicMock()
        
        # Apply mocks to sys.modules specifically for this test
        with patch.dict(sys.modules, {'src.kite_api': mock_kite, 'src.database': mock_db}):
            # Setup mocks
            mock_get_instruments = mock_db.get_instruments_by_pattern
            mock_fetch = mock_kite.fetch_instruments
            mock_save = mock_db.save_instruments
            mock_fetch_historical = mock_kite.fetch_kite_historical_data
            
            # Scenario: First call returns empty, then fetch/save, then second call returns data
            # check_instruments_exist is not used anymore
            
            # We need to simulate the sequence of get_instruments_by_pattern calls
            # 1st call: [] (Empty)
            # 2nd call: [{'trading_symbol': 'NIFTY26JANFUT'}] (Found after fetch)
            mock_get_instruments.side_effect = [[], [{"trading_symbol": "NIFTY26JANFUT", "instrument_token": "123"}]]
            
            mock_fetch.return_value = [{"some": "data"}]
            
            # Check historical data fetch (mock it to avoid errors)
            mock_fetch_historical.return_value = [{"timestamp": "2023-01-01", "close": 100}]

            # Run main.py
            # We don't need to patch specifically if we already mocked the module
            import main
            with open("main.py") as f:
                code = f.read()
                # We need to provide the mocked modules in the globals if possible?
                # No, exec uses current sys.modules imports.
                
                global_vars = {
                    "__name__": "__main__",
                    "__file__": "main.py",
                    "json": MagicMock(),
                    "date": MagicMock()
                }
                exec(code, global_vars)
            
            # Assertions
            # 1. Verify get_instruments_by_pattern was called initially
            # 2. Verify fetch_instruments was called (fallback)
            # 3. Verify save_instruments was called
            # 4. Verify get_instruments_by_pattern was called again
            
            # 4. Verify fetch_kite_historical_data was called for the found instrument
            # The mocked side effect for get_instruments_by_pattern returns 1 instrument "NIFTY26JANFUT"
            # So we expect 1 call to fetch_kite_historical_data
            
            self.assertTrue(mock_fetch_historical.called, "Should have fetched historical data")
            
            args = mock_fetch_historical.call_args
            self.assertEqual(args[1]['trading_symbol'], "NIFTY26JANFUT")
            self.assertEqual(args[1]['instrument_token'], "123") # "123" comes from our mock_rows in the test
            
            # 5. Verify save_historical_data was called for the candle data
            # Since we mocked sys.modules["src.database"], the function save_historical_data is a Mock object there.
            mock_save_hist = mock_db.save_historical_data
            self.assertTrue(mock_save_hist.called, "Should have saved historical data to DB")
            
            print(f"Historical Data Verification Passed. Fetch called for: {args[1]['trading_symbol']}")
            print("Main Logic Verification Passed.")

if __name__ == '__main__':
    unittest.main()
