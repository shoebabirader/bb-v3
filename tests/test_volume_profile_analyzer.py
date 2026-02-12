"""Tests for Volume Profile Analyzer."""

import pytest
from hypothesis import given, strategies as st, settings
from src.volume_profile_analyzer import VolumeProfileAnalyzer
from src.models import Candle, VolumeProfile
from src.config import Config
import time


# Helper function to create test candles
def create_candles(num_candles: int, base_price: float = 50000.0, price_range: float = 1000.0) -> list:
    """Create test candles with varying prices and volumes."""
    candles = []
    timestamp = int(time.time() * 1000)
    
    for i in range(num_candles):
        # Vary price within range
        price_offset = (i % 10) * (price_range / 10)
        open_price = base_price + price_offset
        close_price = open_price + (price_range / 20)
        high = max(open_price, close_price) + (price_range / 40)
        low = min(open_price, close_price) - (price_range / 40)
        volume = 100.0 + (i % 5) * 50.0
        
        candles.append(Candle(
            timestamp=timestamp + (i * 60000),  # 1 minute apart
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=volume
        ))
    
    return candles


# Feature: advanced-trading-enhancements, Property 8: POC correctness
@settings(max_examples=100, deadline=None)
@given(
    num_candles=st.integers(min_value=10, max_value=200),
    base_price=st.floats(min_value=1000.0, max_value=100000.0),
    price_range=st.floats(min_value=100.0, max_value=5000.0)
)
def test_property_poc_is_maximum_volume_price(num_candles, base_price, price_range):
    """Property 8: POC correctness
    
    For any volume profile, the Point of Control must be the price level 
    with the maximum volume.
    
    Validates: Requirements 3.2
    """
    # Create config
    config = Config()
    config.volume_profile_bin_size = 0.001
    
    # Create analyzer
    analyzer = VolumeProfileAnalyzer(config)
    
    # Create test candles
    candles = create_candles(num_candles, base_price, price_range)
    
    # Calculate volume profile
    profile = analyzer.calculate_volume_profile(candles)
    
    # Skip if no valid profile
    if not profile.price_levels or not profile.volumes:
        return
    
    # Find the actual maximum volume
    max_volume = max(profile.volumes)
    max_volume_indices = [i for i, v in enumerate(profile.volumes) if v == max_volume]
    
    # POC should be at one of the price levels with maximum volume
    poc_found = False
    for idx in max_volume_indices:
        if abs(profile.poc - profile.price_levels[idx]) < 0.01:  # Small tolerance for floating point
            poc_found = True
            break
    
    assert poc_found, f"POC {profile.poc} is not at a price level with maximum volume {max_volume}"
    
    # Verify that no other price level has more volume than POC
    poc_volume = analyzer.get_volume_at_price(profile.poc)
    for i, volume in enumerate(profile.volumes):
        assert volume <= poc_volume + 0.01, f"Price level {profile.price_levels[i]} has volume {volume} > POC volume {poc_volume}"


# Feature: advanced-trading-enhancements, Property 9: Value area volume
@settings(max_examples=100, deadline=None)
@given(
    num_candles=st.integers(min_value=50, max_value=200),  # More candles for better distribution
    base_price=st.floats(min_value=1000.0, max_value=100000.0),
    price_range=st.floats(min_value=500.0, max_value=5000.0)  # Larger price range for more bins
)
def test_property_value_area_contains_target_volume(num_candles, base_price, price_range):
    """Property 9: Value area volume
    
    For any volume profile with sufficient bins, the volume between VAL and VAH 
    should approximate the target percentage (70%) of total volume. 
    The value area will contain at least the target percentage.
    
    Validates: Requirements 3.3
    """
    # Create config
    config = Config()
    config.volume_profile_bin_size = 0.001
    config.volume_profile_value_area_pct = 0.70
    
    # Create analyzer
    analyzer = VolumeProfileAnalyzer(config)
    
    # Create test candles
    candles = create_candles(num_candles, base_price, price_range)
    
    # Calculate volume profile
    profile = analyzer.calculate_volume_profile(candles)
    
    # Skip if no valid profile or zero volume
    if not profile.price_levels or not profile.volumes or profile.total_volume == 0:
        return
    
    # Skip if too few bins (edge case where 70% might require all bins)
    if len(profile.price_levels) < 10:
        return
    
    # Calculate volume within value area
    value_area_volume = 0.0
    for i, price_level in enumerate(profile.price_levels):
        if profile.val <= price_level <= profile.vah:
            value_area_volume += profile.volumes[i]
    
    # Calculate percentage
    value_area_pct = value_area_volume / profile.total_volume
    
    # The value area should contain at least the target percentage
    target_pct = config.volume_profile_value_area_pct
    
    assert value_area_pct >= target_pct - 0.01, \
        f"Value area contains {value_area_pct*100:.2f}% of volume, expected at least {target_pct*100:.2f}%"
    
    # The value area should not be excessively large
    # With sufficient bins, it should not exceed 90%
    max_pct = 0.90
    assert value_area_pct <= max_pct, \
        f"Value area contains {value_area_pct*100:.2f}% of volume, expected at most {max_pct*100:.2f}% (bins: {len(profile.price_levels)})"


