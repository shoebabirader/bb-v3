"""Diagnose RVOL blocking issue - why signals aren't executing."""
import json
from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine

print("="*70)
print("RVOL BLOCKING DIAGNOSIS")
print("="*70)

# Load config
config = Config.load_from_file('config/config.json')
print(f"\nCurrent RVOL Threshold: {config.rvol_threshold}")
print(f"This means RVOL must be >= {config.rvol_threshold} for signals to trigger")

# Initialize components
client = Client(config.api_key, config.api_secret)
data_manager = DataManager(config, client)

# Check each symbol
symbols = config.portfolio_symbols if config.enable_portfolio_management else [config.symbol]

print(f"\n{'='*70}")
print(f"Checking all {len(symbols)} symbols...")
print(f"{'='*70}\n")

results = []

for symbol in symbols:
    try:
        # Update config for this symbol
        config.symbol = symbol
        
        # Create strategy
        strategy = StrategyEngine(config)
        
        # Fetch data
        candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
        candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
        
        # Update indicators
        strategy.update_indicators(candles_15m, candles_1h)
        
        # Get current indicators
        ind = strategy.current_indicators
        
        # Check signals
        long_signal = strategy.check_long_entry(symbol)
        short_signal = strategy.check_short_entry(symbol)
        
        # Determine blocking reason
        blocking_reasons = []
        
        if ind.adx < config.adx_threshold:
            blocking_reasons.append(f"ADX too low ({ind.adx:.2f} < {config.adx_threshold})")
        
        if ind.rvol < config.rvol_threshold:
            blocking_reasons.append(f"RVOL too low ({ind.rvol:.2f} < {config.rvol_threshold})")
        
        # Store results
        results.append({
            'symbol': symbol,
            'adx': ind.adx,
            'rvol': ind.rvol,
            'adx_ok': ind.adx >= config.adx_threshold,
            'rvol_ok': ind.rvol >= config.rvol_threshold,
            'long_signal': long_signal is not None,
            'short_signal': short_signal is not None,
            'blocking_reasons': blocking_reasons
        })
        
    except Exception as e:
        print(f"Error checking {symbol}: {e}")

# Display results table
print(f"{'Symbol':<12} {'ADX':<8} {'RVOL':<8} {'ADX OK':<8} {'RVOL OK':<9} {'Signal':<8}")
print("-" * 70)

for r in results:
    adx_status = "✓" if r['adx_ok'] else "✗"
    rvol_status = "✓" if r['rvol_ok'] else "✗"
    signal = "LONG" if r['long_signal'] else ("SHORT" if r['short_signal'] else "NONE")
    
    print(f"{r['symbol']:<12} {r['adx']:<8.2f} {r['rvol']:<8.2f} {adx_status:<8} {rvol_status:<9} {signal:<8}")

# Analysis
print(f"\n{'='*70}")
print("ANALYSIS")
print(f"{'='*70}\n")

rvol_blocked = sum(1 for r in results if not r['rvol_ok'])
adx_blocked = sum(1 for r in results if not r['adx_ok'])

print(f"Symbols blocked by RVOL: {rvol_blocked}/{len(results)}")
print(f"Symbols blocked by ADX: {adx_blocked}/{len(results)}")

if rvol_blocked > 0:
    avg_rvol = sum(r['rvol'] for r in results) / len(results)
    max_rvol = max(r['rvol'] for r in results)
    
    print(f"\nCurrent market RVOL levels:")
    print(f"  Average: {avg_rvol:.2f}")
    print(f"  Maximum: {max_rvol:.2f}")
    print(f"  Threshold: {config.rvol_threshold}")
    
    print(f"\n⚠️  ISSUE IDENTIFIED:")
    print(f"   Your RVOL threshold ({config.rvol_threshold}) is too high for current market conditions.")
    print(f"   The market is in a low-volume period.")
    
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"\n   Option 1: Lower RVOL threshold (RECOMMENDED)")
    print(f"   ----------------------------------------")
    print(f"   Edit config/config.json and change:")
    print(f"   \"rvol_threshold\": {config.rvol_threshold}  →  \"rvol_threshold\": 0.3")
    print(f"   ")
    print(f"   This will allow trades when RVOL >= 0.3 (more suitable for current market)")
    
    print(f"\n   Option 2: Wait for higher volume")
    print(f"   --------------------------------")
    print(f"   Keep current threshold and wait for market volume to increase.")
    print(f"   Monitor with: python monitor_live_signals.py")
    
    print(f"\n   Option 3: Disable RVOL filter temporarily")
    print(f"   -----------------------------------------")
    print(f"   Set \"rvol_threshold\": 0.0 to disable RVOL filtering entirely.")
    print(f"   (Not recommended - may lead to poor quality trades)")

print(f"\n{'='*70}")
print("DIAGNOSIS COMPLETE")
print(f"{'='*70}")
