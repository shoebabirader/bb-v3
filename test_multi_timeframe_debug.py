"""Debug script to test multi-timeframe data fetching."""

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
    """Test multi-timeframe data fetching."""
    print("=" * 80)
    print("Multi-Timeframe Data Fetching Debug")
    print("=" * 80)
    
    # Load config
    config = Config.load_from_file()
    print(f"enable_multi_timeframe: {config.enable_multi_timeframe}")
    
    # Initialize client and data manager
    client = Client(config.api_key, config.api_secret)
    data_manager = DataManager(config, client)
    
    # Test symbol
    symbol = "XRPUSDT"
    
    # Fetch data for all timeframes
    print(f"\nFetching data for {symbol}...")
    
    print("\n1. Fetching 15m data...")
    candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
    print(f"   Fetched {len(candles_15m)} candles")
    
    print("\n2. Fetching 1h data...")
    candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
    print(f"   Fetched {len(candles_1h)} candles")
    
    print("\n3. Fetching 5m data...")
    candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol)
    print(f"   Fetched {len(candles_5m)} candles")
    
    print("\n4. Fetching 4h data...")
    candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol)
    print(f"   Fetched {len(candles_4h)} candles")
    
    # Check buffers
    print("\n" + "=" * 80)
    print("Buffer Status")
    print("=" * 80)
    
    buffer_15m = data_manager._symbol_buffers.get(symbol, {}).get('15m', [])
    buffer_1h = data_manager._symbol_buffers.get(symbol, {}).get('1h', [])
    buffer_5m = data_manager._symbol_buffers.get(symbol, {}).get('5m', [])
    buffer_4h = data_manager._symbol_buffers.get(symbol, {}).get('4h', [])
    
    print(f"15m buffer: {len(buffer_15m)} candles")
    print(f"1h buffer:  {len(buffer_1h)} candles")
    print(f"5m buffer:  {len(buffer_5m)} candles")
    print(f"4h buffer:  {len(buffer_4h)} candles")
    
    # Test get_latest_candles
    print("\n" + "=" * 80)
    print("Testing get_latest_candles()")
    print("=" * 80)
    
    latest_15m = data_manager.get_latest_candles("15m", 200, symbol=symbol)
    latest_1h = data_manager.get_latest_candles("1h", 100, symbol=symbol)
    latest_5m = data_manager.get_latest_candles("5m", 300, symbol=symbol)
    latest_4h = data_manager.get_latest_candles("4h", 50, symbol=symbol)
    
    print(f"get_latest_candles('15m', 200): {len(latest_15m) if latest_15m else 0} candles")
    print(f"get_latest_candles('1h', 100):  {len(latest_1h) if latest_1h else 0} candles")
    print(f"get_latest_candles('5m', 300):  {len(latest_5m) if latest_5m else 0} candles")
    print(f"get_latest_candles('4h', 50):   {len(latest_4h) if latest_4h else 0} candles")
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()
