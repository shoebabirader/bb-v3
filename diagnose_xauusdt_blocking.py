"""Diagnose why XAUUSDT signal is being blocked despite meeting all basic criteria."""

import sys
from src.config import Config
from src.strategy import StrategyEngine
from src.data_manager import DataManager
from binance.client import Client

def diagnose_xauusdt():
    """Check what's blocking XAUUSDT signal."""
    
    # Load config
    config = Config.load_from_file()
    
    # Initialize client and data manager
    client = Client(config.api_key, config.api_secret)
    data_manager = DataManager(config, client)
    
    # Initialize strategy
    strategy = StrategyEngine(config)
    
    print("=" * 80)
    print("XAUUSDT SIGNAL BLOCKING DIAGNOSIS")
    print("=" * 80)
    
    # Fetch data for XAUUSDT
    symbol = "XAUUSDT"
    print(f"\nFetching data for {symbol}...")
    
    candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
    candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
    
    candles_5m = None
    candles_4h = None
    
    if config.enable_multi_timeframe:
        print("Multi-timeframe enabled, fetching 5m and 4h data...")
        candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol)
        candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol)
        print(f"  5m candles: {len(candles_5m)}")
        print(f"  4h candles: {len(candles_4h)}")
    
    print(f"  15m candles: {len(candles_15m)}")
    print(f"  1h candles: {len(candles_1h)}")
    
    # Update indicators
    print("\nUpdating indicators...")
    strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
    
    # Check basic indicators
    print("\n" + "=" * 80)
    print("BASIC INDICATORS (from your output)")
    print("=" * 80)
    print(f"ADX: {strategy.current_indicators.adx:.2f} (threshold: {config.adx_threshold})")
    print(f"RVOL: {strategy.current_indicators.rvol:.2f} (threshold: {config.rvol_threshold})")
    print(f"Squeeze Value: {strategy.current_indicators.squeeze_value:.4f}")
    print(f"Squeeze Color: {strategy.current_indicators.squeeze_color}")
    print(f"Trend 15m: {strategy.current_indicators.trend_15m}")
    print(f"Trend 1h: {strategy.current_indicators.trend_1h}")
    print(f"Price vs VWAP: {strategy.current_indicators.price_vs_vwap}")
    
    # Check advanced features
    print("\n" + "=" * 80)
    print("ADVANCED FEATURES CHECK")
    print("=" * 80)
    
    # 1. ML Prediction
    print("\n1. ML PREDICTION:")
    print(f"   Enabled: {config.enable_ml_prediction}")
    if strategy.ml_predictor and strategy.ml_predictor.enabled:
        print(f"   ML Prediction: {strategy.ml_prediction:.4f}")
        print(f"   Low confidence threshold: {config.ml_low_confidence_threshold}")
        if strategy.ml_prediction < config.ml_low_confidence_threshold:
            print(f"   ❌ BLOCKING: ML prediction {strategy.ml_prediction:.4f} < {config.ml_low_confidence_threshold}")
        else:
            print(f"   ✓ PASS: ML prediction is acceptable")
    else:
        print("   ✓ PASS: ML prediction disabled or not active")
    
    # 2. Market Regime
    print("\n2. MARKET REGIME:")
    print(f"   Enabled: {config.enable_regime_detection}")
    if strategy.market_regime_detector and strategy.current_regime_params:
        print(f"   Current regime: {strategy.market_regime_detector.current_regime}")
        print(f"   Strategy type: {strategy.current_regime_params.strategy_type}")
        if strategy.current_regime_params.strategy_type == "NONE":
            print(f"   ❌ BLOCKING: Regime strategy type is NONE (UNCERTAIN regime)")
        else:
            print(f"   ✓ PASS: Regime allows trading")
    else:
        print("   ✓ PASS: Regime detection disabled or not active")
    
    # 3. Multi-timeframe Alignment
    print("\n3. MULTI-TIMEFRAME ALIGNMENT:")
    print(f"   Enabled: {config.enable_multi_timeframe}")
    if strategy.timeframe_coordinator and strategy.timeframe_analysis:
        print(f"   Alignment score: {strategy.timeframe_analysis.alignment_score}")
        print(f"   Min required: {config.min_timeframe_alignment}")
        print(f"   Overall direction: {strategy.timeframe_analysis.overall_direction}")
        
        if strategy.timeframe_analysis.alignment_score < config.min_timeframe_alignment:
            print(f"   ❌ BLOCKING: Alignment score {strategy.timeframe_analysis.alignment_score} < {config.min_timeframe_alignment}")
        elif strategy.timeframe_analysis.overall_direction != "BULLISH":
            print(f"   ❌ BLOCKING: Overall direction is {strategy.timeframe_analysis.overall_direction}, not BULLISH")
        else:
            print(f"   ✓ PASS: Multi-timeframe alignment is good")
    else:
        if config.enable_multi_timeframe:
            print("   ❌ BLOCKING: Multi-timeframe enabled but timeframe_analysis is None!")
            print("   This means 5m or 4h data is missing or insufficient")
        else:
            print("   ✓ PASS: Multi-timeframe disabled")
    
    # 4. Adaptive Thresholds
    print("\n4. ADAPTIVE THRESHOLDS:")
    print(f"   Enabled: {config.enable_adaptive_thresholds}")
    if strategy.adaptive_threshold_manager:
        thresholds = strategy.adaptive_threshold_manager.get_current_thresholds()
        print(f"   Adaptive ADX threshold: {thresholds['adx']:.2f}")
        print(f"   Adaptive RVOL threshold: {thresholds['rvol']:.2f}")
        
        if strategy.current_indicators.adx < thresholds['adx']:
            print(f"   ❌ BLOCKING: ADX {strategy.current_indicators.adx:.2f} < {thresholds['adx']:.2f}")
        elif strategy.current_indicators.rvol < thresholds['rvol']:
            print(f"   ❌ BLOCKING: RVOL {strategy.current_indicators.rvol:.2f} < {thresholds['rvol']:.2f}")
        else:
            print(f"   ✓ PASS: Adaptive thresholds met")
    else:
        print("   ✓ PASS: Adaptive thresholds disabled")
    
    # Try to generate signal
    print("\n" + "=" * 80)
    print("SIGNAL GENERATION TEST")
    print("=" * 80)
    
    signal = strategy.check_long_entry(symbol)
    
    if signal:
        print(f"✓ SIGNAL GENERATED: {signal.type} at ${signal.price:.2f}")
    else:
        print("✗ NO SIGNAL GENERATED")
        print("\nThe blocker is one of the advanced features checked above.")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    
    # Provide specific recommendation
    if config.enable_multi_timeframe and (not strategy.timeframe_analysis):
        print("❌ ISSUE: Multi-timeframe is enabled but timeframe_analysis is None")
        print("   This is the most likely blocker.")
        print("\n   SOLUTIONS:")
        print("   1. Disable multi-timeframe: Set 'enable_multi_timeframe': false in config.json")
        print("   2. Or ensure 5m and 4h data is being fetched correctly")
    elif strategy.timeframe_coordinator and strategy.timeframe_analysis:
        if strategy.timeframe_analysis.alignment_score < config.min_timeframe_alignment:
            print("❌ ISSUE: Multi-timeframe alignment score too low")
            print(f"   Current: {strategy.timeframe_analysis.alignment_score}, Required: {config.min_timeframe_alignment}")
            print("\n   SOLUTIONS:")
            print(f"   1. Lower min_timeframe_alignment to {strategy.timeframe_analysis.alignment_score} in config.json")
            print("   2. Or disable multi-timeframe: Set 'enable_multi_timeframe': false")
        elif strategy.timeframe_analysis.overall_direction != "BULLISH":
            print("❌ ISSUE: Multi-timeframe overall direction is not BULLISH")
            print(f"   Current: {strategy.timeframe_analysis.overall_direction}")
            print("\n   SOLUTION:")
            print("   Disable multi-timeframe: Set 'enable_multi_timeframe': false in config.json")
    elif strategy.market_regime_detector and strategy.current_regime_params:
        if strategy.current_regime_params.strategy_type == "NONE":
            print("❌ ISSUE: Market regime is UNCERTAIN (strategy type NONE)")
            print("\n   SOLUTION:")
            print("   Disable regime detection: Set 'enable_regime_detection': false in config.json")
    else:
        print("Check the advanced features output above to identify the blocker.")

if __name__ == "__main__":
    try:
        diagnose_xauusdt()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
