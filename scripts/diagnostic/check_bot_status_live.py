"""Check if the bot is actually processing symbols and checking for signals."""

import time
import logging
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from binance.client import Client

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("=" * 80)
    print("CHECKING BOT STATUS - SIGNAL DETECTION")
    print("=" * 80)
    
    # Load config
    config = Config.load_from_file("config/config.json")
    print(f"\n✓ Config loaded")
    print(f"  Symbol: {config.symbol}")
    print(f"  Enable Multi-Timeframe: {config.enable_multi_timeframe}")
    print(f"  Enable Portfolio Management: {config.enable_portfolio_management}")
    
    # Initialize Binance client
    client = Client(config.api_key, config.api_secret)
    
    # Initialize data manager and strategy
    data_manager = DataManager(config, client)
    strategy = StrategyEngine(config)
    
    print(f"\n✓ Data manager and strategy initialized")
    
    # Fetch data for XAGUSDT
    symbol = "XAGUSDT"
    print(f"\n📊 Fetching data for {symbol}...")
    
    candles_15m = data_manager.fetch_historical_data(symbol, "15m", 200)
    candles_1h = data_manager.fetch_historical_data(symbol, "1h", 100)
    
    print(f"  15m candles: {len(candles_15m)}")
    print(f"  1h candles: {len(candles_1h)}")
    
    # Update indicators
    print(f"\n📈 Updating indicators...")
    strategy.update_indicators(candles_15m, candles_1h, None, None)
    
    # Check for signals
    print(f"\n🎯 Checking for signals...")
    long_signal = strategy.check_long_entry(symbol)
    short_signal = strategy.check_short_entry(symbol)
    
    print(f"\n{'='*80}")
    print(f"SIGNAL CHECK RESULTS")
    print(f"{'='*80}")
    print(f"LONG Signal: {'✓ DETECTED' if long_signal else '✗ None'}")
    print(f"SHORT Signal: {'✓ DETECTED' if short_signal else '✗ None'}")
    
    if long_signal:
        print(f"\nLONG Signal Details:")
        print(f"  Price: ${long_signal.price:.4f}")
        print(f"  Side: {long_signal.side}")
    
    if short_signal:
        print(f"\nSHORT Signal Details:")
        print(f"  Price: ${short_signal.price:.4f}")
        print(f"  Side: {short_signal.side}")
    
    # Show current indicators
    print(f"\n{'='*80}")
    print(f"CURRENT INDICATORS")
    print(f"{'='*80}")
    print(f"Price: ${candles_15m[-1].close:.4f}")
    print(f"ADX: {strategy.current_indicators.adx_15m:.2f} (threshold: {config.adx_threshold})")
    print(f"RVOL: {strategy.current_indicators.rvol:.2f} (threshold: {config.rvol_threshold})")
    print(f"Squeeze Value: {strategy.current_indicators.squeeze_value:.4f}")
    print(f"Squeeze Color: {strategy.current_indicators.squeeze_color}")
    print(f"Is Squeezed: {strategy.current_indicators.is_squeezed}")
    print(f"Trend 15m: {strategy.current_indicators.trend_15m}")
    print(f"Trend 1h: {strategy.current_indicators.trend_1h}")
    print(f"Price vs VWAP: {'ABOVE' if candles_15m[-1].close > strategy.current_indicators.vwap else 'BELOW'}")
    
    print(f"\n{'='*80}")
    print(f"CONCLUSION")
    print(f"{'='*80}")
    
    if long_signal or short_signal:
        print(f"✓ SIGNAL EXISTS - Bot should execute trade if margin is sufficient")
    else:
        print(f"✗ NO SIGNAL - Bot is waiting for valid signal")
        print(f"\nPossible reasons:")
        if strategy.current_indicators.adx_15m < config.adx_threshold:
            print(f"  - ADX too low ({strategy.current_indicators.adx_15m:.2f} < {config.adx_threshold})")
        if strategy.current_indicators.rvol < config.rvol_threshold:
            print(f"  - RVOL too low ({strategy.current_indicators.rvol:.2f} < {config.rvol_threshold})")
        if strategy.current_indicators.squeeze_color not in ["green", "maroon"]:
            print(f"  - Squeeze color not favorable (is {strategy.current_indicators.squeeze_color})")

if __name__ == "__main__":
    main()
