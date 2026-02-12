"""Tests for TimeframeCoordinator."""

import pytest
from hypothesis import given, strategies as st, settings
from src.timeframe_coordinator import TimeframeCoordinator, TimeframeData, TimeframeAnalysis
from src.indicators import IndicatorCalculator
from src.config import Config
from src.models import Candle


# Helper strategies for generating test data
@st.composite
def timeframe_data_strategy(draw):
    """Generate random TimeframeData."""
    trend = draw(st.sampled_from(["BULLISH", "BEARISH", "NEUTRAL"]))
    momentum = draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    volatility = draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    volume_trend = draw(st.sampled_from(["INCREASING", "DECREASING", "STABLE"]))
    
    return TimeframeData(
        trend=trend,
        momentum=momentum,
        volatility=volatility,
        volume_trend=volume_trend
    )


@st.composite
def timeframe_analysis_strategy(draw):
    """Generate random TimeframeAnalysis."""
    # Randomly include or exclude each timeframe
    tf_5m = draw(st.one_of(st.none(), timeframe_data_strategy()))
    tf_15m = draw(st.one_of(st.none(), timeframe_data_strategy()))
    tf_1h = draw(st.one_of(st.none(), timeframe_data_strategy()))
    tf_4h = draw(st.one_of(st.none(), timeframe_data_strategy()))
    
    return TimeframeAnalysis(
        timeframe_5m=tf_5m,
        timeframe_15m=tf_15m,
        timeframe_1h=tf_1h,
        timeframe_4h=tf_4h,
        alignment_score=0,  # Will be calculated
        confidence=0.0,  # Will be calculated
        overall_direction="NEUTRAL"  # Will be calculated
    )


@st.composite
def candle_strategy(draw, min_price=1000.0, max_price=100000.0):
    """Generate a random Candle."""
    timestamp = draw(st.integers(min_value=1000000000000, max_value=2000000000000))
    open_price = draw(st.floats(min_value=min_price, max_value=max_price, allow_nan=False, allow_infinity=False))
    close_price = draw(st.floats(min_value=min_price, max_value=max_price, allow_nan=False, allow_infinity=False))
    
    # Ensure high >= max(open, close) and low <= min(open, close)
    high = draw(st.floats(min_value=max(open_price, close_price), max_value=max_price, allow_nan=False, allow_infinity=False))
    low = draw(st.floats(min_value=min_price, max_value=min(open_price, close_price), allow_nan=False, allow_infinity=False))
    
    volume = draw(st.floats(min_value=0.1, max_value=1000000.0, allow_nan=False, allow_infinity=False))
    
    return Candle(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close_price,
        volume=volume
    )