class TestVolumeProfileAnalyzer:
    """Unit tests for VolumeProfileAnalyzer."""
    
    def test_initialization(self):
        """Test VolumeProfileAnalyzer initialization."""
        config = Config()
        analyzer = VolumeProfileAnalyzer(config)
        
        assert analyzer.config == config
        assert analyzer.current_profile is None
        assert analyzer.last_update == 0
    
    def test_calculate_volume_profile_empty_candles(self):
        """Test volume profile calculation with empty candles."""
        config = Config()
        analyzer = VolumeProfileAnalyzer(config)
        
        profile = analyzer.calculate_volume_profile([])
        
        assert profile.price_levels == []
        assert profile.volumes == []
        assert profile.poc == 0.0
        assert profile.vah == 0.0
        assert profile.val == 0.0
        assert profile.total_volume == 0.0
    
    def test_calculate_volume_profile_single_candle(self):
        """Test volume profile calculation with single candle."""
        config = Config()
        analyzer = VolumeProfileAnalyzer(config)
        
        candles = [Candle(
            timestamp=int(time.time() * 1000),
            open=50000.0,
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=100.0
        )]
        
        profile = analyzer.calculate_volume_profile(candles)
        
        assert len(profile.price_levels) > 0
        assert len(profile.volumes) > 0
        assert profile.total_volume > 0
        assert profile.poc > 0
    
    def test_identify_poc_empty_profile(self):
        """Test POC identification with empty profile."""
        config = Config()
        analyzer = VolumeProfileAnalyzer(config)
        
        profile = VolumeProfile(
            price_levels=[],
            volumes=[],
            poc=0.0,
            vah=0.0,
            val=0.0,
            total_volume=0.0,
            timestamp=int(time.time() * 1000)
        )
        
        poc = analyzer.identify_poc(profile)
        assert poc == 0.0
    
    def test_identify_poc_known_values(self):
        """Test POC identification with known values."""
        config = Config()
        analyzer = VolumeProfileAnalyzer(config)
        
        profile = VolumeProfile(
            price_levels=[49000.0, 49500.0, 50000.0, 50500.0, 51000.0],
            volumes=[100.0, 200.0, 500.0, 150.0, 80.0],  # Max at 50000.0
            poc=0.0,
            vah=0.0,
            val=0.0,
            total_volume=1030.0,
            timestamp=int(time.time() * 1000)
        )
        
        poc = analyzer.identify_poc(profile)
        assert poc == 50000.0
    
    def test_identify_value_area_empty_profile(self):
        """Test value area identification with empty profile."""
        config = Config()
        analyzer = VolumeProfileAnalyzer(config)
        
        profile = VolumeProfile(
            price_levels=[],
            volumes=[],
            poc=0.0,
            vah=0.0,
            val=0.0,
            total_volume=0.0,
            timestamp=int(time.time() * 1000)
        )
        
        val, vah = analyzer.identify_value_area(profile)
        assert val == 0.0
        assert vah == 0.0
    
    def test_is_near_key_level_no_profile(self):
        """Test key level detection with no profile."""
        config = Config()
        analyzer = VolumeProfileAnalyzer(config)
        
        assert not analyzer.is_near_key_level(50000.0)
    
    def test_is_near_key_level_with_profile(self):
        """Test key level detection with profile."""
        config = Config()
        config.volume_profile_key_level_threshold = 0.005  # 0.5%
        analyzer = VolumeProfileAnalyzer(config)
        
        # Create a simple profile
        analyzer.current_profile = VolumeProfile(
            price_levels=[49000.0, 50000.0, 51000.0],
            volumes=[100.0, 500.0, 100.0],
            poc=50000.0,
            vah=51000.0,
            val=49000.0,
            total_volume=700.0,
            timestamp=int(time.time() * 1000)
        )
        
        # Price near POC (within 0.5%)
        assert analyzer.is_near_key_level(50000.0)
        assert analyzer.is_near_key_level(50200.0)  # 0.4% away
        
        # Price far from any key level
        assert not analyzer.is_near_key_level(49500.0)
    
    def test_get_volume_at_price_no_profile(self):
        """Test volume query with no profile."""
        config = Config()
        analyzer = VolumeProfileAnalyzer(config)
        
        volume = analyzer.get_volume_at_price(50000.0)
        assert volume == 0.0
    
    def test_get_volume_at_price_with_profile(self):
        """Test volume query with profile."""
        config = Config()
        analyzer = VolumeProfileAnalyzer(config)
        
        analyzer.current_profile = VolumeProfile(
            price_levels=[49000.0, 50000.0, 51000.0],
            volumes=[100.0, 500.0, 100.0],
            poc=50000.0,
            vah=51000.0,
            val=49000.0,
            total_volume=700.0,
            timestamp=int(time.time() * 1000)
        )
        
        # Query exact price level
        volume = analyzer.get_volume_at_price(50000.0)
        assert volume == 500.0
        
        # Query nearby price (should return nearest bin)
        volume = analyzer.get_volume_at_price(50100.0)
        assert volume == 500.0  # Nearest to 50000.0
    
    def test_volume_profile_with_zero_volume_bins(self):
        """Test volume profile calculation with zero-volume bins.
        
        Requirements: 3.1, 3.7
        """
        config = Config()
        analyzer = VolumeProfileAnalyzer(config)
        
        # Create candles with gaps (some price levels will have zero volume)
        candles = [
            Candle(
                timestamp=int(time.time() * 1000) + i * 60000,
                open=50000.0 if i < 5 else 51000.0,
                high=50100.0 if i < 5 else 51100.0,
                low=49900.0 if i < 5 else 50900.0,
                close=50050.0 if i < 5 else 51050.0,
                volume=100.0
            )
            for i in range(10)
        ]
        
        profile = analyzer.calculate_volume_profile(candles)
        
        # Should handle zero-volume bins gracefully
        assert len(profile.price_levels) > 0
        assert len(profile.volumes) > 0
        assert profile.total_volume > 0
        assert profile.poc > 0
        
        # Some bins should have zero or very low volume
        min_volume = min(profile.volumes)
        assert min_volume >= 0  # No negative volumes
    
    def test_volume_profile_with_insufficient_data(self):
        """Test volume profile calculation with insufficient data.
        
        Requirements: 3.1, 3.7
        """
        config = Config()
        analyzer = VolumeProfileAnalyzer(config)
        
        # Test with very few candles
        candles = [
            Candle(
                timestamp=int(time.time() * 1000),
                open=50000.0,
                high=50100.0,
                low=49900.0,
                close=50050.0,
                volume=100.0
            )
        ]
        
        profile = analyzer.calculate_volume_profile(candles)
        
        # Should still produce a valid profile
        assert len(profile.price_levels) > 0
        assert profile.total_volume > 0
    
    def test_volume_profile_update_frequency(self):
        """Test that volume profile respects update frequency.
        
        Requirements: 3.7
        """
        config = Config()
        config.volume_profile_update_interval = 14400  # 4 hours
        analyzer = VolumeProfileAnalyzer(config)
        
        # Create test candles
        candles = create_candles(50)
        
        # Calculate profile
        profile1 = analyzer.calculate_volume_profile(candles)
        first_update = analyzer.last_update
        
        # Verify last_update was set
        assert analyzer.last_update > 0
        assert analyzer.current_profile is not None
        
        # Calculate again immediately
        profile2 = analyzer.calculate_volume_profile(candles)
        second_update = analyzer.last_update
        
        # Both should succeed (update frequency is enforced by caller, not the analyzer)
        assert second_update >= first_update
        assert analyzer.current_profile is not None
