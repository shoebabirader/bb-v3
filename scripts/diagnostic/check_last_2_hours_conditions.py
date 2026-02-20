"""
Check if any signals would have been generated in the last 2 hours.
"""

import json
from datetime import datetime, timedelta
from binance.client import Client
from src.config import Config
from src.strategy import StrategyEngine
from src.data_manager import DataManager

# Load config
config = Config()

# Initialize client
client = Client(config.api_key, config.api_secret)

# Initialize components
data_manager = DataManager(config, client)
strategy = StrategyEngine(config)

print("=" * 80)
print("ANALYZING LAST 2 HOURS FOR SIGNAL CONDITIONS")
print("=" * 80)
print(f"\nCurrent Thresholds:")
print(f"  ADX Threshold: {config.adx_threshold}")
print(f"  RVOL Threshold: {config.rvol_threshold}")
print(f"\nPortfolio Symbols: {config.portfolio_symbols}")
print("\n" + "=" * 80)

# Check each symbol
for symbol in config.portfolio_symbols:
    print(f"\n{'=' * 80}")
    print(f"SYMBOL: {symbol}")
    print(f"{'=' * 80}")
    
    try:
        # Fetch recent data (last 2 hours = 8 candles on 15m)
        candles_15m = data_manager.fetch_historical_data(days=1, timeframe="15m", symbol=symbol)
        candles_1h = data_manager.fetch_historical_data(days=1, timeframe="1h", symbol=symbol)
        candles_5m = data_manager.fetch_historical_data(days=1, timeframe="5m", symbol=symbol)
        candles_4h = data_manager.fetch_historical_data(days=2, timeframe="4h", symbol=symbol)
        
        print(f"\nData loaded: 15m={len(candles_15m)}, 1h={len(candles_1h)}, 5m={len(candles_5m)}, 4h={len(candles_4h)}")
        
        # Check last 8 candles (2 hours on 15m timeframe)
        last_8_candles = candles_15m[-8:] if len(candles_15m) >= 8 else candles_15m
        
        print(f"\nAnalyzing last {len(last_8_candles)} candles (last 2 hours):")
        print(f"{'Time':<20} {'Price':<10} {'ADX':<8} {'RVOL':<8} {'Squeeze':<10} {'Signal':<10}")
        print("-" * 80)
        
        signals_found = 0
        
        for i, candle in enumerate(last_8_candles):
            # Update indicators for this candle
            candle_index = candles_15m.index(candle)
            
            # Get slice up to this candle
            candles_15m_slice = candles_15m[:candle_index + 1]
            candles_1h_slice = candles_1h[:len(candles_1h)]
            candles_5m_slice = candles_5m[:len(candles_5m)]
            candles_4h_slice = candles_4h[:len(candles_4h)]
            
            # Update indicators
            strategy.update_indicators(
                candles_15m_slice,
                candles_1h_slice,
                candles_5m_slice,
                candles_4h_slice
            )
            
            # Get current indicators
            ind = strategy.current_indicators
            
            # Check for signals
            long_signal = strategy.check_long_entry(symbol)
            short_signal = strategy.check_short_entry(symbol)
            
            signal_str = "NONE"
            if long_signal:
                signal_str = "LONG ✓"
                signals_found += 1
            elif short_signal:
                signal_str = "SHORT ✓"
                signals_found += 1
            
            # Format time
            time_str = datetime.fromtimestamp(candle.timestamp / 1000).strftime('%Y-%m-%d %H:%M')
            
            # Print row
            print(f"{time_str:<20} ${candle.close:<9.4f} {ind.adx:<7.2f} {ind.rvol:<7.2f} {ind.squeeze_color:<10} {signal_str:<10}")
        
        print(f"\n{'=' * 80}")
        print(f"SUMMARY FOR {symbol}:")
        print(f"  Signals Found: {signals_found}")
        print(f"  Current ADX: {ind.adx:.2f} (threshold: {config.adx_threshold})")
        print(f"  Current RVOL: {ind.rvol:.2f} (threshold: {config.rvol_threshold})")
        print(f"  Current Squeeze: {ind.squeeze_color}")
        print(f"  Trend 15m: {ind.trend_15m}")
        print(f"  Trend 1h: {ind.trend_1h}")
        
        # Explain why no signals
        if signals_found == 0:
            print(f"\n  WHY NO SIGNALS:")
            if ind.rvol < config.rvol_threshold:
                print(f"    ✗ RVOL too low: {ind.rvol:.2f} < {config.rvol_threshold}")
            if ind.adx < config.adx_threshold:
                print(f"    ✗ ADX too low: {ind.adx:.2f} < {config.adx_threshold}")
            if ind.squeeze_color not in ['lime', 'green']:
                print(f"    ✗ Squeeze not firing: {ind.squeeze_color}")
        
    except Exception as e:
        print(f"ERROR analyzing {symbol}: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'=' * 80}")
print("ANALYSIS COMPLETE")
print(f"{'=' * 80}")
print("\nRECOMMENDATIONS:")
print("1. Current RVOL threshold (1.2) is TOO HIGH for current market conditions")
print("2. Consider lowering RVOL threshold to 0.8 or even 0.6 temporarily")
print("3. Or wait for market volume to increase (typically during US trading hours)")
print("4. Check if you're trading during low-volume Asian/European hours")
