"""Property-based tests for stop loss ladder functionality.

Feature: scaled-take-profit
Property 3: Stop loss monotonicity (Long)
Property 4: Stop loss monotonicity (Short)
Validates: Requirements 1.5
"""

import pytest
from hypothesis import given, strategies as st
from src.config import Config
from src.models import Position
from src.scaled_tp_manager import ScaledTakeProfitManager


# Helper strategy for generating valid positions
@st.composite
def position_strategy(draw, side=None):
    """Generate a valid Position for testing."""
    if side is None:
        side = draw(st.sampled_from(["LONG", "SHORT"]))
    
    entry_price = draw(st.floats(min_value=100.0, max_value=100000.0))
    quantity = draw(st.floats(min_value=0.001, max_value=10.0))
    leverage = draw(st.integers(min_value=1, max_value=10))
    
    # Calculate stop loss based on side
    if side == "LONG":
        stop_loss = entry_price * 0.98  # 2% below entry
    else:
        stop_loss = entry_price * 1.02  # 2% above entry
    
    return Position(
        symbol="BTCUSDT",
        side=side,
        entry_price=entry_price,
        quantity=quantity,
        leverage=leverage,
        stop_loss=stop_loss,
        trailing_stop=stop_loss,
        entry_time=1708450000000,
        unrealized_pnl=0.0,
        original_quantity=quantity,
        partial_exits=[],
        tp_levels_hit=[]
    )


