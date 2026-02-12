"""Property-based and unit tests for Adaptive Threshold Manager."""

import time
import pytest
from hypothesis import given, strategies as st, settings
from src.config import Config
from src.models import Candle
from src.adaptive_threshold_manager import AdaptiveThresholdManager


# Helper function to generate candles
def generate_candles(count: int, base_price: float = 50000.0, volatility: float = 0.01) -> list:
    """Generate synthetic candle data for testing.
    
    Args:
        count: Number of candles to generate
        base_price: Base price for candles
        volatility: Price volatility factor
        
    Returns:
        List of Candle objects
    """
    import random
    candles = []
    current_price = base_price
    timestamp = int(time.time() * 1000) - (count * 3600000)  # Start count hours ago
    
    for i in range(count):
        # Add some random price movement
        price_change = current_price * volatility * (random.random() - 0.5) * 2
        current_price += price_change
        
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


# Feature: advanced-trading-enhancements, Property 2: Threshold bounds invariant
@given(
    base_adx=st.floats(min_value=15.0, max_value=35.0),
    base_rvol=st.floats(min_value=0.8, max_value=2.0),
    min_adx=st.floats(min_value=10.0, max_value=20.0),
    max_adx=st.floats(min_value=30.0, max_value=50.0),
    min_rvol=st.floats(min_value=0.5, max_value=1.0),
    max_rvol=st.floats(min_value=1.5, max_value=3.0),
    volatility=st.floats(min_value=0.001, max_value=0.05)
)
@settings(max_examples=100)
def test_threshold_bounds_invariant(
    base_adx, base_rvol, min_adx, max_adx, min_rvol, max_rvol, volatility
):
    """For any volatility level, the adjusted thresholds must remain within 
    configured minimum and maximum bounds.
    
    Property 2: Threshold bounds invariant
    Validates: Requirements 1.4
    """
    # Create config with specified bounds
    config = Config()
    config.adx_threshold = base_adx
    config.rvol_threshold = base_rvol
    config.adaptive_threshold_min_adx = min_adx
    config.adaptive_threshold_max_adx = max_adx
    config.adaptive_threshold_min_rvol = min_rvol
    config.adaptive_threshold_max_rvol = max_rvol
    config.adaptive_threshold_lookback_days = 30
    
    # Create manager
    manager = AdaptiveThresholdManager(config)
    
    # Generate candles with varying volatility
    candles = generate_candles(count=30 * 24, base_price=50000.0, volatility=volatility)
    
    # Update thresholds
    thresholds = manager.update_thresholds(candles)
    
    # Verify bounds are respected
    assert min_adx <= thresholds['adx'] <= max_adx, (
        f"ADX threshold {thresholds['adx']} outside bounds [{min_adx}, {max_adx}]"
    )
    assert min_rvol <= thresholds['rvol'] <= max_rvol, (
        f"RVOL threshold {thresholds['rvol']} outside bounds [{min_rvol}, {max_rvol}]"
    )


# Feature: advanced-trading-enhancements, Property 1: Threshold volatility correlation
@given(
    percentile_sequence=st.lists(
        st.floats(min_value=0.0, max_value=100.0),
        min_size=3,
        max_size=5
    )
)
@settings(max_examples=100)
def test_threshold_volatility_correlation(percentile_sequence):
    """For any sequence of increasing volatility percentiles, 
    the threshold multipliers should increase monotonically.
    
    Property 1: Threshold volatility correlation
    Validates: Requirements 1.1, 1.2
    """
    # Sort percentile sequence to ensure it's increasing
    percentile_sequence = sorted(percentile_sequence)
    
    # Create config
    config = Config()
    config.adx_threshold = 20.0
    config.rvol_threshold = 1.2
    
    # Create manager
    manager = AdaptiveThresholdManager(config)
    
    # Track multipliers and resulting thresholds
    multipliers = []
    adx_thresholds = []
    rvol_thresholds = []
    
    for percentile in percentile_sequence:
        # Calculate multiplier for this percentile
        multiplier = manager._calculate_threshold_multiplier(percentile)
        multipliers.append(multiplier)
        
        # Calculate what the thresholds would be
        adx = config.adx_threshold * multiplier
        rvol = config.rvol_threshold * multiplier
        
        # Apply bounds
        adx = max(config.adaptive_threshold_min_adx, 
                 min(adx, config.adaptive_threshold_max_adx))
        rvol = max(config.adaptive_threshold_min_rvol,
                  min(rvol, config.adaptive_threshold_max_rvol))
        
        adx_thresholds.append(adx)
        rvol_thresholds.append(rvol)
    
    # Verify that multipliers increase with percentiles
    # (or stay the same if we're in the same percentile range)
    for i in range(1, len(multipliers)):
        assert multipliers[i] >= multipliers[i-1], (
            f"Multiplier decreased: percentiles={percentile_sequence}, "
            f"multipliers={multipliers}"
        )
    
    # Verify that thresholds generally increase (allowing for bounds constraints)
    # The last threshold should be >= first threshold
    assert adx_thresholds[-1] >= adx_thresholds[0], (
        f"ADX thresholds did not increase: {adx_thresholds}"
    )
    assert rvol_thresholds[-1] >= rvol_thresholds[0], (
        f"RVOL thresholds did not increase: {rvol_thresholds}"
    )


