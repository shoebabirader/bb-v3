#!/usr/bin/env python3
"""Test buffer population issue."""

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
    
    # Fetch data for all 5 symbols
    symbols = ['XRPUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'BNBUSDT']
    
    for symbol in symbols:
        print(f"\nFetching data for {symbol}...")
        dm.fetch_historical_data(7, '15m', symbol=symbol)
        dm.fetch_historical_data(7, '1h', symbol=symbol)
        dm.fetch_historical_data(7, '5m', symbol=symbol)
        dm.fetch_historical_data(7, '4h', symbol=symbol)
        
        print(f"Checking buffers for {symbol}...")
        print(f"  Symbol in _symbol_buffers: {symbol in dm._symbol_buffers}")
        if symbol in dm._symbol_buffers:
            print(f"  Timeframes: {list(dm._symbol_buffers[symbol].keys())}")
            for tf in ['5m', '15m', '1h', '4h']:
                if tf in dm._symbol_buffers[symbol]:
                    print(f"    {tf}: {len(dm._symbol_buffers[symbol][tf])} candles")
        
        # Try to retrieve
        candles_5m = dm.get_latest_candles('5m', 300, symbol)
        candles_4h = dm.get_latest_candles('4h', 50, symbol)
        print(f"  Retrieved 5m: {len(candles_5m)}")
        print(f"  Retrieved 4h: {len(candles_4h)}")

if __name__ == '__main__':
    main()
