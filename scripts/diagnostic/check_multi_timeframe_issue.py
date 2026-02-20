"""Diagnostic script to identify multi-timeframe data issue."""

import logging
from binance.client import Client
from src.config import Config
from src.data_manager import DataManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Diagnose multi-timeframe issue."""
    print("=" * 80)
    print("Multi-Timeframe Issue Diagnostic")
    print("=" * 80)
    
    # Load config
    config = Config.load_from_file()
    
    print(f"\nConfiguration:")
    print(f"  enable_multi_timeframe: {config.enable_multi_timeframe}")
    print(f"  enable_portfolio_management: {config.enable_portfolio_management}")
    print(f"  primary symbol: {config.symbol}")
    
    if config.enable_portfolio_management:
        print(f"  portfolio symbols: {config.portfolio_symbols}")
        print(f"  ⚠️  Portfolio management is ENABLED with {len(config.portfolio_symbols)} symbols")
        print(f"  This means the bot will try to fetch data for ALL symbols")
    
    # Initialize client and data manager
    client = Client(config.api_key, config.api_secret)
    data_manager = DataManager(config, client)
    
    # Determine which symbols to test
    if config.enable_portfolio_management:
        test_symbols = config.portfolio_symbols
    else:
        test_symbols = [config.symbol]
    
    print(f"\nTesting data fetch for {len(test_symbols)} symbol(s)...")
    
    # Test fetching data for each symbol
    for symbol in test_symbols:
        print(f"\n--- Testing {symbol} ---")
        
        try:
            # Fetch 15m
            print(f"  Fetching 15m...")
            candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
            print(f"    ✓ Fetched {len(candles_15m)} candles")
            
            # Fetch 1h
            print(f"  Fetching 1h...")
            candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
            print(f"    ✓ Fetched {len(candles_1h)} candles")
            
            if config.enable_multi_timeframe:
                # Fetch 5m
                print(f"  Fetching 5m...")
                candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol)
                print(f"    ✓ Fetched {len(candles_5m)} candles")
                
                # Fetch 4h
                print(f"  Fetching 4h...")
                candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol)
                print(f"    ✓ Fetched {len(candles_4h)} candles")
            
            # Check buffers
            buffer_15m = data_manager._symbol_buffers.get(symbol, {}).get('15m', [])
            buffer_1h = data_manager._symbol_buffers.get(symbol, {}).get('1h', [])
            buffer_5m = data_manager._symbol_buffers.get(symbol, {}).get('5m', [])
            buffer_4h = data_manager._symbol_buffers.get(symbol, {}).get('4h', [])
            
            print(f"  Buffer status:")
            print(f"    15m: {len(buffer_15m)} candles")
            print(f"    1h:  {len(buffer_1h)} candles")
            print(f"    5m:  {len(buffer_5m)} candles")
            print(f"    4h:  {len(buffer_4h)} candles")
            
            # Check if multi-timeframe data is missing
            if config.enable_multi_timeframe:
                if len(buffer_5m) == 0 or len(buffer_4h) == 0:
                    print(f"    ✗ PROBLEM: Multi-timeframe buffers are empty!")
                else:
                    print(f"    ✓ Multi-timeframe buffers OK")
            
        except Exception as e:
            print(f"    ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Diagnostic Complete")
    print("=" * 80)
    
    # Recommendations
    print("\nRecommendations:")
    if config.enable_portfolio_management and len(config.portfolio_symbols) > 1:
        print("  1. Try disabling portfolio management temporarily:")
        print("     Set 'enable_portfolio_management': false in config.json")
        print("  2. Or reduce the number of portfolio symbols to test with fewer symbols")
    
    if config.enable_multi_timeframe:
        print("  3. If issue persists, check Binance API rate limits")
        print("  4. Consider adding delays between symbol data fetches")

if __name__ == "__main__":
    main()
