"""Diagnose why V3 strategy is not executing any trades."""

import sys
from binance.client import Client
from src.config import Config
from src.strategy import StrategyEngine
from src.data_manager import DataManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Check what's blocking trades in V3 strategy."""
    
    # Load config
    config = Config()
    
    print("\n" + "="*80)
    print("V3 STRATEGY DIAGNOSTIC - WHY NO TRADES?")
    print("="*80)
    
    print("\n📊 CURRENT V3 SETTINGS:")
    print(f"  ADX Threshold: {config.adx_threshold}")
    print(f"  RVOL Threshold: {config.rvol_threshold}")
    print(f"  Min Timeframe Alignment: {config.min_timeframe_alignment}/4")
    print(f"  Stop Loss: {config.stop_loss_atr_multiplier}x ATR")
    print(f"  Take Profit: {config.take_profit_pct*100}%")
    
    # Initialize client
    client = Client(config.api_key, config.api_secret)
    data_mgr = DataManager(config, client)
    strategy = StrategyEngine(config)
    
    # Test each symbol
    symbols = config.portfolio_symbols
    
    print(f"\n🔍 TESTING {len(symbols)} SYMBOLS OVER 90 DAYS...")
    print("-"*80)
    
    total_opportunities = 0
    blocking_reasons = {
        'adx_too_low': 0,
        'rvol_too_low': 0,
        'timeframe_misalignment': 0,
        'momentum_exhaustion': 0,
        'no_signal': 0
    }
    
    for symbol in symbols:
        print(f"\n📈 Testing {symbol}...")
        
        # Temporarily change symbol
        original_symbol = config.symbol
        config.symbol = symbol
        
        try:
            # Fetch data
            candles_15m = data_mgr.fetch_historical_data(days=90, timeframe='15m')
            candles_1h = data_mgr.fetch_historical_data(days=90, timeframe='1h')
            candles_5m = data_mgr.fetch_historical_data(days=90, timeframe='5m')
            candles_4h = data_mgr.fetch_historical_data(days=90, timeframe='4h')
            
            print(f"  Fetched: {len(candles_15m)} 15m, {len(candles_1h)} 1h, {len(candles_5m)} 5m, {len(candles_4h)} 4h candles")
            
            # Scan through candles
            opportunities = 0
            min_candles = 50
            
            for i in range(min_candles, len(candles_15m)):
                current_candles_15m = candles_15m[max(0, i-200):i+1]
                current_1h_index = min(i // 4, len(candles_1h) - 1)
                current_candles_1h = candles_1h[max(0, current_1h_index-100):current_1h_index+1]
                
                # Get synchronized 5m and 4h
                current_candles_5m = None
                current_candles_4h = None
                
                if len(candles_5m) > 0:
                    idx_5m = min(i * 3, len(candles_5m) - 1)
                    current_candles_5m = candles_5m[max(0, idx_5m-300):idx_5m+1]
                
                if len(candles_4h) > 0:
                    idx_4h = min(i // 16, len(candles_4h) - 1)
                    current_candles_4h = candles_4h[max(0, idx_4h-50):idx_4h+1]
                
                # Update indicators
                strategy.update_indicators(
                    current_candles_15m,
                    current_candles_1h,
                    current_candles_5m,
                    current_candles_4h
                )
                
                # Check signals
                long_signal = strategy.check_long_entry()
                short_signal = strategy.check_short_entry()
                
                if long_signal or short_signal:
                    opportunities += 1
                else:
                    # Diagnose why no signal
                    indicators = strategy.current_indicators
                    
                    # Check ADX
                    if indicators.adx_15m < config.adx_threshold:
                        blocking_reasons['adx_too_low'] += 1
                    
                    # Check RVOL
                    if indicators.rvol_15m < config.rvol_threshold:
                        blocking_reasons['rvol_too_low'] += 1
                    
                    # Check timeframe alignment (simplified check)
                    if hasattr(strategy, 'timeframe_coordinator') and strategy.timeframe_coordinator:
                        alignment = strategy.timeframe_coordinator.get_alignment_score()
                        if alignment < config.min_timeframe_alignment:
                            blocking_reasons['timeframe_misalignment'] += 1
            
            print(f"  ✅ Found {opportunities} potential trade opportunities")
            total_opportunities += opportunities
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Restore original symbol
        config.symbol = original_symbol
    
    print("\n" + "="*80)
    print("📊 DIAGNOSTIC RESULTS")
    print("="*80)
    
    print(f"\n🎯 Total Trade Opportunities Found: {total_opportunities}")
    
    if total_opportunities == 0:
        print("\n❌ PROBLEM: Strategy is TOO STRICT - No trades in 90 days!")
        print("\n🔧 BLOCKING REASONS (sample of 1000 candles per symbol):")
        total_blocks = sum(blocking_reasons.values())
        if total_blocks > 0:
            for reason, count in sorted(blocking_reasons.items(), key=lambda x: x[1], reverse=True):
                pct = (count / total_blocks) * 100
                print(f"  {reason}: {count} ({pct:.1f}%)")
        
        print("\n💡 RECOMMENDED ADJUSTMENTS:")
        print("\n  Option 1: MODERATE (Recommended)")
        print("  {")
        print('    "adx_threshold": 25.0,  // Down from 30')
        print('    "rvol_threshold": 1.2,   // Down from 1.5')
        print('    "min_timeframe_alignment": 3  // Down from 4')
        print("  }")
        print("  Expected: 10-20 trades in 90 days")
        
        print("\n  Option 2: BALANCED")
        print("  {")
        print('    "adx_threshold": 27.0,')
        print('    "rvol_threshold": 1.3,')
        print('    "min_timeframe_alignment": 3')
        print("  }")
        print("  Expected: 5-15 trades in 90 days")
        
        print("\n  Option 3: CONSERVATIVE (Keep strict but allow 3/4 timeframes)")
        print("  {")
        print('    "adx_threshold": 30.0,  // Keep')
        print('    "rvol_threshold": 1.5,   // Keep')
        print('    "min_timeframe_alignment": 3  // Down from 4')
        print("  }")
        print("  Expected: 3-10 trades in 90 days")
        
    else:
        print(f"\n✅ Strategy found {total_opportunities} opportunities")
        print("   This should result in actual trades in backtest")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
