"""Property-based tests for StrategyEngine."""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from src.strategy import StrategyEngine
from src.config import Config
from src.models import Candle, IndicatorState
from typing import List
import time


# Helper function to generate valid candle data
@st.composite
def candle_list(draw, min_candles=50, max_candles=100):
    """Generate a list of valid candles with realistic price movements."""
    num_candles = draw(st.integers(min_value=min_candles, max_value=max_candles))
    
    # Start with a base price
    base_price = draw(st.floats(min_value=1000, max_value=50000))
    base_volume = draw(st.floats(min_value=100, max_value=10000))
    
    candles = []
    current_time = int(time.time() * 1000) - (num_candles * 15 * 60 * 1000)  # 15 min intervals
    
    for i in range(num_candles):
        # Generate OHLC with realistic relationships
        open_price = base_price * draw(st.floats(min_value=0.95, max_value=1.05))
        close_price = open_price * draw(st.floats(min_value=0.98, max_value=1.02))
        high_price = max(open_price, close_price) * draw(st.floats(min_value=1.0, max_value=1.01))
        low_price = min(open_price, close_price) * draw(st.floats(min_value=0.99, max_value=1.0))
        volume = base_volume * draw(st.floats(min_value=0.5, max_value=2.0))
        
        candles.append(Candle(
            timestamp=current_time + (i * 15 * 60 * 1000),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume
        ))
        
        # Update base price for next candle (random walk)
        base_price = close_price
    
    return candles


@st.composite
def candle_list_1h(draw, min_candles=30, max_candles=50):
    """Generate a list of 1-hour candles."""
    num_candles = draw(st.integers(min_value=min_candles, max_value=max_candles))
    
    base_price = draw(st.floats(min_value=1000, max_value=50000))
    base_volume = draw(st.floats(min_value=1000, max_value=50000))
    
    candles = []
    current_time = int(time.time() * 1000) - (num_candles * 60 * 60 * 1000)  # 1 hour intervals
    
    for i in range(num_candles):
        open_price = base_price * draw(st.floats(min_value=0.95, max_value=1.05))
        close_price = open_price * draw(st.floats(min_value=0.98, max_value=1.02))
        high_price = max(open_price, close_price) * draw(st.floats(min_value=1.0, max_value=1.01))
        low_price = min(open_price, close_price) * draw(st.floats(min_value=0.99, max_value=1.0))
        volume = base_volume * draw(st.floats(min_value=0.5, max_value=2.0))
        
        candles.append(Candle(
            timestamp=current_time + (i * 60 * 60 * 1000),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume
        ))
        
        base_price = close_price
    
    return candles


# Feature: binance-futures-bot, Property 16: Long Entry Signal Validity
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
@given(
    candles_15m=candle_list(min_candles=50, max_candles=100),
    candles_1h=candle_list_1h(min_candles=30, max_candles=50)
)
def test_long_entry_signal_validity(candles_15m: List[Candle], candles_1h: List[Candle]):
    """Property 16: Long Entry Signal Validity
    
    For any LONG_ENTRY signal generated, all of the following conditions must be true:
    - 15m price > VWAP
    - 1h trend is bullish
    - Squeeze releases green
    - ADX > 20
    - RVOL > 1.2
    
    Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
    """
    config = Config()
    strategy = StrategyEngine(config)
    
    # Update indicators
    strategy.update_indicators(candles_15m, candles_1h)
    
    # Check for long entry signal
    signal = strategy.check_long_entry()
    
    # If a signal was generated, verify all conditions are met
    if signal is not None:
        assert signal.type == "LONG_ENTRY", "Signal type must be LONG_ENTRY"
        
        # Verify all conditions
        assert strategy.current_indicators.price_vs_vwap == "ABOVE", \
            "Price must be above VWAP for long entry"
        
        assert strategy.current_indicators.trend_1h == "BULLISH", \
            "1h trend must be BULLISH for long entry"
        
        assert strategy.current_indicators.squeeze_color == "green", \
            "Squeeze must release green for long entry"
        
        assert strategy.current_indicators.adx > config.adx_threshold, \
            f"ADX must be > {config.adx_threshold} for long entry"
        
        assert strategy.current_indicators.rvol > config.rvol_threshold, \
            f"RVOL must be > {config.rvol_threshold} for long entry"
        
        # Verify signal has required fields
        assert signal.timestamp > 0, "Signal must have valid timestamp"
        assert signal.price > 0, "Signal must have valid price"
        assert isinstance(signal.indicators, dict), "Signal must have indicators dict"