# Feature: advanced-trading-enhancements, Property 3: Volatility percentile range
@given(
    candle_count=st.integers(min_value=30 * 24, max_value=60 * 24),
    volatility=st.floats(min_value=0.001, max_value=0.1)
)
@settings(max_examples=100)
def test_volatility_percentile_range(candle_count, volatility):
    """For any set of candles, the calculated volatility percentile must be 
    between 0 and 100 inclusive.
    
    Property 3: Volatility percentile range
    Validates: Requirements 1.3
    """
    # Create config
    config = Config()
    config.adaptive_threshold_lookback_days = 30
    
    # Create manager
    manager = AdaptiveThresholdManager(config)
    
    # Generate candles
    candles = generate_candles(count=candle_count, base_price=50000.0, volatility=volatility)
    
    # Calculate volatility percentile
    percentile = manager.calculate_volatility_percentile(candles)
    
    # Verify range
    assert 0.0 <= percentile <= 100.0, (
        f"Volatility percentile {percentile} outside valid range [0, 100]"
    )


class TestAdaptiveThresholdManagerUnit:
    """Unit tests for Adaptive Threshold Manager edge cases."""
    
    def test_insufficient_data_uses_default_percentile(self):
        """Test with insufficient data returns default percentile.
        
        Validates: Requirements 1.3
        """
        config = Config()
        config.adaptive_threshold_lookback_days = 30
        manager = AdaptiveThresholdManager(config)
        
        # Generate only 100 candles (insufficient for 30 days)
        candles = generate_candles(count=100, base_price=50000.0, volatility=0.01)
        
        # Calculate percentile
        percentile = manager.calculate_volatility_percentile(candles)
        
        # Should return default of 50.0
        assert percentile == 50.0
    
    def test_extreme_low_volatility(self):
        """Test with extremely low volatility values.
        
        Validates: Requirements 1.3
        """
        config = Config()
        config.adaptive_threshold_lookback_days = 30
        manager = AdaptiveThresholdManager(config)
        
        # Generate candles with very low volatility
        candles = generate_candles(count=30 * 24, base_price=50000.0, volatility=0.0001)
        
        # Update thresholds
        thresholds = manager.update_thresholds(candles)
        
        # Should still produce valid thresholds within bounds
        assert config.adaptive_threshold_min_adx <= thresholds['adx'] <= config.adaptive_threshold_max_adx
        assert config.adaptive_threshold_min_rvol <= thresholds['rvol'] <= config.adaptive_threshold_max_rvol
    
    def test_extreme_high_volatility(self):
        """Test with extremely high volatility values.
        
        Validates: Requirements 1.3
        """
        config = Config()
        config.adaptive_threshold_lookback_days = 30
        manager = AdaptiveThresholdManager(config)
        
        # Generate candles with very high volatility
        candles = generate_candles(count=30 * 24, base_price=50000.0, volatility=0.1)
        
        # Update thresholds
        thresholds = manager.update_thresholds(candles)
        
        # Should still produce valid thresholds within bounds
        assert config.adaptive_threshold_min_adx <= thresholds['adx'] <= config.adaptive_threshold_max_adx
        assert config.adaptive_threshold_min_rvol <= thresholds['rvol'] <= config.adaptive_threshold_max_rvol
    
    def test_threshold_adjustment_logging(self):
        """Test that threshold adjustments are logged with reasoning.
        
        Validates: Requirements 1.5
        """
        config = Config()
        config.adaptive_threshold_lookback_days = 30
        manager = AdaptiveThresholdManager(config)
        
        # Generate candles
        candles = generate_candles(count=30 * 24, base_price=50000.0, volatility=0.02)
        
        # Update thresholds
        manager.update_thresholds(candles)
        
        # Check that history was recorded
        history = manager.get_threshold_history()
        assert len(history) > 0
        
        # Check that history entry has all required fields
        entry = history[-1]
        assert entry.timestamp > 0
        assert 0.0 <= entry.volatility_percentile <= 100.0
        assert entry.adx_threshold > 0
        assert entry.rvol_threshold > 0
        assert len(entry.reason) > 0
        
        # Verify reason contains key information
        assert "Volatility percentile" in entry.reason
        assert "Multiplier" in entry.reason
        assert "ADX" in entry.reason
        assert "RVOL" in entry.reason
    
    def test_get_current_thresholds(self):
        """Test getting current threshold values.
        
        Validates: Requirements 1.1, 1.2
        """
        config = Config()
        config.adx_threshold = 25.0
        config.rvol_threshold = 1.5
        manager = AdaptiveThresholdManager(config)
        
        # Get initial thresholds
        thresholds = manager.get_current_thresholds()
        
        # Should match config values initially
        assert thresholds['adx'] == 25.0
        assert thresholds['rvol'] == 1.5
        
        # Verify it returns a copy (not reference)
        thresholds['adx'] = 999.0
        assert manager.get_current_thresholds()['adx'] == 25.0
    
    def test_update_interval_respected(self):
        """Test that update interval is respected.
        
        Validates: Requirements 1.6
        """
        config = Config()
        config.adaptive_threshold_update_interval = 3600  # 1 hour
        config.adaptive_threshold_lookback_days = 30
        manager = AdaptiveThresholdManager(config)
        
        # Generate candles
        candles = generate_candles(count=30 * 24, base_price=50000.0, volatility=0.02)
        
        # First update should work
        thresholds1 = manager.update_thresholds(candles)
        history_count1 = len(manager.get_threshold_history())
        
        # Immediate second update should not change anything
        thresholds2 = manager.update_thresholds(candles)
        history_count2 = len(manager.get_threshold_history())
        
        # Thresholds should be the same
        assert thresholds1 == thresholds2
        # History should not have grown
        assert history_count1 == history_count2
    
    def test_threshold_history_tracking(self):
        """Test that threshold history is properly tracked.
        
        Validates: Requirements 1.5
        """
        config = Config()
        config.adaptive_threshold_update_interval = 0  # Allow immediate updates
        config.adaptive_threshold_lookback_days = 30
        manager = AdaptiveThresholdManager(config)
        
        # Generate candles
        candles = generate_candles(count=30 * 24, base_price=50000.0, volatility=0.02)
        
        # Perform multiple updates
        for i in range(3):
            manager.last_update_time = 0  # Force update
            manager.update_thresholds(candles)
        
        # Check history
        history = manager.get_threshold_history()
        assert len(history) == 3
        
        # Check limited history
        limited_history = manager.get_threshold_history(limit=2)
        assert len(limited_history) == 2
        assert limited_history[-1] == history[-1]  # Most recent should match
    
    def test_zero_atr_handled_gracefully(self):
        """Test that zero ATR values are handled gracefully.
        
        Validates: Requirements 1.3
        """
        config = Config()
        config.adaptive_threshold_lookback_days = 30
        manager = AdaptiveThresholdManager(config)
        
        # Create candles with no price movement (zero ATR)
        candles = []
        timestamp = int(time.time() * 1000)
        for i in range(30 * 24):
            candle = Candle(
                timestamp=timestamp,
                open=50000.0,
                high=50000.0,
                low=50000.0,
                close=50000.0,
                volume=100.0
            )
            candles.append(candle)
            timestamp += 3600000
        
        # Calculate percentile
        percentile = manager.calculate_volatility_percentile(candles)
        
        # Should return default percentile
        assert percentile == 50.0
    
    def test_multiplier_calculation(self):
        """Test threshold multiplier calculation for different volatility levels.
        
        Validates: Requirements 1.1, 1.2
        """
        config = Config()
        manager = AdaptiveThresholdManager(config)
        
        # Test different volatility percentile ranges
        assert manager._calculate_threshold_multiplier(10.0) == 0.7   # 0-20 range
        assert manager._calculate_threshold_multiplier(30.0) == 0.85  # 20-40 range
        assert manager._calculate_threshold_multiplier(50.0) == 1.0   # 40-60 range
        assert manager._calculate_threshold_multiplier(70.0) == 1.15  # 60-80 range
        assert manager._calculate_threshold_multiplier(90.0) == 1.3   # 80-100 range
    
    def test_initialization_logging(self):
        """Test that initialization is logged.
        
        Validates: Requirements 1.5
        """
        config = Config()
        config.adx_threshold = 22.0
        config.rvol_threshold = 1.3
        
        # Create manager (should log initialization)
        manager = AdaptiveThresholdManager(config)
        
        # Verify initial state
        assert manager.volatility_percentile == 50.0
        assert manager.last_update_time == 0
        assert len(manager.threshold_history) == 0
        assert manager.current_thresholds['adx'] == 22.0
        assert manager.current_thresholds['rvol'] == 1.3
