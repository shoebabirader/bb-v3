"""Property-based and unit tests for Advanced Exit Manager."""

import time
import pytest
from hypothesis import given, strategies as st, settings, assume
from src.config import Config
from src.models import Position
from src.advanced_exit_manager import AdvancedExitManager


# ===== PROPERTY-BASED TESTS =====

# Feature: advanced-trading-enhancements, Property 19: Partial exit percentages
@settings(max_examples=100)
@given(
    entry_price=st.floats(min_value=1000.0, max_value=100000.0),
    atr=st.floats(min_value=10.0, max_value=1000.0),
    side=st.sampled_from(["LONG", "SHORT"])
)
def test_property_partial_exit_percentages(entry_price, atr, side):
    """Property 19: For any position reaching profit targets, the cumulative closed 
    percentage must equal 33% at 1.5x ATR, 66% at 3x ATR, and 100% at 5x ATR.
    
    Validates: Requirements 6.1, 6.2, 6.3
    """
    # Create config with default exit parameters
    config = Config()
    config.exit_partial_1_atr_multiplier = 1.5
    config.exit_partial_1_percentage = 0.33
    config.exit_partial_2_atr_multiplier = 3.0
    config.exit_partial_2_percentage = 0.33
    config.exit_final_atr_multiplier = 5.0
    
    manager = AdvancedExitManager(config)
    
    # Create position
    position = Position(
        symbol="BTCUSDT",
        side=side,
        entry_price=entry_price,
        quantity=1.0,
        leverage=3,
        stop_loss=entry_price - atr if side == "LONG" else entry_price + atr,
        trailing_stop=entry_price - atr if side == "LONG" else entry_price + atr,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Test by simulating price movement through all levels
    # We need to test each level independently with fresh manager instances
    # to verify the cumulative percentages
    
    # Test 1: At exactly 1.5x ATR, should close 33%
    manager1 = AdvancedExitManager(config)
    position1 = Position(
        symbol="BTCUSDT",
        side=side,
        entry_price=entry_price,
        quantity=1.0,
        leverage=3,
        stop_loss=entry_price - atr if side == "LONG" else entry_price + atr,
        trailing_stop=entry_price - atr if side == "LONG" else entry_price + atr,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    if side == "LONG":
        price_at_1_5x = entry_price + (1.51 * atr)  # Slightly above to avoid floating point issues
    else:
        price_at_1_5x = entry_price - (1.51 * atr)
    
    result1 = manager1.check_partial_exits(position1, price_at_1_5x, atr)
    assert result1 == 0.33, f"At 1.5x ATR, should close 33%, got {result1}"
    
    # Test 2: Simulate reaching 3x ATR after 1.5x was triggered
    manager2 = AdvancedExitManager(config)
    position2 = Position(
        symbol="BTCUSDT2",  # Different symbol to avoid tracking conflicts
        side=side,
        entry_price=entry_price,
        quantity=1.0,
        leverage=3,
        stop_loss=entry_price - atr if side == "LONG" else entry_price + atr,
        trailing_stop=entry_price - atr if side == "LONG" else entry_price + atr,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # First trigger 1.5x
    manager2.check_partial_exits(position2, price_at_1_5x, atr)
    
    # Then trigger 3x
    if side == "LONG":
        price_at_3x = entry_price + (3.01 * atr)  # Slightly above to avoid floating point issues
    else:
        price_at_3x = entry_price - (3.01 * atr)
    
    result2 = manager2.check_partial_exits(position2, price_at_3x, atr)
    assert result2 == 0.33, f"At 3x ATR (after 1.5x), should close another 33%, got {result2}"
    
    # Cumulative should be 66%
    cumulative_at_3x = 0.33 + 0.33
    assert abs(cumulative_at_3x - 0.66) < 0.01, f"Cumulative at 3x ATR should be 66%, got {cumulative_at_3x * 100}%"
    
    # Test 3: Simulate reaching 5x ATR after both previous exits
    manager3 = AdvancedExitManager(config)
    position3 = Position(
        symbol="BTCUSDT3",  # Different symbol
        side=side,
        entry_price=entry_price,
        quantity=1.0,
        leverage=3,
        stop_loss=entry_price - atr if side == "LONG" else entry_price + atr,
        trailing_stop=entry_price - atr if side == "LONG" else entry_price + atr,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Trigger 1.5x and 3x first
    manager3.check_partial_exits(position3, price_at_1_5x, atr)
    manager3.check_partial_exits(position3, price_at_3x, atr)
    
    # Then trigger 5x
    if side == "LONG":
        price_at_5x = entry_price + (5.01 * atr)  # Slightly above to avoid floating point issues
    else:
        price_at_5x = entry_price - (5.01 * atr)
    
    result3 = manager3.check_partial_exits(position3, price_at_5x, atr)
    # Remaining should be 34% (100% - 33% - 33%)
    assert result3 is not None and abs(result3 - 0.34) < 0.01, f"At 5x ATR, should close remaining ~34%, got {result3}"
    
    # Cumulative should be 100%
    cumulative_at_5x = 0.33 + 0.33 + result3
    assert abs(cumulative_at_5x - 1.0) < 0.01, f"Cumulative at 5x ATR should be 100%, got {cumulative_at_5x * 100}%"



# Feature: advanced-trading-enhancements, Property 20: Breakeven stop movement
@settings(max_examples=100)
@given(
    entry_price=st.floats(min_value=1000.0, max_value=100000.0),
    atr=st.floats(min_value=10.0, max_value=500.0),  # Limit ATR to reasonable range
    side=st.sampled_from(["LONG", "SHORT"]),
    profit_multiplier=st.floats(min_value=2.0, max_value=5.0)
)
def test_property_breakeven_stop_movement(entry_price, atr, side, profit_multiplier):
    """Property 20: For any position reaching 2x ATR profit, the stop-loss must be 
    moved to the entry price (breakeven).
    
    Validates: Requirements 6.6
    """
    # Create config
    config = Config()
    config.exit_breakeven_atr_multiplier = 2.0
    config.exit_tight_stop_atr_multiplier = 0.5
    
    manager = AdvancedExitManager(config)
    
    # Create position with initial stop at 1.5x ATR (reasonable distance)
    # This ensures the breakeven stop will always be better than initial stop
    initial_stop_distance = 1.5 * atr
    
    if side == "LONG":
        initial_stop = entry_price - initial_stop_distance
    else:
        initial_stop = entry_price + initial_stop_distance
    
    position = Position(
        symbol="BTCUSDT",
        side=side,
        entry_price=entry_price,
        quantity=1.0,
        leverage=3,
        stop_loss=initial_stop,
        trailing_stop=initial_stop,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Calculate price at profit_multiplier x ATR
    if side == "LONG":
        current_price = entry_price + (profit_multiplier * atr * 1.01)  # Add small buffer for floating point
    else:
        current_price = entry_price - (profit_multiplier * atr * 1.01)
    
    # Update dynamic stops
    manager.update_dynamic_stops(position, current_price, atr, momentum_reversed=False)
    
    # If profit >= 2x ATR, stop should be at breakeven (entry price)
    if profit_multiplier >= 2.0:
        if side == "LONG":
            # For long, stop should have moved up to entry price
            assert position.trailing_stop >= entry_price, \
                f"Long position at {profit_multiplier}x ATR profit should have stop at or above entry price. " \
                f"Entry: {entry_price}, Stop: {position.trailing_stop}"
            # Should be exactly at entry price (breakeven)
            assert abs(position.trailing_stop - entry_price) < 0.01, \
                f"Long position stop should be at breakeven (entry price)"
        else:
            # For short, stop should have moved down to entry price
            assert position.trailing_stop <= entry_price, \
                f"Short position at {profit_multiplier}x ATR profit should have stop at or below entry price. " \
                f"Entry: {entry_price}, Stop: {position.trailing_stop}"
            # Should be exactly at entry price (breakeven)
            assert abs(position.trailing_stop - entry_price) < 0.01, \
                f"Short position stop should be at breakeven (entry price)"


# ===== UNIT TESTS =====

def test_partial_exits_at_each_level():
    """Test partial exits are triggered at each profit level."""
    config = Config()
    config.exit_partial_1_atr_multiplier = 1.5
    config.exit_partial_1_percentage = 0.33
    config.exit_partial_2_atr_multiplier = 3.0
    config.exit_partial_2_percentage = 0.33
    config.exit_final_atr_multiplier = 5.0
    
    manager = AdvancedExitManager(config)
    
    # Create long position
    entry_price = 50000.0
    atr = 500.0
    position = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=entry_price,
        quantity=1.0,
        leverage=3,
        stop_loss=entry_price - (2.0 * atr),
        trailing_stop=entry_price - (2.0 * atr),
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Test at 1.5x ATR (should trigger partial_1)
    price_1 = entry_price + (1.5 * atr)
    result = manager.check_partial_exits(position, price_1, atr)
    assert result == 0.33, "Should close 33% at 1.5x ATR"
    
    # Test at 3x ATR (should trigger partial_2)
    price_2 = entry_price + (3.0 * atr)
    result = manager.check_partial_exits(position, price_2, atr)
    assert result == 0.33, "Should close another 33% at 3x ATR"
    
    # Test at 5x ATR (should trigger final)
    price_3 = entry_price + (5.0 * atr)
    result = manager.check_partial_exits(position, price_3, atr)
    assert abs(result - 0.34) < 0.01, "Should close remaining ~34% at 5x ATR"


def test_partial_exits_short_position():
    """Test partial exits work correctly for short positions."""
    config = Config()
    config.exit_partial_1_atr_multiplier = 1.5
    config.exit_partial_1_percentage = 0.33
    config.exit_partial_2_atr_multiplier = 3.0
    config.exit_partial_2_percentage = 0.33
    config.exit_final_atr_multiplier = 5.0
    
    manager = AdvancedExitManager(config)
    
    # Create short position
    entry_price = 50000.0
    atr = 500.0
    position = Position(
        symbol="BTCUSDT",
        side="SHORT",
        entry_price=entry_price,
        quantity=1.0,
        leverage=3,
        stop_loss=entry_price + (2.0 * atr),
        trailing_stop=entry_price + (2.0 * atr),
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Test at 1.5x ATR profit (price moves down for short)
    price_1 = entry_price - (1.5 * atr)
    result = manager.check_partial_exits(position, price_1, atr)
    assert result == 0.33, "Should close 33% at 1.5x ATR for short"
    
    # Test at 3x ATR profit
    price_2 = entry_price - (3.0 * atr)
    result = manager.check_partial_exits(position, price_2, atr)
    assert result == 0.33, "Should close another 33% at 3x ATR for short"


def test_no_partial_exit_before_threshold():
    """Test that no partial exit is triggered before reaching thresholds."""
    config = Config()
    manager = AdvancedExitManager(config)
    
    entry_price = 50000.0
    atr = 500.0
    position = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=entry_price,
        quantity=1.0,
        leverage=3,
        stop_loss=entry_price - (2.0 * atr),
        trailing_stop=entry_price - (2.0 * atr),
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Test at 1x ATR (below first threshold)
    price = entry_price + (1.0 * atr)
    result = manager.check_partial_exits(position, price, atr)
    assert result is None, "Should not trigger exit below 1.5x ATR"


def test_breakeven_stop_at_2x_atr():
    """Test stop moves to breakeven at 2x ATR profit."""
    config = Config()
    config.exit_breakeven_atr_multiplier = 2.0
    
    manager = AdvancedExitManager(config)
    
    entry_price = 50000.0
    atr = 500.0
    
    # Test long position
    position_long = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=entry_price,
        quantity=1.0,
        leverage=3,
        stop_loss=entry_price - (2.0 * atr),
        trailing_stop=entry_price - (2.0 * atr),
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Price at 2x ATR profit
    current_price = entry_price + (2.0 * atr)
    manager.update_dynamic_stops(position_long, current_price, atr, momentum_reversed=False)
    
    assert position_long.trailing_stop == entry_price, "Long stop should move to entry price at 2x ATR"
    
    # Test short position
    position_short = Position(
        symbol="BTCUSDT",
        side="SHORT",
        entry_price=entry_price,
        quantity=1.0,
        leverage=3,
        stop_loss=entry_price + (2.0 * atr),
        trailing_stop=entry_price + (2.0 * atr),
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Price at 2x ATR profit (moves down for short)
    current_price = entry_price - (2.0 * atr)
    manager.update_dynamic_stops(position_short, current_price, atr, momentum_reversed=False)
    
    assert position_short.trailing_stop == entry_price, "Short stop should move to entry price at 2x ATR"


def test_tight_stop_on_momentum_reversal():
    """Test stop tightens to 0.5x ATR on momentum reversal while in profit."""
    config = Config()
    config.exit_tight_stop_atr_multiplier = 0.5
    
    manager = AdvancedExitManager(config)
    
    entry_price = 50000.0
    atr = 500.0
    
    # Create long position in profit
    position = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=entry_price,
        quantity=1.0,
        leverage=3,
        stop_loss=entry_price - (2.0 * atr),
        trailing_stop=entry_price - (2.0 * atr),
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Price at 1.5x ATR profit
    current_price = entry_price + (1.5 * atr)
    
    # Update with momentum reversal
    manager.update_dynamic_stops(position, current_price, atr, momentum_reversed=True)
    
    # Stop should be tightened to current_price - 0.5x ATR
    expected_stop = current_price - (0.5 * atr)
    assert position.trailing_stop == expected_stop, "Stop should tighten to 0.5x ATR on momentum reversal"


def test_time_based_exit():
    """Test time-based exit after 24 hours."""
    config = Config()
    config.exit_max_hold_time_hours = 24
    
    manager = AdvancedExitManager(config)
    
    # Create position opened 25 hours ago
    entry_time = int(time.time() * 1000) - (25 * 3600 * 1000)
    position = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=50000.0,
        quantity=1.0,
        leverage=3,
        stop_loss=49000.0,
        trailing_stop=49000.0,
        entry_time=entry_time,
        unrealized_pnl=0.0
    )
    
    # Should trigger time-based exit
    assert manager.check_time_based_exit(position) is True, "Should exit after 24 hours"
    
    # Create position opened 20 hours ago
    entry_time = int(time.time() * 1000) - (20 * 3600 * 1000)
    position_recent = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=50000.0,
        quantity=1.0,
        leverage=3,
        stop_loss=49000.0,
        trailing_stop=49000.0,
        entry_time=entry_time,
        unrealized_pnl=0.0
    )
    
    # Should not trigger time-based exit
    assert manager.check_time_based_exit(position_recent) is False, "Should not exit before 24 hours"


def test_regime_based_exit():
    """Test regime-based exit when changing from trending to ranging."""
    config = Config()
    config.exit_regime_change_enabled = True
    
    manager = AdvancedExitManager(config)
    
    position = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=50000.0,
        quantity=1.0,
        leverage=3,
        stop_loss=49000.0,
        trailing_stop=49000.0,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Test regime change from TRENDING_BULLISH to RANGING
    assert manager.check_regime_exit(position, "RANGING", "TRENDING_BULLISH") is True
    
    # Test regime change from TRENDING_BEARISH to RANGING
    assert manager.check_regime_exit(position, "RANGING", "TRENDING_BEARISH") is True
    
    # Test regime staying TRENDING
    assert manager.check_regime_exit(position, "TRENDING_BULLISH", "TRENDING_BULLISH") is False
    
    # Test regime change from RANGING to TRENDING (should not exit)
    assert manager.check_regime_exit(position, "TRENDING_BULLISH", "RANGING") is False


def test_regime_exit_disabled():
    """Test regime-based exit can be disabled."""
    config = Config()
    config.exit_regime_change_enabled = False
    
    manager = AdvancedExitManager(config)
    
    position = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=50000.0,
        quantity=1.0,
        leverage=3,
        stop_loss=49000.0,
        trailing_stop=49000.0,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Should not exit even with regime change when disabled
    assert manager.check_regime_exit(position, "RANGING", "TRENDING_BULLISH") is False


def test_exit_tracking_reset():
    """Test exit tracking can be reset for a symbol."""
    config = Config()
    manager = AdvancedExitManager(config)
    
    position = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=50000.0,
        quantity=1.0,
        leverage=3,
        stop_loss=49000.0,
        trailing_stop=49000.0,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    # Trigger some exits
    manager.check_partial_exits(position, 50750.0, 500.0)
    
    # Verify exits were tracked
    triggered = manager.get_triggered_exits("BTCUSDT")
    assert len(triggered) > 0
    
    # Reset tracking
    manager.reset_exit_tracking("BTCUSDT")
    
    # Verify tracking was cleared
    triggered = manager.get_triggered_exits("BTCUSDT")
    assert len(triggered) == 0
