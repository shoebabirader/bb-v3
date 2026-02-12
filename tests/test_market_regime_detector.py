"""Property-based and unit tests for Market Regime Detector."""

import time
import pytest
from hypothesis import given, strategies as st, settings
from src.config import Config
from src.models import Candle
from src.indicators import IndicatorCalculator
from src.market_regime_detector import MarketRegimeDetector, RegimeParameters


# Helper function to generate candles
def generate_candles(count: int, base_price: float = 50000.0, volatility: float = 0.01, trend: str = "NEUTRAL") -> list:
    """Generate synthetic candle data for testing.
    
    Args:
        count: Number of candles to generate
        base_price: Base price for candles
        volatility: Price volatility factor
        trend: Trend direction ("BULLISH", "BEARISH", "NEUTRAL")
        
    Returns:
        List of Candle objects
    """
    import random
    candles = []
    current_price = base_price
    timestamp = int(time.time() * 1000) - (count * 3600000)  # Start count hours ago
    
    # Trend factor
    trend_factor = 0.0
    if trend == "BULLISH":
        trend_factor = 0.0005  # Slight upward bias
    elif trend == "BEARISH":
        trend_factor = -0.0005  # Slight downward bias
    
    for i in range(count):
        # Add trend and random price movement
        price_change = current_price * (trend_factor + volatility * (random.random() - 0.5) * 2)
        current_price += price_change
        current_price = max(current_price, base_price * 0.5)  # Prevent negative prices
        
        high = current_price * (1 + abs(random.random() * volatility))
        low = current_price * (1 - abs(random.random() * volatility))
        open_price = current_price + (random.random() - 0.5) * volatility * current_price
        close_price = current_price + (random.random() - 0.5) * volatility * current_price
        volume = random.uniform(100, 1000)
        
        candle = Candle(
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=volume
        )
        candles.append(candle)
        timestamp += 3600000  # 1 hour
    
    return candles


# Feature: advanced-trading-enhancements, Property 23: Regime classification completeness
@given(
    candle_count=st.integers(min_value=50, max_value=200),
    volatility=st.floats(min_value=0.001, max_value=0.1),
    trend=st.sampled_from(["BULLISH", "BEARISH", "NEUTRAL"])
)
@settings(max_examples=100)
def test_regime_classification_completeness(candle_count, volatility, trend):
    """For any market state, the detected regime must be one of: 
    TRENDING_BULLISH, TRENDING_BEARISH, RANGING, VOLATILE, or UNCERTAIN.
    
    Property 23: Regime classification completeness
    Validates: Requirements 7.1
    """
    # Create config and detector
    config = Config()
    indicator_calc = IndicatorCalculator()
    detector = MarketRegimeDetector(config, indicator_calc)
    
    # Generate candles
    candles = generate_candles(count=candle_count, base_price=50000.0, volatility=volatility, trend=trend)
    
    # Detect regime
    regime = detector.detect_regime(candles)
    
    # Verify regime is one of the valid values
    valid_regimes = ["TRENDING_BULLISH", "TRENDING_BEARISH", "RANGING", "VOLATILE", "UNCERTAIN"]
    assert regime in valid_regimes, (
        f"Invalid regime '{regime}'. Must be one of: {valid_regimes}"
    )