# Feature: scaled-take-profit, Property 3: Stop loss monotonicity (Long)
@given(position=position_strategy(side="LONG"))
def test_stop_loss_monotonicity_long(position):
    """For any long position, after each TP level hit, the new stop loss must be >= previous stop loss.
    
    This property verifies that for LONG positions, the stop loss only moves upward
    (or stays the same) as TP levels are hit. The stop loss should never move down,
    which would increase risk.
    
    Property 3: Stop loss monotonicity (Long)
    Validates: Requirements 1.5
    """
    # Setup config with scaled TP enabled
    config = Config()
    config.enable_scaled_take_profit = True
    config.scaled_tp_levels = [
        {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: +3%
        {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: +5%
        {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: +8%
    ]
    
    manager = ScaledTakeProfitManager(config, client=None)
    
    # Track stop loss history
    stop_loss_history = [position.stop_loss]
    
    # Simulate hitting each TP level
    for i, tp_config in enumerate(config.scaled_tp_levels):
        tp_level = i + 1
        
        # Calculate target price for this TP level
        target_price = position.entry_price * (1 + tp_config["profit_pct"])
        
        # Check if TP level should trigger
        action = manager.check_take_profit_levels(position, target_price)
        
        if action is not None:
            # Update stop loss using the manager
            new_stop_loss = manager.update_stop_loss_ladder(position, tp_level)
            
            # Update position
            position.stop_loss = new_stop_loss
            position.tp_levels_hit.append(tp_level)
            position.quantity -= action.quantity
            
            # Record new stop loss
            stop_loss_history.append(new_stop_loss)
    
    # Property: For LONG positions, each new stop loss must be >= previous stop loss
    for i in range(len(stop_loss_history) - 1):
        current_sl = stop_loss_history[i]
        next_sl = stop_loss_history[i + 1]
        
        assert next_sl >= current_sl, \
            f"Stop loss moved down for LONG position: {current_sl:.2f} -> {next_sl:.2f}. " \
            f"Stop loss history: {stop_loss_history}"


# Feature: scaled-take-profit, Property 4: Stop loss monotonicity (Short)
@given(position=position_strategy(side="SHORT"))
def test_stop_loss_monotonicity_short(position):
    """For any short position, after each TP level hit, the new stop loss must be <= previous stop loss.
    
    This property verifies that for SHORT positions, the stop loss only moves downward
    (or stays the same) as TP levels are hit. The stop loss should never move up,
    which would increase risk.
    
    Property 4: Stop loss monotonicity (Short)
    Validates: Requirements 1.5
    """
    # Setup config with scaled TP enabled
    config = Config()
    config.enable_scaled_take_profit = True
    config.scaled_tp_levels = [
        {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: -3%
        {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: -5%
        {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: -8%
    ]
    
    manager = ScaledTakeProfitManager(config, client=None)
    
    # Track stop loss history
    stop_loss_history = [position.stop_loss]
    
    # Simulate hitting each TP level
    for i, tp_config in enumerate(config.scaled_tp_levels):
        tp_level = i + 1
        
        # Calculate target price for this TP level (price goes down for shorts)
        target_price = position.entry_price * (1 - tp_config["profit_pct"])
        
        # Check if TP level should trigger
        action = manager.check_take_profit_levels(position, target_price)
        
        if action is not None:
            # Update stop loss using the manager
            new_stop_loss = manager.update_stop_loss_ladder(position, tp_level)
            
            # Update position
            position.stop_loss = new_stop_loss
            position.tp_levels_hit.append(tp_level)
            position.quantity -= action.quantity
            
            # Record new stop loss
            stop_loss_history.append(new_stop_loss)
    
    # Property: For SHORT positions, each new stop loss must be <= previous stop loss
    for i in range(len(stop_loss_history) - 1):
        current_sl = stop_loss_history[i]
        next_sl = stop_loss_history[i + 1]
        
        assert next_sl <= current_sl, \
            f"Stop loss moved up for SHORT position: {current_sl:.2f} -> {next_sl:.2f}. " \
            f"Stop loss history: {stop_loss_history}"


# Unit tests for stop loss ladder logic
class TestStopLossLadder:
    """Unit tests for stop loss ladder functionality."""
    
    def test_tp1_moves_stop_to_breakeven_long(self):
        """When TP1 is hit on a LONG position, stop loss should move to breakeven (entry price)."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=49000.0,  # Initial SL below entry
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Update stop loss after TP1 hit
        new_stop_loss = manager.update_stop_loss_ladder(position, tp_level_hit=1)
        
        # Should be at breakeven (entry price)
        assert new_stop_loss == position.entry_price, \
            f"TP1 should move SL to breakeven: expected {position.entry_price}, got {new_stop_loss}"
    
    def test_tp2_moves_stop_to_tp1_price_long(self):
        """When TP2 is hit on a LONG position, stop loss should move to TP1 price."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: +3%
            {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: +5%
            {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: +8%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position with TP1 already hit
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.06,
            leverage=3,
            stop_loss=50000.0,  # Already at breakeven from TP1
            trailing_stop=50000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[],
            tp_levels_hit=[1]
        )
        
        # Update stop loss after TP2 hit
        new_stop_loss = manager.update_stop_loss_ladder(position, tp_level_hit=2)
        
        # Should be at TP1 price
        expected_tp1_price = 50000.0 * 1.03  # +3%
        assert abs(new_stop_loss - expected_tp1_price) < 0.01, \
            f"TP2 should move SL to TP1 price: expected {expected_tp1_price}, got {new_stop_loss}"
    
    def test_tp3_moves_stop_to_tp2_price_long(self):
        """When TP3 is hit on a LONG position, stop loss should move to TP2 price."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: +3%
            {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: +5%
            {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: +8%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position with TP1 and TP2 already hit
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.03,
            leverage=3,
            stop_loss=51500.0,  # Already at TP1 price from TP2
            trailing_stop=51500.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[],
            tp_levels_hit=[1, 2]
        )
        
        # Update stop loss after TP3 hit
        new_stop_loss = manager.update_stop_loss_ladder(position, tp_level_hit=3)
        
        # Should be at TP2 price
        expected_tp2_price = 50000.0 * 1.05  # +5%
        assert abs(new_stop_loss - expected_tp2_price) < 0.01, \
            f"TP3 should move SL to TP2 price: expected {expected_tp2_price}, got {new_stop_loss}"
    
    def test_tp1_moves_stop_to_breakeven_short(self):
        """When TP1 is hit on a SHORT position, stop loss should move to breakeven (entry price)."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a SHORT position
        position = Position(
            symbol="BTCUSDT",
            side="SHORT",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=51000.0,  # Initial SL above entry
            trailing_stop=51000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Update stop loss after TP1 hit
        new_stop_loss = manager.update_stop_loss_ladder(position, tp_level_hit=1)
        
        # Should be at breakeven (entry price)
        assert new_stop_loss == position.entry_price, \
            f"TP1 should move SL to breakeven for SHORT: expected {position.entry_price}, got {new_stop_loss}"
    
    def test_tp2_moves_stop_to_tp1_price_short(self):
        """When TP2 is hit on a SHORT position, stop loss should move to TP1 price."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: -3%
            {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: -5%
            {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: -8%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a SHORT position with TP1 already hit
        position = Position(
            symbol="BTCUSDT",
            side="SHORT",
            entry_price=50000.0,
            quantity=0.06,
            leverage=3,
            stop_loss=50000.0,  # Already at breakeven from TP1
            trailing_stop=50000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[],
            tp_levels_hit=[1]
        )
        
        # Update stop loss after TP2 hit
        new_stop_loss = manager.update_stop_loss_ladder(position, tp_level_hit=2)
        
        # Should be at TP1 price
        expected_tp1_price = 50000.0 * 0.97  # -3%
        assert abs(new_stop_loss - expected_tp1_price) < 0.01, \
            f"TP2 should move SL to TP1 price for SHORT: expected {expected_tp1_price}, got {new_stop_loss}"
    
    def test_stop_loss_never_moves_unfavorably_long(self):
        """Stop loss should never move down for LONG positions."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position with SL already above breakeven
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=52000.0,  # SL already above breakeven
            trailing_stop=52000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        old_stop_loss = position.stop_loss
        
        # Update stop loss after TP1 hit (which would normally move to breakeven)
        new_stop_loss = manager.update_stop_loss_ladder(position, tp_level_hit=1)
        
        # Should NOT move down - should stay at 52000 or higher
        assert new_stop_loss >= old_stop_loss, \
            f"Stop loss moved down for LONG: {old_stop_loss} -> {new_stop_loss}"
    
    def test_stop_loss_never_moves_unfavorably_short(self):
        """Stop loss should never move up for SHORT positions."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a SHORT position with SL already below breakeven
        position = Position(
            symbol="BTCUSDT",
            side="SHORT",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=48000.0,  # SL already below breakeven
            trailing_stop=48000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        old_stop_loss = position.stop_loss
        
        # Update stop loss after TP1 hit (which would normally move to breakeven)
        new_stop_loss = manager.update_stop_loss_ladder(position, tp_level_hit=1)
        
        # Should NOT move up - should stay at 48000 or lower
        assert new_stop_loss <= old_stop_loss, \
            f"Stop loss moved up for SHORT: {old_stop_loss} -> {new_stop_loss}"
    
    def test_stop_loss_ladder_progression_long(self):
        """Test complete stop loss ladder progression for LONG position."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: +3%
            {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: +5%
            {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: +8%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        entry_price = 50000.0
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=entry_price,
            quantity=0.1,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Hit TP1 - should move to breakeven
        sl_after_tp1 = manager.update_stop_loss_ladder(position, tp_level_hit=1)
        assert sl_after_tp1 == entry_price, f"After TP1: expected {entry_price}, got {sl_after_tp1}"
        position.stop_loss = sl_after_tp1
        position.tp_levels_hit.append(1)
        
        # Hit TP2 - should move to TP1 price
        sl_after_tp2 = manager.update_stop_loss_ladder(position, tp_level_hit=2)
        expected_tp1 = entry_price * 1.03
        assert abs(sl_after_tp2 - expected_tp1) < 0.01, \
            f"After TP2: expected {expected_tp1}, got {sl_after_tp2}"
        position.stop_loss = sl_after_tp2
        position.tp_levels_hit.append(2)
        
        # Hit TP3 - should move to TP2 price
        sl_after_tp3 = manager.update_stop_loss_ladder(position, tp_level_hit=3)
        expected_tp2 = entry_price * 1.05
        assert abs(sl_after_tp3 - expected_tp2) < 0.01, \
            f"After TP3: expected {expected_tp2}, got {sl_after_tp3}"
        
        # Verify progression: initial < breakeven < TP1 < TP2
        assert 49000.0 < sl_after_tp1 < sl_after_tp2 < sl_after_tp3, \
            f"Stop loss ladder not progressing correctly: 49000 < {sl_after_tp1} < {sl_after_tp2} < {sl_after_tp3}"