# Feature: binance-futures-bot, Property 17: Short Entry Signal Validity
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
@given(
    candles_15m=candle_list(min_candles=50, max_candles=100),
    candles_1h=candle_list_1h(min_candles=30, max_candles=50)
)
def test_short_entry_signal_validity(candles_15m: List[Candle], candles_1h: List[Candle]):
    """Property 17: Short Entry Signal Validity
    
    For any SHORT_ENTRY signal generated, all of the following conditions must be true:
    - 15m price < VWAP
    - 1h trend is bearish
    - Squeeze releases maroon
    - ADX > 20
    - RVOL > 1.2
    
    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
    """
    config = Config()
    strategy = StrategyEngine(config)
    
    # Update indicators
    strategy.update_indicators(candles_15m, candles_1h)
    
    # Check for short entry signal
    signal = strategy.check_short_entry()
    
    # If a signal was generated, verify all conditions are met
    if signal is not None:
        assert signal.type == "SHORT_ENTRY", "Signal type must be SHORT_ENTRY"
        
        # Verify all conditions
        assert strategy.current_indicators.price_vs_vwap == "BELOW", \
            "Price must be below VWAP for short entry"
        
        assert strategy.current_indicators.trend_1h == "BEARISH", \
            "1h trend must be BEARISH for short entry"
        
        assert strategy.current_indicators.squeeze_color == "maroon", \
            "Squeeze must release maroon for short entry"
        
        assert strategy.current_indicators.adx > config.adx_threshold, \
            f"ADX must be > {config.adx_threshold} for short entry"
        
        assert strategy.current_indicators.rvol > config.rvol_threshold, \
            f"RVOL must be > {config.rvol_threshold} for short entry"
        
        # Verify signal has required fields
        assert signal.timestamp > 0, "Signal must have valid timestamp"
        assert signal.price > 0, "Signal must have valid price"
        assert isinstance(signal.indicators, dict), "Signal must have indicators dict"


# Feature: binance-futures-bot, Property 18: Signal Completeness
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
@given(
    candles_15m=candle_list(min_candles=50, max_candles=100),
    candles_1h=candle_list_1h(min_candles=30, max_candles=50)
)
def test_signal_completeness(candles_15m: List[Candle], candles_1h: List[Candle]):
    """Property 18: Signal Completeness
    
    For any entry signal (LONG or SHORT), the signal object should contain
    type, timestamp, price, and indicators fields with valid values.
    
    Validates: Requirements 5.6, 6.6
    """
    config = Config()
    strategy = StrategyEngine(config)
    
    # Update indicators
    strategy.update_indicators(candles_15m, candles_1h)
    
    # Check both long and short signals
    long_signal = strategy.check_long_entry()
    short_signal = strategy.check_short_entry()
    
    # Test whichever signal was generated
    for signal in [long_signal, short_signal]:
        if signal is not None:
            # Verify all required fields are present
            assert hasattr(signal, 'type'), "Signal must have 'type' field"
            assert hasattr(signal, 'timestamp'), "Signal must have 'timestamp' field"
            assert hasattr(signal, 'price'), "Signal must have 'price' field"
            assert hasattr(signal, 'indicators'), "Signal must have 'indicators' field"
            
            # Verify field values are valid
            assert signal.type in ["LONG_ENTRY", "SHORT_ENTRY", "EXIT"], \
                "Signal type must be valid"
            assert signal.timestamp > 0, "Timestamp must be positive"
            assert signal.price > 0, "Price must be positive"
            assert isinstance(signal.indicators, dict), "Indicators must be a dictionary"
            assert len(signal.indicators) > 0, "Indicators dict must not be empty"


