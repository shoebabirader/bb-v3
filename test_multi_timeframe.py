#!/usr/bin/env python3
"""Test multi-timeframe data fetching."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import Config
from src.data_manager import DataManager
from binance.client import Client

def main():
    # Load config
    config = Config.load_from_file('config/config.json')
    
    # Create Binance client
    client = Client(config.api_key, config.api_secret)
    
    # Create data manager
    dm = DataManager(config, client)
    
    # Fetch data for XRPUSDT
    print("Fetching 15m data...")
    dm.fetch_historical_data(7, '15m', 'XRPUSDT')
    candles_15m = dm.get_latest_candles('15m', 200, 'XRPUSDT')
    print(f"15m candles: {len(candles_15m)}")
    
    print("\nFetching 1h data...")
    dm.fetch_historical_data(7, '1h', 'XRPUSDT')
    candles_1h = dm.get_latest_candles('1h', 100, 'XRPUSDT')
    print(f"1h candles: {len(candles_1h)}")
    
    if config.enable_multi_timeframe:
        print("\nFetching 5m data...")
        dm.fetch_historical_data(7, '5m', 'XRPUSDT')
        candles_5m = dm.get_latest_candles('5m', 300, 'XRPUSDT')
        print(f"5m candles: {len(candles_5m)}")
        
        print("\nFetching 4h data...")
        dm.fetch_historical_data(7, '4h', 'XRPUSDT')
        candles_4h = dm.get_latest_candles('4h', 50, 'XRPUSDT')
        print(f"4h candles: {len(candles_4h)}")
        
        print(f"\nMulti-timeframe enabled: {config.enable_multi_timeframe}")
        print(f"5m data available: {candles_5m is not None and len(candles_5m) > 0}")
        print(f"4h data available: {candles_4h is not None and len(candles_4h) > 0}")

if __name__ == '__main__':
    main()
