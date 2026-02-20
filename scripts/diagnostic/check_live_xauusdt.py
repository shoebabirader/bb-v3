"""Check XAUUSDT indicators in real-time from live bot perspective."""

import sys
import time
from src.config import Config
from src.strategy import StrategyEngine
from src.data_manager import DataManager
from binance.client import Client

def check_live_xauusdt():
    """Check XAUUSDT with live data (WebSocket updates)."""
    
    # Load config
    config = Config.load_from_file()
    
    # Initialize client and data manager
    client = Client(config.api_key, config.api_secret)
    data_manager = DataManager(config, client)
    
    # Initialize strategy
    strategy = StrategyEngine(config)
    
    symbol = "XAUUSDT"
    
    print("=" * 80)
    print(f"LIVE {symbol} INDICATOR CHECK")
    print("=" * 80)
    
    # Fetch initial historical data
    print(f"\nFetching historical data for {symbol}...")
    candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
    candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
    
    candles_5m = None
    candles_4h = None
    
    if config.enable_multi_timeframe:
        candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol)
        candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol)
    
    print(f"Loaded: 15m={len(candles_15m)}, 1h={len(candles_1h)}, 5m={len(candles_5m) if candles_5m else 0}, 4h={len(candles_4h) if candles_4h else 0}")
    
    # Start WebSocket to get live updates
    print(f"\nStarting WebSocket for {symbol}...")
    data_manager.start_websocket_streams(symbol=symbol)
    
    print("Waiting 3 seconds for WebSocket to connect...")
    time.sleep(3)
    
    # Get latest candles from buffer (includes WebSocket updates)
    print("\nGetting latest candles from buffer (with WebSocket updates)...")
    candles_15m = data_manager.get_latest_candles("15m", 200, symbol=symbol)
    candles_1h = data_manager.get_latest_candles("1h", 100, symbol=symbol)
    
    if config.enable_multi_timeframe:
        candles_5m = data_manager.get_latest_candles("5m", 300, symbol=symbol)
        candles_4h = data_manager.get_latest_candles("4h", 50, symbol=symbol)
    
    print(f"Buffer: 15m={len(candles_15m)}, 1h={len(candles_1h)}, 5m={len(candles_5m) if candles_5m else 0}, 4h={len(candles_4h) if candles_4h else 0}")
    
    # Update indicators
    print("\nUpdating indicators with live data...")
    strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
    
    # Display indicators
    print("\n" + "=" * 80)
    print("CURRENT INDICATORS (LIVE)")
    print("=" * 80)
    print(f"Current Price: ${strategy.current_indicators.current_price:.4f}")
    print(f"ADX: {strategy.current_indicators.adx:.2f} (threshold: {config.adx_threshold})")
    print(f"RVOL: {strategy.current_indicators.rvol:.2f} (threshold: {config.rvol_threshold})")
    print(f"Squeeze Value: {strategy.current_indicators.squeeze_value:.4f}")
    print(f"Squeeze Color: {strategy.current_indicators.squeeze_color}")
    print(f"Is Squeezed: {strategy.current_indicators.is_squeezed}")
    print(f"Trend 15m: {strategy.current_indicators.trend_15m}")
    print(f"Trend 1h: {strategy.current_indicators.trend_1h}")
    print(f"Price vs VWAP: {strategy.current_indicators.price_vs_vwap}")
    
    # Check advanced features
    print("\n" + "=" * 80)
    print("ADVANCED FEATURES")
    print("=" * 80)
    
    # Multi-timeframe
    if config.enable_multi_timeframe:
        if strategy.timeframe_analysis:
            print(f"Multi-timeframe alignment: {strategy.timeframe_analysis.alignment_score}/{config.min_timeframe_alignment}")
            print(f"Overall direction: {strategy.timeframe_analysis.overall_direction}")
            print(f"Confidence: {strategy.timeframe_analysis.confidence:.2f}")
        else:
            print("Multi-timeframe: ANALYSIS IS NONE (data missing or insufficient)")
    
    # Regime
    if config.enable_regime_detection and strategy.market_regime_detector:
        print(f"Market regime: {strategy.market_regime_detector.current_regime}")
        if strategy.current_regime_params:
            print(f"Strategy type: {strategy.current_regime_params.strategy_type}")
    
    # Adaptive thresholds
    if config.enable_adaptive_thresholds and strategy.adaptive_threshold_manager:
        thresholds = strategy.adaptive_threshold_manager.get_current_thresholds()
        print(f"Adaptive ADX: {thresholds['adx']:.2f}")
        print(f"Adaptive RVOL: {thresholds['rvol']:.2f}")
    
    # Check for signal
    print("\n" + "=" * 80)
    print("SIGNAL CHECK")
    print("=" * 80)
    
    long_signal = strategy.check_long_entry(symbol)
    short_signal = strategy.check_short_entry(symbol)
    
    if long_signal:
        print(f"✓ LONG SIGNAL at ${long_signal.price:.2f}")
    elif short_signal:
        print(f"✓ SHORT SIGNAL at ${short_signal.price:.2f}")
    else:
        print("✗ No signal")
        
        # Detailed blocking analysis
        print("\nBLOCKING ANALYSIS:")
        
        # Check each condition for LONG
        print("\nLONG entry conditions:")
        print(f"  Price vs VWAP: {strategy.current_indicators.price_vs_vwap} (need ABOVE) {'✓' if strategy.current_indicators.price_vs_vwap == 'ABOVE' else '✗'}")
        print(f"  Trend 15m: {strategy.current_indicators.trend_15m} (need BULLISH) {'✓' if strategy.current_indicators.trend_15m == 'BULLISH' else '✗'}")
        print(f"  Trend 1h: {strategy.current_indicators.trend_1h} (need BULLISH) {'✓' if strategy.current_indicators.trend_1h == 'BULLISH' else '✗'}")
        print(f"  Squeeze value: {strategy.current_indicators.squeeze_value:.2f} (need > 0) {'✓' if strategy.current_indicators.squeeze_value > 0 else '✗'}")
        print(f"  Squeeze color: {strategy.current_indicators.squeeze_color} (need green) {'✓' if strategy.current_indicators.squeeze_color == 'green' else '✗'}")
        
        # Get thresholds
        adx_threshold = config.adx_threshold
        rvol_threshold = config.rvol_threshold
        
        if strategy.adaptive_threshold_manager:
            thresholds = strategy.adaptive_threshold_manager.get_current_thresholds()
            adx_threshold = thresholds['adx']
            rvol_threshold = thresholds['rvol']
        
        if strategy.current_regime_params:
            adx_threshold *= strategy.current_regime_params.threshold_multiplier
            rvol_threshold *= strategy.current_regime_params.threshold_multiplier
        
        print(f"  ADX: {strategy.current_indicators.adx:.2f} (need > {adx_threshold:.2f}) {'✓' if strategy.current_indicators.adx > adx_threshold else '✗'}")
        print(f"  RVOL: {strategy.current_indicators.rvol:.2f} (need > {rvol_threshold:.2f}) {'✓' if strategy.current_indicators.rvol > rvol_threshold else '✗'}")
        
        if config.enable_multi_timeframe and strategy.timeframe_analysis:
            print(f"  Multi-timeframe alignment: {strategy.timeframe_analysis.alignment_score} (need >= {config.min_timeframe_alignment}) {'✓' if strategy.timeframe_analysis.alignment_score >= config.min_timeframe_alignment else '✗'}")
            print(f"  Multi-timeframe direction: {strategy.timeframe_analysis.overall_direction} (need BULLISH) {'✓' if strategy.timeframe_analysis.overall_direction == 'BULLISH' else '✗'}")
        elif config.enable_multi_timeframe:
            print(f"  Multi-timeframe: ✗ (analysis is None - data missing)")
    
    # Stop WebSocket
    print("\nStopping WebSocket...")
    data_manager.stop_websocket_streams()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    try:
        check_live_xauusdt()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
