"""Simple check for current signals on all portfolio symbols."""

from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine

config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)
data_manager = DataManager(config, client)
strategy = StrategyEngine(config)

print("Checking signals for all portfolio symbols...")
print(f"Config: ADX>{config.adx_threshold}, RVOL>{config.rvol_threshold}")
print()

for symbol in config.portfolio_symbols:
    try:
        candles_15m = data_manager.fetch_historical_data(days=2, timeframe="15m", symbol=symbol)
        candles_1h = data_manager.fetch_historical_data(days=2, timeframe="1h", symbol=symbol)
        candles_5m = data_manager.fetch_historical_data(days=2, timeframe="5m", symbol=symbol)
        candles_4h = data_manager.fetch_historical_data(days=2, timeframe="4h", symbol=symbol)
        
        strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
        
        long_signal = strategy.check_long_entry(symbol)
        short_signal = strategy.check_short_entry(symbol)
        
        if long_signal:
            print(f"{symbol}: LONG SIGNAL ACTIVE")
        elif short_signal:
            print(f"{symbol}: SHORT SIGNAL ACTIVE")
        else:
            indicators = strategy.get_indicator_snapshot()
            print(f"{symbol}: No signal (RVOL={indicators['rvol']:.2f}, ADX={indicators['adx']:.1f}, Squeeze={indicators['squeeze_color']})")
    except Exception as e:
        print(f"{symbol}: Error - {e}")

print()
print("If no signals are showing, the market conditions changed.")
print("Signals are dynamic and change as price/volume/momentum changes.")
