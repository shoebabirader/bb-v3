"""Check the actual live position details and current market price."""

import json
from pathlib import Path
from binance.client import Client

# Load config to get symbol and API keys
config_path = Path("config/config.json")
if config_path.exists():
    with open(config_path, 'r') as f:
        config = json.load(f)
        symbol = config.get('symbol', 'DOTUSDT')
        api_key = config.get('api_key')
        api_secret = config.get('api_secret')
else:
    symbol = 'DOTUSDT'
    api_key = None
    api_secret = None

print(f"Checking position data for {symbol}...")

# Get current market price
try:
    if api_key and api_secret:
        client = Client(api_key, api_secret)
        ticker = client.futures_symbol_ticker(symbol=symbol)
        current_price = float(ticker['price'])
        print(f"\n{'='*50}")
        print(f"CURRENT MARKET PRICE for {symbol}: ${current_price:.4f}")
        print(f"{'='*50}")
    else:
        print("\nNo API keys found - cannot fetch current price")
        current_price = None
except Exception as e:
    print(f"\nError fetching current price: {e}")
    current_price = None

# Check if there's a state file or recent trade log
trades_log = Path("logs/trades.log")
if trades_log.exists():
    with open(trades_log, 'r') as f:
        lines = f.readlines()
        if lines:
            last_line = lines[-1]
            print(f"\nLast trade log entry:")
            print(last_line[:200] + "..." if len(last_line) > 200 else last_line)
            
            # Try to parse it
            if "TRADE_EXECUTED" in last_line:
                try:
                    json_start = last_line.index('{')
                    json_str = last_line[json_start:]
                    trade_data = json.loads(json_str)
                    print(f"\nParsed trade data:")
                    print(f"  Symbol: {trade_data.get('symbol')}")
                    print(f"  Side: {trade_data.get('side')}")
                    print(f"  Entry: ${trade_data.get('entry_price')}")
                    print(f"  Exit: ${trade_data.get('exit_price')}")
                    print(f"  PnL: ${trade_data.get('pnl')}")
                    print(f"  Exit Reason: {trade_data.get('exit_reason')}")
                    
                    if current_price and trade_data.get('symbol') == symbol:
                        print(f"\n  Current price: ${current_price:.4f}")
                        if trade_data.get('exit_price'):
                            print(f"  (Trade already closed)")
                except Exception as e:
                    print(f"Could not parse trade data: {e}")
else:
    print("\nNo trades.log file found")

print("\n" + "="*50)
print("PAPER TRADING TIPS:")
print("="*50)
print("If bot is not executing trades, check:")
print("1. Strategy conditions are very strict (ADX, RVOL, VWAP all must align)")
print("2. With 2% risk, trades are more conservative")
print("3. Run check_signals.py to see current market conditions")
print("4. Consider lowering ADX threshold or RVOL threshold if needed")