# Feature: binance-futures-bot, Property 14: Bullish Trend Signal Filtering
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
@given(
    candles_15m=candle_list(min_candles=50, max_candles=100),
    candles_1h=candle_list_1h(min_candles=30, max_candles=50)
)
def test_bullish_trend_signal_filtering(candles_15m: List[Candle], candles_1h: List[Candle]):
    """Property 14: Bullish Trend Signal Filtering
    
    For any market state where the 1-hour trend is bullish, the Signal_Generator
    should only emit LONG_ENTRY signals and never emit SHORT_ENTRY signals.
    
    Validates: Requirements 4.2
    """
    config = Config()
    strategy = StrategyEngine(config)
    
    # Update indicators
    strategy.update_indicators(candles_15m, candles_1h)
    
    # If 1h trend is bullish, check signal filtering
    if strategy.current_indicators.trend_1h == "BULLISH":
        long_signal = strategy.check_long_entry()
        short_signal = strategy.check_short_entry()
        
        # Short signal should never be generated when trend is bullish
        assert short_signal is None, \
            "SHORT_ENTRY signal should not be generated when 1h trend is BULLISH"
        
        # If any signal is generated, it must be long
        if long_signal is not None:
            assert long_signal.type == "LONG_ENTRY", \
                "Only LONG_ENTRY signals allowed when 1h trend is BULLISH"


# Feature: binance-futures-bot, Property 15: Bearish Trend Signal Filtering
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
@given(
    candles_15m=candle_list(min_candles=50, max_candles=100),
    candles_1h=candle_list_1h(min_candles=30, max_candles=50)
)
def test_bearish_trend_signal_filtering(candles_15m: List[Candle], candles_1h: List[Candle]):
    """Property 15: Bearish Trend Signal Filtering
    
    For any market state where the 1-hour trend is bearish, the Signal_Generator
    should only emit SHORT_ENTRY signals and never emit LONG_ENTRY signals.
    
    Validates: Requirements 4.3
    """
    config = Config()
    strategy = StrategyEngine(config)
    
    # Update indicators
    strategy.update_indicators(candles_15m, candles_1h)
    
    # If 1h trend is bearish, check signal filtering
    if strategy.current_indicators.trend_1h == "BEARISH":
        long_signal = strategy.check_long_entry()
        short_signal = strategy.check_short_entry()
        
        # Long signal should never be generated when trend is bearish
        assert long_signal is None, \
            "LONG_ENTRY signal should not be generated when 1h trend is BEARISH"
        
        # If any signal is generated, it must be short
        if short_signal is not None:
            assert short_signal.type == "SHORT_ENTRY", \
                "Only SHORT_ENTRY signals allowed when 1h trend is BEARISH"


# Feature: binance-futures-bot, Property 13: Trend Direction Consistency
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
@given(
    candles_1h=candle_list_1h(min_candles=30, max_candles=50)
)
def test_trend_direction_consistency(candles_1h: List[Candle]):
    """Property 13: Trend Direction Consistency
    
    For any 1-hour candle data with VWAP and momentum indicators, the determined
    trend direction should remain consistent until the next 1-hour candle close.
    
    Validates: Requirements 4.1, 4.4
    """
    config = Config()
    strategy = StrategyEngine(config)
    
    # Generate 15m candles (need them for update_indicators)
    candles_15m = []
    base_price = candles_1h[0].open if candles_1h else 30000
    current_time = int(time.time() * 1000) - (50 * 15 * 60 * 1000)
    
    for i in range(50):
        candles_15m.append(Candle(
            timestamp=current_time + (i * 15 * 60 * 1000),
            open=base_price,
            high=base_price * 1.01,
            low=base_price * 0.99,
            close=base_price,
            volume=1000
        ))
    
    # Update indicators with initial data
    strategy.update_indicators(candles_15m, candles_1h)
    initial_trend = strategy.current_indicators.trend_1h
    
    # Update indicators again with same 1h data (simulating time passing within same 1h candle)
    # Add a few more 15m candles but keep 1h data the same
    for i in range(4):
        candles_15m.append(Candle(
            timestamp=candles_15m[-1].timestamp + (15 * 60 * 1000),
            open=base_price,
            high=base_price * 1.01,
            low=base_price * 0.99,
            close=base_price,
            volume=1000
        ))
    
    strategy.update_indicators(candles_15m, candles_1h)
    updated_trend = strategy.current_indicators.trend_1h
    
    # Trend should remain consistent when 1h data hasn't changed
    assert initial_trend == updated_trend, \
        "Trend direction should remain consistent when 1h candle data hasn't changed"


