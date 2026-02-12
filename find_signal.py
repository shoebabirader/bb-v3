"""Quick script to find which symbol currently has a signal."""

from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine

config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)
data_manager = DataManager(config, client)
strategy = StrategyEngine(config)

print("Checking all symbols for signals...\n")

for symbol in config.portfolio_symbols:
    print(f"{symbol}:", end=" ")
    
    try:
        candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
        candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
        candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol)
        candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol)
        
        strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
        
        long_signal = strategy.check_long_entry(symbol)
        short_signal = strategy.check_short_entry(symbol)
        
        if long_signal:
            print(f"LONG signal (symbol={long_signal.symbol})")
        elif short_signal:
            print(f"SHORT signal (symbol={short_signal.symbol})")
        else:
            print("No signal")
    except Exception as e:
        print(f"Error: {e}")

print("\nDone!")