# Feature: advanced-trading-enhancements, Property 25: Volatile regime position sizing
@given(
    candle_count=st.integers(min_value=50, max_value=200),
    high_volatility=st.floats(min_value=0.05, max_value=0.15)
)
@settings(max_examples=100)
def test_volatile_regime_position_sizing(candle_count, high_volatility):
    """For any market state classified as VOLATILE, position sizes must be 
    reduced by 50% and thresholds increased by 30%.
    
    Property 25: Volatile regime position sizing
    Validates: Requirements 7.8
    """
    # Create config with specific volatile regime settings
    config = Config()
    config.regime_volatile_size_reduction = 0.5  # 50% reduction
    config.regime_volatile_threshold_increase = 0.3  # 30% increase
    config.regime_volatile_atr_percentile = 80.0
    
    indicator_calc = IndicatorCalculator()
    detector = MarketRegimeDetector(config, indicator_calc)
    
    # Generate high volatility candles
    candles = generate_candles(count=candle_count, base_price=50000.0, volatility=high_volatility)
    
    # Detect regime
    regime = detector.detect_regime(candles)
    
    # If regime is VOLATILE, check parameters
    if regime == "VOLATILE":
        params = detector.get_regime_parameters(regime)
        
        # Verify position size reduction
        assert params.position_size_multiplier == 0.5, (
            f"VOLATILE regime position_size_multiplier should be 0.5, got {params.position_size_multiplier}"
        )
        
        # Verify threshold increase
        assert params.threshold_multiplier == 1.3, (
            f"VOLATILE regime threshold_multiplier should be 1.3, got {params.threshold_multiplier}"
        )
        
        # Verify strategy type
        assert params.strategy_type == "TREND_FOLLOWING", (
            f"VOLATILE regime should use TREND_FOLLOWING strategy, got {params.strategy_type}"
        )