# ===== INTEGRATION TESTS FOR ADVANCED FEATURES =====

def test_strategy_with_all_features_enabled():
    """Integration test: Full signal generation pipeline with all features enabled.
    
    Tests that the strategy engine works correctly when all advanced features
    are enabled simultaneously.
    
    Validates: Requirements 8.6
    """
    # Create config with all features enabled
    config = Config()
    config.enable_adaptive_thresholds = True
    config.enable_multi_timeframe = True
    config.enable_volume_profile = True
    config.enable_ml_prediction = False  # Disabled as model may not exist
    config.enable_regime_detection = True
    
    # Create strategy engine
    strategy = StrategyEngine(config)
    
    # Verify all components are initialized
    assert strategy.adaptive_threshold_manager is not None
    assert strategy.timeframe_coordinator is not None
    assert strategy.volume_profile_analyzer is not None
    assert strategy.market_regime_detector is not None
    
    # Generate test candles
    candles_15m = _generate_test_candles(100, "15m")
    candles_1h = _generate_test_candles(50, "1h")
    candles_5m = _generate_test_candles(200, "5m")
    candles_4h = _generate_test_candles(30, "4h")
    
    # Update indicators with all timeframes
    strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
    
    # Check that indicators were updated
    assert strategy.current_indicators.current_price > 0
    
    # Try to generate signals (may or may not generate depending on conditions)
    long_signal = strategy.check_long_entry()
    short_signal = strategy.check_short_entry()
    
    # Signals should be either None or valid Signal objects
    if long_signal:
        assert long_signal.type == "LONG_ENTRY"
        assert long_signal.price > 0
        assert 0.0 <= long_signal.confidence <= 1.0
    
    if short_signal:
        assert short_signal.type == "SHORT_ENTRY"
        assert short_signal.price > 0
        assert 0.0 <= short_signal.confidence <= 1.0


def test_strategy_with_individual_features_disabled():
    """Integration test: Strategy works with individual features disabled.
    
    Tests that disabling individual features doesn't break the strategy engine.
    
    Validates: Requirements 8.6
    """
    # Test with each feature disabled individually
    feature_flags = [
        'enable_adaptive_thresholds',
        'enable_multi_timeframe',
        'enable_volume_profile',
        'enable_regime_detection'
    ]
    
    for disabled_feature in feature_flags:
        config = Config()
        # Enable all features
        config.enable_adaptive_thresholds = True
        config.enable_multi_timeframe = True
        config.enable_volume_profile = True
        config.enable_regime_detection = True
        config.enable_ml_prediction = False
        
        # Disable one feature
        setattr(config, disabled_feature, False)
        
        # Create strategy engine
        strategy = StrategyEngine(config)
        
        # Generate test candles
        candles_15m = _generate_test_candles(100, "15m")
        candles_1h = _generate_test_candles(50, "1h")
        candles_5m = _generate_test_candles(200, "5m")
        candles_4h = _generate_test_candles(30, "4h")
        
        # Update indicators - should not raise exceptions
        strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
        
        # Check signals - should not raise exceptions
        long_signal = strategy.check_long_entry()
        short_signal = strategy.check_short_entry()
        
        # Verify strategy still works
        assert strategy.current_indicators.current_price > 0


def test_strategy_with_no_advanced_features():
    """Integration test: Strategy works with all advanced features disabled.
    
    Tests backward compatibility - strategy should work with all features off.
    
    Validates: Requirements 8.6
    """
    config = Config()
    config.enable_adaptive_thresholds = False
    config.enable_multi_timeframe = False
    config.enable_volume_profile = False
    config.enable_ml_prediction = False
    config.enable_regime_detection = False
    
    strategy = StrategyEngine(config)
    
    # Verify no advanced components are initialized
    assert strategy.adaptive_threshold_manager is None
    assert strategy.timeframe_coordinator is None
    assert strategy.volume_profile_analyzer is None
    assert strategy.market_regime_detector is None
    assert strategy.ml_predictor is None
    
    # Generate test candles
    candles_15m = _generate_test_candles(100, "15m")
    candles_1h = _generate_test_candles(50, "1h")
    
    # Update indicators (without optional timeframes)
    strategy.update_indicators(candles_15m, candles_1h)
    
    # Check that basic functionality still works
    assert strategy.current_indicators.current_price > 0
    
    # Try to generate signals
    long_signal = strategy.check_long_entry()
    short_signal = strategy.check_short_entry()
    
    # Should work without errors


