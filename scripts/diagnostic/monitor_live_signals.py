"""Monitor live signals in real-time to see if they trigger."""
import time
from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine

print("="*70)
print("LIVE SIGNAL MONITOR - Press Ctrl+C to stop")
print("="*70)

# Load config
config = Config.load_from_file('config/config.json')
client = Client(config.api_key, config.api_secret)
data_manager = DataManager(config, client)

# Monitor TRXUSDT since you saw a signal there
symbol = "TRXUSDT"
config.symbol = symbol

strategy = StrategyEngine(config)

print(f"\nMonitoring {symbol} for signals...")
print(f"ADX threshold: {config.adx_threshold}")
print(f"RVOL threshold: {config.rvol_threshold}")
print("\nChecking every 5 seconds...\n")

try:
    while True:
        # Fetch latest data
        candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
        candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
        
        # Update indicators
        strategy.update_indicators(candles_15m, candles_1h)
        
        # Check signals
        long_signal = strategy.check_long_entry(symbol)
        short_signal = strategy.check_short_entry(symbol)
        
        # Get indicators
        ind = strategy.current_indicators
        
        # Display status
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] ADX={ind.adx:.2f} RVOL={ind.rvol:.2f} | ", end="")
        
        if long_signal:
            print(f"🟢 LONG SIGNAL @ ${long_signal.price:.4f}")
        elif short_signal:
            print(f"🔴 SHORT SIGNAL @ ${short_signal.price:.4f}")
        else:
            print("⚪ No signal")
        
        time.sleep(5)
        
except KeyboardInterrupt:
    print("\n\nMonitoring stopped.")