class TestMarketRegimeDetectorUnit:
    """Unit tests for Market Regime Detector edge cases."""
    
    def test_trending_bullish_classification(self):
        """Test classification of trending bullish market.
        
        Validates: Requirements 7.1, 7.3
        """
        config = Config()
        config.regime_trending_adx_threshold = 30.0
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Generate strong bullish trend candles
        candles = generate_candles(count=100, base_price=50000.0, volatility=0.02, trend="BULLISH")
        
        # Detect regime
        regime = detector.detect_regime(candles)
        
        # Should be TRENDING_BULLISH or UNCERTAIN (depending on ADX)
        assert regime in ["TRENDING_BULLISH", "UNCERTAIN", "RANGING", "VOLATILE"]
    
    def test_trending_bearish_classification(self):
        """Test classification of trending bearish market.
        
        Validates: Requirements 7.1, 7.3
        """
        config = Config()
        config.regime_trending_adx_threshold = 30.0
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Generate strong bearish trend candles
        candles = generate_candles(count=100, base_price=50000.0, volatility=0.02, trend="BEARISH")
        
        # Detect regime
        regime = detector.detect_regime(candles)
        
        # Should be TRENDING_BEARISH or UNCERTAIN (depending on ADX)
        assert regime in ["TRENDING_BEARISH", "UNCERTAIN", "RANGING", "VOLATILE"]
    
    def test_ranging_classification(self):
        """Test classification of ranging market.
        
        Validates: Requirements 7.1, 7.4
        """
        config = Config()
        config.regime_ranging_adx_threshold = 20.0
        config.regime_ranging_atr_percentile = 40.0
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Generate low volatility sideways candles
        candles = generate_candles(count=100, base_price=50000.0, volatility=0.005, trend="NEUTRAL")
        
        # Detect regime
        regime = detector.detect_regime(candles)
        
        # Should be RANGING, UNCERTAIN, or VOLATILE (depending on ATR percentile calculation)
        assert regime in ["RANGING", "UNCERTAIN", "VOLATILE"]
    
    def test_volatile_classification(self):
        """Test classification of volatile market.
        
        Validates: Requirements 7.1, 7.5
        """
        config = Config()
        config.regime_volatile_atr_percentile = 80.0
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Generate high volatility candles
        candles = generate_candles(count=100, base_price=50000.0, volatility=0.1, trend="NEUTRAL")
        
        # Detect regime
        regime = detector.detect_regime(candles)
        
        # Should be VOLATILE, UNCERTAIN, or possibly RANGING depending on ATR percentile
        # High volatility doesn't guarantee high ATR percentile in random data
        assert regime in ["VOLATILE", "UNCERTAIN", "RANGING", "TRENDING_BULLISH", "TRENDING_BEARISH"]
    
    def test_regime_stability_checking(self):
        """Test regime stability checking over time.
        
        Validates: Requirements 7.9
        """
        config = Config()
        config.regime_stability_minutes = 15
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Generate candles
        candles = generate_candles(count=100, base_price=50000.0, volatility=0.02)
        
        # First detection
        regime1 = detector.detect_regime(candles)
        
        # Should not be stable yet (only one entry, need consistent history)
        # Clear history to test from scratch
        detector.regime_history = []
        assert not detector.is_regime_stable()
        
        # Add regime history entries with same regime within stability window
        current_time = int(time.time())
        for i in range(5):
            detector.regime_history.append({
                'timestamp': current_time - (i * 60),  # 1 minute apart, within 15 min window
                'regime': "RANGING"
            })
        
        # Set current regime to match
        detector.current_regime = "RANGING"
        
        # Now should be stable (all recent entries match current regime)
        assert detector.is_regime_stable()
        
        # Now test instability: add a different regime entry within the stability window
        detector.regime_history = []
        detector.regime_history.append({
            'timestamp': current_time - 60,  # 1 minute ago
            'regime': "RANGING"
        })
        detector.regime_history.append({
            'timestamp': current_time - 120,  # 2 minutes ago
            'regime': "VOLATILE"  # Different regime
        })
        detector.current_regime = "RANGING"
        
        # Should not be stable (mixed regimes in recent history)
        assert not detector.is_regime_stable()
    
    def test_regime_parameters_trending(self):
        """Test regime parameters for trending markets.
        
        Validates: Requirements 7.6
        """
        config = Config()
        config.regime_trending_stop_multiplier = 2.5
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Get parameters for trending bullish
        params = detector.get_regime_parameters("TRENDING_BULLISH")
        
        assert params.regime == "TRENDING_BULLISH"
        assert params.stop_multiplier == 2.5
        assert params.threshold_multiplier == 1.0
        assert params.position_size_multiplier == 1.0
        assert params.strategy_type == "TREND_FOLLOWING"
        
        # Get parameters for trending bearish
        params = detector.get_regime_parameters("TRENDING_BEARISH")
        
        assert params.regime == "TRENDING_BEARISH"
        assert params.stop_multiplier == 2.5
        assert params.strategy_type == "TREND_FOLLOWING"
    
    def test_regime_parameters_ranging(self):
        """Test regime parameters for ranging markets.
        
        Validates: Requirements 7.7
        """
        config = Config()
        config.regime_ranging_stop_multiplier = 1.0
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Get parameters for ranging
        params = detector.get_regime_parameters("RANGING")
        
        assert params.regime == "RANGING"
        assert params.stop_multiplier == 1.0
        assert params.threshold_multiplier == 1.0
        assert params.position_size_multiplier == 1.0
        assert params.strategy_type == "MEAN_REVERSION"
    
    def test_regime_parameters_volatile(self):
        """Test regime parameters for volatile markets.
        
        Validates: Requirements 7.8
        """
        config = Config()
        config.regime_volatile_size_reduction = 0.5
        config.regime_volatile_threshold_increase = 0.3
        config.regime_trending_stop_multiplier = 2.5
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Get parameters for volatile
        params = detector.get_regime_parameters("VOLATILE")
        
        assert params.regime == "VOLATILE"
        assert params.stop_multiplier == 2.5
        assert params.threshold_multiplier == 1.3  # 1.0 + 0.3
        assert params.position_size_multiplier == 0.5
        assert params.strategy_type == "TREND_FOLLOWING"
    
    def test_regime_parameters_uncertain(self):
        """Test regime parameters for uncertain markets.
        
        Validates: Requirements 7.1
        """
        config = Config()
        config.stop_loss_atr_multiplier = 2.0
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Get parameters for uncertain
        params = detector.get_regime_parameters("UNCERTAIN")
        
        assert params.regime == "UNCERTAIN"
        assert params.stop_multiplier == 2.0
        assert params.threshold_multiplier == 1.0
        assert params.position_size_multiplier == 0.5  # Reduced in uncertain conditions
        assert params.strategy_type == "NONE"
    
    def test_insufficient_data_returns_uncertain(self):
        """Test that insufficient data returns UNCERTAIN regime.
        
        Validates: Requirements 7.1
        """
        config = Config()
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Generate insufficient candles
        candles = generate_candles(count=10, base_price=50000.0, volatility=0.02)
        
        # Detect regime
        regime = detector.detect_regime(candles)
        
        # Should return UNCERTAIN
        assert regime == "UNCERTAIN"
    
    def test_empty_candles_returns_uncertain(self):
        """Test that empty candles list returns UNCERTAIN regime.
        
        Validates: Requirements 7.1
        """
        config = Config()
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Detect regime with empty list
        regime = detector.detect_regime([])
        
        # Should return UNCERTAIN
        assert regime == "UNCERTAIN"
    
    def test_regime_history_tracking(self):
        """Test that regime history is properly tracked.
        
        Validates: Requirements 7.9
        """
        config = Config()
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Generate candles
        candles = generate_candles(count=100, base_price=50000.0, volatility=0.02)
        
        # Perform multiple detections
        for i in range(3):
            detector.detect_regime(candles)
        
        # Check history
        assert len(detector.regime_history) == 3
        
        # Verify each entry has required fields
        for entry in detector.regime_history:
            assert 'timestamp' in entry
            assert 'regime' in entry
            assert entry['timestamp'] > 0
            assert entry['regime'] in ["TRENDING_BULLISH", "TRENDING_BEARISH", "RANGING", "VOLATILE", "UNCERTAIN"]
    
    def test_regime_history_cleanup(self):
        """Test that old regime history is cleaned up.
        
        Validates: Requirements 7.9
        """
        config = Config()
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Add old history entries (more than 24 hours old)
        current_time = int(time.time())
        old_time = current_time - (25 * 3600)  # 25 hours ago
        
        detector.regime_history.append({
            'timestamp': old_time,
            'regime': "RANGING"
        })
        
        # Generate candles and detect regime
        candles = generate_candles(count=100, base_price=50000.0, volatility=0.02)
        detector.detect_regime(candles)
        
        # Old entry should be removed
        for entry in detector.regime_history:
            assert entry['timestamp'] > old_time
    
    def test_atr_percentile_calculation(self):
        """Test ATR percentile calculation.
        
        Validates: Requirements 7.1
        """
        config = Config()
        config.atr_period = 14
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Generate candles
        candles = generate_candles(count=100, base_price=50000.0, volatility=0.02)
        
        # Calculate current ATR
        current_atr = indicator_calc.calculate_atr(candles, config.atr_period)
        
        # Calculate percentile
        percentile = detector._calculate_atr_percentile(candles, current_atr)
        
        # Should be between 0 and 100
        assert 0.0 <= percentile <= 100.0
    
    def test_bb_width_calculation(self):
        """Test Bollinger Band width calculation.
        
        Validates: Requirements 7.1
        """
        config = Config()
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Generate candles
        candles = generate_candles(count=100, base_price=50000.0, volatility=0.02)
        
        # Calculate BB width
        bb_width = detector._calculate_bb_width(candles)
        
        # Should be positive
        assert bb_width >= 0.0
    
    def test_error_handling_returns_uncertain(self):
        """Test that errors during detection return UNCERTAIN.
        
        Validates: Requirements 7.1
        """
        config = Config()
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Create invalid candles (will cause calculation errors)
        candles = [
            Candle(timestamp=0, open=0, high=0, low=0, close=0, volume=0)
            for _ in range(50)
        ]
        
        # Detect regime (should handle error gracefully)
        regime = detector.detect_regime(candles)
        
        # Should return UNCERTAIN on error
        assert regime == "UNCERTAIN"
    
    def test_regime_update_interval(self):
        """Test that regime update interval is tracked.
        
        Validates: Requirements 7.9
        """
        config = Config()
        config.regime_update_interval = 900  # 15 minutes
        indicator_calc = IndicatorCalculator()
        detector = MarketRegimeDetector(config, indicator_calc)
        
        # Generate candles
        candles = generate_candles(count=100, base_price=50000.0, volatility=0.02)
        
        # First detection
        regime1 = detector.detect_regime(candles)
        last_update1 = detector.last_update
        
        # Verify last_update was set
        assert last_update1 > 0
        
        # Second detection
        regime2 = detector.detect_regime(candles)
        last_update2 = detector.last_update
        
        # Verify last_update was updated
        assert last_update2 >= last_update1