class TestTimeframeCoordinator:
    """Unit tests for TimeframeCoordinator."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = Config()
        config.enable_multi_timeframe = True
        return config
    
    @pytest.fixture
    def coordinator(self, config):
        """Create a TimeframeCoordinator instance."""
        indicator_calc = IndicatorCalculator()
        return TimeframeCoordinator(config, indicator_calc)
    
    def test_initialization(self, coordinator, config):
        """Test TimeframeCoordinator initialization."""
        assert coordinator.config == config
        assert coordinator.timeframes == ['5m', '15m', '1h', '4h']
        assert coordinator.weights == config.timeframe_weights
    
    def test_analyze_all_timeframes_with_no_data(self, coordinator):
        """Test analysis with no candle data."""
        analysis = coordinator.analyze_all_timeframes([], [], [], [])
        
        assert analysis.timeframe_5m is None
        assert analysis.timeframe_15m is None
        assert analysis.timeframe_1h is None
        assert analysis.timeframe_4h is None
        assert analysis.alignment_score == 0
        assert analysis.confidence == 0.0
        assert analysis.overall_direction == "NEUTRAL"
    
    def test_analyze_all_timeframes_with_insufficient_data(self, coordinator):
        """Test analysis with insufficient candle data."""
        # Create minimal candles (less than 20)
        candles = [
            Candle(timestamp=i * 60000, open=50000.0, high=50100.0, low=49900.0, close=50000.0, volume=100.0)
            for i in range(10)
        ]
        
        analysis = coordinator.analyze_all_timeframes(candles, candles, candles, candles)
        
        # Should return neutral data for all timeframes
        assert analysis.timeframe_5m.trend == "NEUTRAL"
        assert analysis.timeframe_15m.trend == "NEUTRAL"
        assert analysis.timeframe_1h.trend == "NEUTRAL"
        assert analysis.timeframe_4h.trend == "NEUTRAL"
    
    def test_check_timeframe_alignment_all_bullish(self, coordinator):
        """Test alignment when all timeframes are bullish."""
        analysis = TimeframeAnalysis(
            timeframe_5m=TimeframeData("BULLISH", 0.01, 100.0, "INCREASING"),
            timeframe_15m=TimeframeData("BULLISH", 0.02, 150.0, "INCREASING"),
            timeframe_1h=TimeframeData("BULLISH", 0.03, 200.0, "STABLE"),
            timeframe_4h=TimeframeData("BULLISH", 0.04, 250.0, "STABLE"),
            alignment_score=0,
            confidence=0.0,
            overall_direction="NEUTRAL"
        )
        
        alignment = coordinator.check_timeframe_alignment(analysis)
        assert alignment == 4
    
    def test_check_timeframe_alignment_mixed(self, coordinator):
        """Test alignment with mixed trends."""
        analysis = TimeframeAnalysis(
            timeframe_5m=TimeframeData("BULLISH", 0.01, 100.0, "INCREASING"),
            timeframe_15m=TimeframeData("BULLISH", 0.02, 150.0, "INCREASING"),
            timeframe_1h=TimeframeData("BULLISH", 0.03, 200.0, "STABLE"),
            timeframe_4h=TimeframeData("BEARISH", -0.04, 250.0, "STABLE"),
            alignment_score=0,
            confidence=0.0,
            overall_direction="NEUTRAL"
        )
        
        alignment = coordinator.check_timeframe_alignment(analysis)
        assert alignment == 3  # 3 bullish, 1 bearish
    
    def test_check_timeframe_alignment_with_missing_data(self, coordinator):
        """Test alignment with missing timeframe data."""
        analysis = TimeframeAnalysis(
            timeframe_5m=TimeframeData("BULLISH", 0.01, 100.0, "INCREASING"),
            timeframe_15m=None,
            timeframe_1h=TimeframeData("BULLISH", 0.03, 200.0, "STABLE"),
            timeframe_4h=None,
            alignment_score=0,
            confidence=0.0,
            overall_direction="NEUTRAL"
        )
        
        alignment = coordinator.check_timeframe_alignment(analysis)
        assert alignment == 2  # Only 2 valid timeframes, both bullish
    
    def test_calculate_signal_confidence_high(self, coordinator):
        """Test confidence calculation with 4 aligned timeframes."""
        analysis = TimeframeAnalysis(
            timeframe_5m=TimeframeData("BULLISH", 0.01, 100.0, "INCREASING"),
            timeframe_15m=TimeframeData("BULLISH", 0.02, 150.0, "INCREASING"),
            timeframe_1h=TimeframeData("BULLISH", 0.03, 200.0, "STABLE"),
            timeframe_4h=TimeframeData("BULLISH", 0.04, 250.0, "STABLE"),
            alignment_score=4,
            confidence=0.0,
            overall_direction="NEUTRAL"
        )
        
        confidence = coordinator.calculate_signal_confidence(analysis)
        assert confidence == 1.0
    
    def test_calculate_signal_confidence_medium(self, coordinator):
        """Test confidence calculation with 3 aligned timeframes."""
        analysis = TimeframeAnalysis(
            timeframe_5m=TimeframeData("BULLISH", 0.01, 100.0, "INCREASING"),
            timeframe_15m=TimeframeData("BULLISH", 0.02, 150.0, "INCREASING"),
            timeframe_1h=TimeframeData("BULLISH", 0.03, 200.0, "STABLE"),
            timeframe_4h=TimeframeData("BEARISH", -0.04, 250.0, "STABLE"),
            alignment_score=3,
            confidence=0.0,
            overall_direction="NEUTRAL"
        )
        
        confidence = coordinator.calculate_signal_confidence(analysis)
        assert confidence == 0.7
    
    def test_calculate_signal_confidence_low(self, coordinator):
        """Test confidence calculation with <3 aligned timeframes."""
        analysis = TimeframeAnalysis(
            timeframe_5m=TimeframeData("BULLISH", 0.01, 100.0, "INCREASING"),
            timeframe_15m=TimeframeData("BEARISH", -0.02, 150.0, "DECREASING"),
            timeframe_1h=TimeframeData("NEUTRAL", 0.0, 200.0, "STABLE"),
            timeframe_4h=TimeframeData("BEARISH", -0.04, 250.0, "STABLE"),
            alignment_score=2,
            confidence=0.0,
            overall_direction="NEUTRAL"
        )
        
        confidence = coordinator.calculate_signal_confidence(analysis)
        assert confidence == 0.0
    
    def test_weighted_voting_bullish(self, coordinator):
        """Test weighted voting with bullish bias."""
        # 4h (40%) and 1h (30%) are bullish = 70% bullish weight
        analysis = TimeframeAnalysis(
            timeframe_5m=TimeframeData("BEARISH", -0.01, 100.0, "DECREASING"),
            timeframe_15m=TimeframeData("BEARISH", -0.02, 150.0, "DECREASING"),
            timeframe_1h=TimeframeData("BULLISH", 0.03, 200.0, "INCREASING"),
            timeframe_4h=TimeframeData("BULLISH", 0.04, 250.0, "INCREASING"),
            alignment_score=0,
            confidence=0.0,
            overall_direction="NEUTRAL"
        )
        
        direction = coordinator._determine_overall_direction(analysis)
        assert direction == "BULLISH"
    
    def test_weighted_voting_bearish(self, coordinator):
        """Test weighted voting with bearish bias."""
        # 4h (40%) and 1h (30%) are bearish = 70% bearish weight
        analysis = TimeframeAnalysis(
            timeframe_5m=TimeframeData("BULLISH", 0.01, 100.0, "INCREASING"),
            timeframe_15m=TimeframeData("BULLISH", 0.02, 150.0, "INCREASING"),
            timeframe_1h=TimeframeData("BEARISH", -0.03, 200.0, "DECREASING"),
            timeframe_4h=TimeframeData("BEARISH", -0.04, 250.0, "DECREASING"),
            alignment_score=0,
            confidence=0.0,
            overall_direction="NEUTRAL"
        )
        
        direction = coordinator._determine_overall_direction(analysis)
        assert direction == "BEARISH"
    
    def test_weighted_voting_neutral(self, coordinator):
        """Test weighted voting with no clear direction."""
        # Equal weights on both sides
        analysis = TimeframeAnalysis(
            timeframe_5m=TimeframeData("BULLISH", 0.01, 100.0, "INCREASING"),
            timeframe_15m=TimeframeData("BULLISH", 0.02, 150.0, "INCREASING"),
            timeframe_1h=TimeframeData("BEARISH", -0.03, 200.0, "DECREASING"),
            timeframe_4h=TimeframeData("NEUTRAL", 0.0, 250.0, "STABLE"),
            alignment_score=0,
            confidence=0.0,
            overall_direction="NEUTRAL"
        )
        
        direction = coordinator._determine_overall_direction(analysis)
        # 5m (10%) + 15m (20%) = 30% bullish
        # 1h (30%) = 30% bearish
        # Neither exceeds 50%, so should be NEUTRAL
        assert direction == "NEUTRAL"
    
    def test_conflicting_signals_with_missing_data(self, coordinator):
        """Test handling of conflicting signals when some timeframes are missing."""
        analysis = TimeframeAnalysis(
            timeframe_5m=None,
            timeframe_15m=TimeframeData("BULLISH", 0.02, 150.0, "INCREASING"),
            timeframe_1h=None,
            timeframe_4h=TimeframeData("BEARISH", -0.04, 250.0, "DECREASING"),
            alignment_score=0,
            confidence=0.0,
            overall_direction="NEUTRAL"
        )
        
        # Calculate alignment - should be 1 (only 1 direction has majority)
        alignment = coordinator.check_timeframe_alignment(analysis)
        assert alignment == 1
        
        # Calculate confidence - should be 0.0 (less than 3 aligned)
        confidence = coordinator.calculate_signal_confidence(analysis)
        assert confidence == 0.0
    
    def test_volume_trend_calculation_increasing(self, coordinator):
        """Test volume trend calculation for increasing volume."""
        # Create candles with increasing volume
        candles = []
        for i in range(20):
            volume = 100.0 + (i * 10.0)  # Increasing volume
            candles.append(
                Candle(
                    timestamp=i * 60000,
                    open=50000.0,
                    high=50100.0,
                    low=49900.0,
                    close=50000.0,
                    volume=volume
                )
            )
        
        volume_trend = coordinator._calculate_volume_trend(candles)
        assert volume_trend == "INCREASING"
    
    def test_volume_trend_calculation_decreasing(self, coordinator):
        """Test volume trend calculation for decreasing volume."""
        # Create candles with decreasing volume
        candles = []
        for i in range(20):
            volume = 200.0 - (i * 8.0)  # Decreasing volume more significantly
            candles.append(
                Candle(
                    timestamp=i * 60000,
                    open=50000.0,
                    high=50100.0,
                    low=49900.0,
                    close=50000.0,
                    volume=max(volume, 10.0)  # Ensure volume doesn't go negative
                )
            )
        
        volume_trend = coordinator._calculate_volume_trend(candles)
        assert volume_trend == "DECREASING"
    
    def test_volume_trend_calculation_stable(self, coordinator):
        """Test volume trend calculation for stable volume."""
        # Create candles with stable volume
        candles = []
        for i in range(20):
            volume = 100.0  # Stable volume
            candles.append(
                Candle(
                    timestamp=i * 60000,
                    open=50000.0,
                    high=50100.0,
                    low=49900.0,
                    close=50000.0,
                    volume=volume
                )
            )
        
        volume_trend = coordinator._calculate_volume_trend(candles)
        assert volume_trend == "STABLE"
    
    def test_analyze_timeframe_with_sufficient_data(self, coordinator):
        """Test timeframe analysis with sufficient candle data."""
        # Create 50 candles with bullish trend
        candles = []
        for i in range(50):
            price = 50000.0 + (i * 10.0)  # Increasing price
            candles.append(
                Candle(
                    timestamp=i * 60000,
                    open=price,
                    high=price + 50.0,
                    low=price - 50.0,
                    close=price + 10.0,
                    volume=100.0
                )
            )
        
        tf_data = coordinator._analyze_timeframe(candles, "15m")
        
        # Should detect bullish trend
        assert tf_data.trend == "BULLISH"
        assert tf_data.momentum > 0
        assert tf_data.volatility > 0


class TestTimeframeCoordinatorProperties:
    """Property-based tests for TimeframeCoordinator."""
    
    # Feature: advanced-trading-enhancements, Property 6: Confidence calculation correctness
    @settings(max_examples=100, deadline=None)
    @given(timeframe_analysis_strategy())
    def test_property_confidence_calculation_correctness(self, analysis):
        """Property 6: Confidence calculation correctness.
        
        For any timeframe analysis, if all 4 timeframes align, confidence must equal 1.0;
        if 3 align, confidence must equal 0.7; if fewer than 3 align, confidence must equal 0.0.
        
        Validates: Requirements 2.6, 2.7, 2.8
        """
        # Create coordinator instance
        config = Config()
        config.enable_multi_timeframe = True
        indicator_calc = IndicatorCalculator()
        coordinator = TimeframeCoordinator(config, indicator_calc)
        
        # Calculate alignment score
        analysis.alignment_score = coordinator.check_timeframe_alignment(analysis)
        
        # Calculate confidence
        confidence = coordinator.calculate_signal_confidence(analysis)
        
        # Verify confidence matches alignment rules
        if analysis.alignment_score >= 4:
            assert confidence == 1.0, f"Expected confidence 1.0 for alignment {analysis.alignment_score}, got {confidence}"
        elif analysis.alignment_score == 3:
            assert confidence == 0.7, f"Expected confidence 0.7 for alignment {analysis.alignment_score}, got {confidence}"
        else:
            assert confidence == 0.0, f"Expected confidence 0.0 for alignment {analysis.alignment_score}, got {confidence}"
        
        # Verify confidence is in valid range
        assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} out of range [0.0, 1.0]"
    
    # Feature: advanced-trading-enhancements, Property 7: Signal filtering
    @settings(max_examples=100, deadline=None)
    @given(timeframe_analysis_strategy())
    def test_property_signal_filtering(self, analysis):
        """Property 7: Signal filtering.
        
        For any timeframe analysis with fewer than 3 aligned timeframes,
        no trading signal should be generated (confidence = 0.0).
        
        Validates: Requirements 2.8
        """
        # Create coordinator instance
        config = Config()
        config.enable_multi_timeframe = True
        indicator_calc = IndicatorCalculator()
        coordinator = TimeframeCoordinator(config, indicator_calc)
        
        # Calculate alignment score
        analysis.alignment_score = coordinator.check_timeframe_alignment(analysis)
        
        # Calculate confidence
        confidence = coordinator.calculate_signal_confidence(analysis)
        
        # Verify that if alignment < 3, confidence is 0.0 (no signal)
        if analysis.alignment_score < 3:
            assert confidence == 0.0, f"Expected confidence 0.0 for alignment {analysis.alignment_score}, got {confidence}"
        
        # Also verify that if confidence is 0.0, alignment must be < 3
        if confidence == 0.0:
            assert analysis.alignment_score < 3, f"Confidence is 0.0 but alignment is {analysis.alignment_score}"