def test_adaptive_thresholds_integration():
    """Integration test: Adaptive thresholds affect signal generation.
    
    Tests that adaptive threshold manager properly adjusts thresholds
    and those adjustments are used in signal generation.
    
    Validates: Requirements 1.6
    """
    config = Config()
    config.enable_adaptive_thresholds = True
    
    strategy = StrategyEngine(config)
    
    # Generate test candles with high volatility
    candles_15m = _generate_high_volatility_candles(100)
    candles_1h = _generate_test_candles(50, "1h")
    
    # Update indicators
    strategy.update_indicators(candles_15m, candles_1h)
    
    # Get current thresholds
    if strategy.adaptive_threshold_manager:
        thresholds = strategy.adaptive_threshold_manager.get_current_thresholds()
        
        # Thresholds should be within configured bounds
        assert config.adaptive_threshold_min_adx <= thresholds['adx'] <= config.adaptive_threshold_max_adx
        assert config.adaptive_threshold_min_rvol <= thresholds['rvol'] <= config.adaptive_threshold_max_rvol


def test_volume_profile_size_adjustment():
    """Integration test: Volume profile affects position sizing.
    
    Tests that volume profile analyzer properly identifies low volume areas
    and returns appropriate size adjustments.
    
    Validates: Requirements 3.4, 3.5, 3.6
    """
    config = Config()
    config.enable_volume_profile = True
    
    strategy = StrategyEngine(config)
    
    # Generate test candles
    candles_15m = _generate_test_candles(100, "15m")
    candles_1h = _generate_test_candles(50, "1h")
    
    # Update indicators
    strategy.update_indicators(candles_15m, candles_1h)
    
    # Get volume profile size adjustment
    size_adjustment = strategy.get_volume_profile_size_adjustment()
    
    # Size adjustment should be between 0.5 and 1.0
    assert 0.5 <= size_adjustment <= 1.0


# Helper functions for test data generation

def _generate_test_candles(count: int, timeframe: str) -> List[Candle]:
    """Generate test candles with realistic price movements."""
    candles = []
    base_price = 30000.0
    base_volume = 1000.0
    
    # Determine interval in milliseconds
    intervals = {
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000
    }
    interval = intervals.get(timeframe, 15 * 60 * 1000)
    
    current_time = int(time.time() * 1000) - (count * interval)
    
    for i in range(count):
        # Generate OHLC with realistic relationships
        open_price = base_price * (1.0 + (i % 10 - 5) * 0.001)
        close_price = open_price * (1.0 + (i % 7 - 3) * 0.002)
        high_price = max(open_price, close_price) * 1.005
        low_price = min(open_price, close_price) * 0.995
        volume = base_volume * (1.0 + (i % 5) * 0.2)
        
        candles.append(Candle(
            timestamp=current_time + (i * interval),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume
        ))
        
        base_price = close_price
    
    return candles


def _generate_high_volatility_candles(count: int) -> List[Candle]:
    """Generate test candles with high volatility."""
    candles = []
    base_price = 30000.0
    base_volume = 1000.0
    
    current_time = int(time.time() * 1000) - (count * 15 * 60 * 1000)
    
    for i in range(count):
        # Generate OHLC with high volatility
        open_price = base_price * (1.0 + (i % 10 - 5) * 0.01)  # 1% swings
        close_price = open_price * (1.0 + (i % 7 - 3) * 0.02)  # 2% swings
        high_price = max(open_price, close_price) * 1.02
        low_price = min(open_price, close_price) * 0.98
        volume = base_volume * (1.0 + (i % 5) * 0.5)
        
        candles.append(Candle(
            timestamp=current_time + (i * 15 * 60 * 1000),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume
        ))
        
        base_price = close_price
    
    return candles
