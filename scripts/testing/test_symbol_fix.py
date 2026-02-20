"""Quick test to verify symbol is correctly passed to signals."""

import sys
from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine

def main():
    print("Testing symbol fix...")
    
    # Load config
    config = Config.load_from_file()
    print(f"Config loaded: {config.run_mode} mode")
    print(f"Symbols: {config.portfolio_symbols}")
    
    # Initialize client
    client = Client(config.api_key, config.api_secret)
    
    # Initialize components
    data_manager = DataManager(config, client)
    strategy = StrategyEngine(config)
    
    # Test with XAGUSDT
    symbol = "XAGUSDT"
    print(f"\nTesting {symbol}...")
    
    # Fetch data
    candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
    candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
    candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol)
    candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol)
    
    print(f"Data fetched: 15m={len(candles_15m)}, 1h={len(candles_1h)}")
    
    # Update indicators
    strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
    print("Indicators updated")
    
    # Check for signals WITH symbol parameter
    long_signal = strategy.check_long_entry(symbol)
    short_signal = strategy.check_short_entry(symbol)
    
    if long_signal:
        print(f"\nLONG SIGNAL DETECTED")
        print(f"  Signal symbol: {long_signal.symbol}")
        print(f"  Expected symbol: {symbol}")
        print(f"  Match: {long_signal.symbol == symbol}")
    elif short_signal:
        print(f"\nSHORT SIGNAL DETECTED")
        print(f"  Signal symbol: {short_signal.symbol}")
        print(f"  Expected symbol: {symbol}")
        print(f"  Match: {short_signal.symbol == symbol}")
    else:
        print("\nNo signal detected")
    
    # Test with RIVERUSDT
    symbol = "RIVERUSDT"
    print(f"\n\nTesting {symbol}...")
    
    # Fetch data
    candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
    candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
    candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol)
    candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol)
    
    print(f"Data fetched: 15m={len(candles_15m)}, 1h={len(candles_1h)}")
    
    # Update indicators
    strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
    print("Indicators updated")
    
    # Check for signals WITH symbol parameter
    long_signal = strategy.check_long_entry(symbol)
    short_signal = strategy.check_short_entry(symbol)
    
    if long_signal:
        print(f"\nLONG SIGNAL DETECTED")
        print(f"  Signal symbol: {long_signal.symbol}")
        print(f"  Expected symbol: {symbol}")
        print(f"  Match: {long_signal.symbol == symbol}")
    elif short_signal:
        print(f"\nSHORT SIGNAL DETECTED")
        print(f"  Signal symbol: {short_signal.symbol}")
        print(f"  Expected symbol: {symbol}")
        print(f"  Match: {short_signal.symbol == symbol}")
    else:
        print("\nNo signal detected")
    
    print("\n\nTest complete!")

if __name__ == "__main__":
    main()
