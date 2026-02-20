#!/usr/bin/env python3
"""
Diagnostic script to check what's blocking signal generation in real-time.
"""

import sys
import time
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from src.logger import TradingLogger

def main():
    print("=" * 80)
    print("SIGNAL BLOCKER DIAGNOSTIC")
    print("=" * 80)
    print()
    
    # Load config
    config = Config("config/config.json")
    print(f"✓ Config loaded: {config.symbol}")
    print(f"  - Mode: {config.run_mode}")
    print(f"  - ADX Threshold: {config.adx_threshold}")
    print(f"  - RVOL Threshold: {config.rvol_threshold}")
    print(f"  - Regime Detection: {config.enable_regime_detection}")
    print(f"  - Multi-Timeframe: {config.enable_multi_timeframe}")
    print(f"  - ML Prediction: {config.enable_ml_prediction}")
    print()
    
    # Initialize components
    logger = TradingLogger(config)
    data_manager = DataManager(config, logger)
    strategy_obj = StrategyEngine(config, logger)
    
    print("✓ Components initialized")
    print()
    
    # Fetch data
    print("Fetching market data...")
    data_manager.fetch_historical_data(days=7, timeframe="15m")
    data_manager.fetch_historical_data(days=7, timeframe="1h")
    
    if config.enable_multi_timeframe:
        data_manager.fetch_historical_data(days=7, timeframe="5m")
        data_manager.fetch_historical_data(days=7, timeframe="4h")
    
    print("✓ Data fetched")
    print()
    
    # Get candles
    candles_15m = data_manager.get_latest_candles("15m", 200)
    candles_1h = data_manager.get_latest_candles("1h", 100)
    candles_5m = None
    candles_4h = None
    
    if config.enable_multi_timeframe:
        candles_5m = data_manager.get_latest_candles("5m", 300)
        candles_4h = data_manager.get_latest_candles("4h", 50)
    
    print(f"✓ Candles retrieved:")
    print(f"  - 15m: {len(candles_15m)} candles")
    print(f"  - 1h: {len(candles_1h)} candles")
    if candles_5m:
        print(f"  - 5m: {len(candles_5m)} candles")
    if candles_4h:
        print(f"  - 4h: {len(candles_4h)} candles")
    print()
    
    # Update indicators
    print("Updating indicators...")
    strategy_obj.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
    print("✓ Indicators updated")
    print()
    
    # Get current state
    indicators = strategy_obj.current_indicators
    current_price = indicators.current_price
    
    print("=" * 80)
    print("CURRENT MARKET STATE")
    print("=" * 80)
    print(f"Price: ${current_price:.4f}")
    print(f"Trend 15m: {indicators.trend_15m}")
    print(f"Trend 1h: {indicators.trend_1h}")
    print(f"Price vs VWAP: {indicators.price_vs_vwap}")
    print(f"ADX: {indicators.adx:.2f}")
    print(f"RVOL: {indicators.rvol:.2f}")
    print(f"Squeeze Value: {indicators.squeeze_value:.4f}")
    print(f"Squeeze Color: {indicators.squeeze_color}")
    print()
    
    # Check regime if enabled
    if strategy_obj.market_regime_detector and strategy_obj.current_regime_params:
        print("REGIME DETECTION:")
        print(f"  - Regime: {strategy_obj.current_regime_params.regime}")
        print(f"  - Strategy Type: {strategy_obj.current_regime_params.strategy_type}")
        print(f"  - Threshold Multiplier: {strategy_obj.current_regime_params.threshold_multiplier}")
        print()
    
    # Check multi-timeframe if enabled
    if strategy_obj.timeframe_coordinator and strategy_obj.timeframe_analysis:
        print("MULTI-TIMEFRAME ANALYSIS:")
        print(f"  - Overall Direction: {strategy_obj.timeframe_analysis.overall_direction}")
        print(f"  - Alignment Score: {strategy_obj.timeframe_analysis.alignment_score}")
        print(f"  - Confidence: {strategy_obj.timeframe_analysis.confidence:.2f}")
        print(f"  - Min Required: {config.min_timeframe_alignment}")
        print()
    
    # Check ML if enabled
    if strategy_obj.ml_predictor and strategy_obj.ml_predictor.enabled:
        print("ML PREDICTION:")
        print(f"  - Prediction: {strategy_obj.ml_prediction:.4f}")
        print(f"  - High Confidence Threshold: {config.ml_high_confidence_threshold}")
        print(f"  - Low Confidence Threshold: {config.ml_low_confidence_threshold}")
        print()
    
    # Check adaptive thresholds if enabled
    if strategy_obj.adaptive_threshold_manager:
        thresholds = strategy_obj.adaptive_threshold_manager.get_current_thresholds()
        print("ADAPTIVE THRESHOLDS:")
        print(f"  - ADX: {thresholds['adx']:.2f} (base: {config.adx_threshold})")
        print(f"  - RVOL: {thresholds['rvol']:.2f} (base: {config.rvol_threshold})")
        print()
    
    # Now check what's blocking signals
    print("=" * 80)
    print("SIGNAL GENERATION CHECK - LONG ENTRY")
    print("=" * 80)
    
    # Get thresholds
    adx_threshold = config.adx_threshold
    rvol_threshold = config.rvol_threshold
    
    if strategy_obj.adaptive_threshold_manager:
        thresholds = strategy_obj.adaptive_threshold_manager.get_current_thresholds()
        adx_threshold = thresholds['adx']
        rvol_threshold = thresholds['rvol']
    
    if strategy_obj.current_regime_params:
        adx_threshold *= strategy_obj.current_regime_params.threshold_multiplier
        rvol_threshold *= strategy_obj.current_regime_params.threshold_multiplier
    
    # Check each condition
    checks = {
        "Price ABOVE VWAP": indicators.price_vs_vwap == "ABOVE",
        "15m Trend BULLISH": indicators.trend_15m == "BULLISH",
        "1h Trend BULLISH": indicators.trend_1h == "BULLISH",
        "Squeeze > 0": indicators.squeeze_value > 0,
        "Squeeze Color GREEN": indicators.squeeze_color == "green",
        f"ADX > {adx_threshold:.2f}": indicators.adx > adx_threshold,
        f"RVOL > {rvol_threshold:.2f}": indicators.rvol > rvol_threshold
    }
    
    passed = 0
    failed = 0
    
    for condition, result in checks.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {condition}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print()
    print(f"Summary: {passed}/{len(checks)} conditions met")
    
    # Check regime blocker
    if strategy_obj.market_regime_detector and strategy_obj.current_regime_params:
        if strategy_obj.current_regime_params.strategy_type == "NONE":
            print("⚠️  BLOCKED: Regime is UNCERTAIN (strategy_type = NONE)")
            failed += 1
    
    # Check multi-timeframe blocker
    if strategy_obj.timeframe_coordinator and strategy_obj.timeframe_analysis:
        if strategy_obj.timeframe_analysis.alignment_score < config.min_timeframe_alignment:
            print(f"⚠️  BLOCKED: Timeframe alignment too low ({strategy_obj.timeframe_analysis.alignment_score} < {config.min_timeframe_alignment})")
            failed += 1
        if strategy_obj.timeframe_analysis.overall_direction != "BULLISH":
            print(f"⚠️  BLOCKED: Overall direction is {strategy_obj.timeframe_analysis.overall_direction}, need BULLISH")
            failed += 1
    
    # Check ML blocker
    if strategy_obj.ml_predictor and strategy_obj.ml_predictor.enabled:
        if strategy_obj.ml_prediction < config.ml_low_confidence_threshold:
            print(f"⚠️  BLOCKED: ML prediction too low ({strategy_obj.ml_prediction:.4f} < {config.ml_low_confidence_threshold})")
            failed += 1
    
    print()
    
    # Try to generate signal
    long_signal = strategy_obj.check_long_entry()
    short_signal = strategy_obj.check_short_entry()
    
    if long_signal:
        print("✓ LONG SIGNAL GENERATED!")
        print(f"  - Price: ${long_signal.price:.4f}")
        print(f"  - Confidence: {long_signal.confidence:.2f}")
    elif short_signal:
        print("✓ SHORT SIGNAL GENERATED!")
        print(f"  - Price: ${short_signal.price:.4f}")
        print(f"  - Confidence: {short_signal.confidence:.2f}")
    else:
        print("✗ NO SIGNAL GENERATED")
        print()
        print("REASON: One or more conditions not met (see above)")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
