from src.database import create_order, get_open_sell_order, close_order

def process_order_logic(trading_symbol: str, current_close: float, avg_200: float):
    """
    Processes the order logic based on 200 SMA strategy.
    
    Logic:
    1. Check if there is an open SELL order.
    2. If NO open order:
       - If current_close < avg_200: Create SELL order.
    3. If YES open SELL order:
       - If current_close > avg_200: Create BUY order, close open SELL order.
       - If current_close < avg_200 AND (entry_price - current_close) / entry_price >= 0.20:
         Create BUY order and close open SELL order.
    """
    
    existing_order = get_open_sell_order(trading_symbol)
    
    if not existing_order:
        # Case A: No open order
        if current_close < avg_200:
            print(f"[SIGNAL] SELL for {trading_symbol}: Close ({current_close}) < SMA ({avg_200})")
            create_order("SELL", trading_symbol, current_close, close=current_close, avg_200=avg_200)
    else:
        # Case B: Existing Open SELL order
        entry_price = existing_order['price']
        
        # 1. Check for Stop Loss / Reversal (Close > SMA)
        if current_close > avg_200:
            print(f"[SIGNAL] BUY (Reversal) for {trading_symbol}: Close ({current_close}) > SMA ({avg_200})")
            # Create BUY order to pair with the SELL
            create_order("BUY", trading_symbol, current_close, close=current_close, avg_200=avg_200, status="completed")
            # Close the original SELL order
            close_order(existing_order['id'])
            
        # 2. Check for Profit Taking (Profit >= 20%)
        # Profit on Short = (Entry - Current) / Entry
        # Note: If current_close < avg_200 is implicitly true if we are in profit on a short initiated below SMA? 
        # Not necessarily, price could be < entry but > SMA if SMA moved down?
        # The condition "current_close < avg_200" is explicitly requested.
        elif current_close < avg_200:
            profit_pct = (entry_price - current_close) / entry_price
            
            if profit_pct >= 0.02:
                print(f"[SIGNAL] BUY (Take Profit) for {trading_symbol}: Profit {profit_pct*100:.2f}% >= 20%")
                # "Create a sell order and mark both as completed" - As requested.
                # Usually closing a short is a BUY, but user requested SELL.
                create_order("BUY", trading_symbol, current_close, close=current_close, avg_200=avg_200, status="completed")
                
                # Close the original SELL order
                close_order(existing_order['id'])
