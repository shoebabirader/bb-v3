#!/usr/bin/env python3
"""Debug data manager buffers."""

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
    print("Fetching data for XRPUSDT...")
    dm.fetch_historical_data(7, '15m', 'XRPUSDT')
    dm.fetch_historical_data(7, '1h', 'XRPUSDT')
    dm.fetch_historical_data(7, '5m', 'XRPUSDT')
    dm.fetch_historical_data(7, '4h', 'XRPUSDT')
    
    print("\nChecking symbol buffers...")
    print(f"Symbol buffers keys: {list(dm._symbol_buffers.keys())}")
    
    if 'XRPUSDT' in dm._symbol_buffers:
        print(f"XRPUSDT timeframes: {list(dm._symbol_buffers['XRPUSDT'].keys())}")
        for tf in dm._symbol_buffers['XRPUSDT']:
            print(f"  {tf}: {len(dm._symbol_buffers['XRPUSDT'][tf])} candles")
    
    print("\nTrying to retrieve candles...")
    candles_15m = dm.get_latest_candles('15m', 200, 'XRPUSDT')
    candles_1h = dm.get_latest_candles('1h', 100, 'XRPUSDT')
    candles_5m = dm.get_latest_candles('5m', 300, 'XRPUSDT')
    candles_4h = dm.get_latest_candles('4h', 50, 'XRPUSDT')
    
    print(f"Retrieved 15m: {len(candles_15m) if candles_15m else 0}")
    print(f"Retrieved 1h: {len(candles_1h) if candles_1h else 0}")
    print(f"Retrieved 5m: {len(candles_5m) if candles_5m else 0}")
    print(f"Retrieved 4h: {len(candles_4h) if candles_4h else 0}")

if __name__ == '__main__':
    main()
