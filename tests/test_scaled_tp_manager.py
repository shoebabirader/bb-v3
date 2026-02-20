"""Property-based and unit tests for Scaled Take Profit Manager."""

import pytest
from hypothesis import given, strategies as st, assume
from src.config import Config
from src.models import Position, PartialCloseAction
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


# Feature: scaled-take-profit, Property 1: TP level ordering
@given(
    position=position_strategy(),
    price_multipliers=st.lists(
        st.floats(min_value=1.0, max_value=1.15),
        min_size=3,
        max_size=3
    )
)
def test_tp_levels_hit_in_ascending_order(position, price_multipliers):
    """For any position with scaled TP enabled, TP levels must be hit in ascending order.
    
    This property verifies that when checking multiple prices, TP levels are only
    triggered in order (TP1 before TP2 before TP3). Once a level is hit and marked,
    the next check should only trigger the next level in sequence.
    
    Property 1: TP level ordering
    Validates: Requirements 1.1, 1.2, 1.3
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
    
    # Sort price multipliers to ensure ascending order
    price_multipliers = sorted(price_multipliers)
    
    # Ensure multipliers are distinct enough to trigger different TP levels
    assume(price_multipliers[1] - price_multipliers[0] > 0.01)
    assume(price_multipliers[2] - price_multipliers[1] > 0.01)
    
    # Calculate prices that would hit each TP level
    if position.side == "LONG":
        # For longs, prices increase
        price_tp1 = position.entry_price * 1.03  # +3%
        price_tp2 = position.entry_price * 1.05  # +5%
        price_tp3 = position.entry_price * 1.08  # +8%
        
        # Test prices in ascending order
        test_prices = [
            position.entry_price * price_multipliers[0],  # Below or at TP1
            position.entry_price * price_multipliers[1],  # Between TP1 and TP2
            position.entry_price * price_multipliers[2]   # At or above TP2
        ]
    else:  # SHORT
        # For shorts, prices decrease
        price_tp1 = position.entry_price * 0.97  # -3%
        price_tp2 = position.entry_price * 0.95  # -5%
        price_tp3 = position.entry_price * 0.92  # -8%
        
        # Test prices in descending order (profit for shorts)
        test_prices = [
            position.entry_price * (2.0 - price_multipliers[0]),  # Below or at TP1
            position.entry_price * (2.0 - price_multipliers[1]),  # Between TP1 and TP2
            position.entry_price * (2.0 - price_multipliers[2])   # At or above TP2
        ]
    
    # Track which levels get hit
    levels_hit_sequence = []
    
    # Simulate price movement and check TP levels
    for i, test_price in enumerate(test_prices):
        action = manager.check_take_profit_levels(position, test_price)
        
        if action is not None:
            levels_hit_sequence.append(action.tp_level)
            
            # Mark this level as hit in the position
            position.tp_levels_hit.append(action.tp_level)
            
            # Update position quantity (simulate partial close)
            position.quantity *= (1.0 - action.close_pct)
    
    # Property: If any TP levels were hit, they must be in ascending order
    if len(levels_hit_sequence) > 1:
        for i in range(len(levels_hit_sequence) - 1):
            assert levels_hit_sequence[i] < levels_hit_sequence[i + 1], \
                f"TP levels not in ascending order: {levels_hit_sequence}"
    
    # Property: TP levels must be consecutive (no skipping)
    if len(levels_hit_sequence) > 0:
        # First level hit should be TP1
        assert levels_hit_sequence[0] == 1, \
            f"First TP level hit should be 1, got {levels_hit_sequence[0]}"
        
        # All subsequent levels should be consecutive
        for i in range(len(levels_hit_sequence) - 1):
            assert levels_hit_sequence[i + 1] == levels_hit_sequence[i] + 1, \
                f"TP levels not consecutive: {levels_hit_sequence}"


# Feature: scaled-take-profit, Property 1: TP level ordering (unit test variant)
class TestTPLevelOrdering:
    """Unit tests for TP level ordering property."""
    
    def test_tp1_must_be_hit_before_tp2(self):
        """TP1 must be hit before TP2 can be triggered."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: +3%
            {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: +5%
            {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: +8%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
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
        
        # Price jumps directly to TP2 level (skipping TP1)
        price_at_tp2 = 50000.0 * 1.05  # +5%
        
        # Check what happens - should still hit TP1 first
        action = manager.check_take_profit_levels(position, price_at_tp2)
        
        # Should trigger TP1, not TP2
        assert action is not None
        assert action.tp_level == 1, "TP1 must be hit first even if price is at TP2"
    
    def test_tp2_only_triggers_after_tp1_marked(self):
        """TP2 should only trigger after TP1 is marked as hit."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: +3%
            {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: +5%
            {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: +8%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
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
        
        # Price at TP2 level
        price_at_tp2 = 50000.0 * 1.05  # +5%
        
        # First check - should hit TP1
        action1 = manager.check_take_profit_levels(position, price_at_tp2)
        assert action1.tp_level == 1
        
        # Mark TP1 as hit
        position.tp_levels_hit.append(1)
        position.quantity *= (1.0 - action1.close_pct)
        
        # Second check at same price - should now hit TP2
        action2 = manager.check_take_profit_levels(position, price_at_tp2)
        assert action2 is not None
        assert action2.tp_level == 2, "TP2 should trigger after TP1 is marked"
    
    def test_short_position_tp_ordering(self):
        """TP levels for SHORT positions must also be in order."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: -3%
            {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: -5%
            {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: -8%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a SHORT position
        position = Position(
            symbol="BTCUSDT",
            side="SHORT",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=51000.0,
            trailing_stop=51000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Price drops to TP2 level (skipping TP1)
        price_at_tp2 = 50000.0 * 0.95  # -5%
        
        # Check what happens - should still hit TP1 first
        action = manager.check_take_profit_levels(position, price_at_tp2)
        
        # Should trigger TP1, not TP2
        assert action is not None
        assert action.tp_level == 1, "TP1 must be hit first for SHORT positions too"
    
    def test_all_three_levels_hit_in_order(self):
        """All three TP levels should be hit in order 1, 2, 3."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: +3%
            {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: +5%
            {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: +8%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
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
        
        # Price reaches TP3 level (all TPs should be hit)
        price_at_tp3 = 50000.0 * 1.08  # +8%
        
        levels_hit = []
        
        # Check TP1
        action1 = manager.check_take_profit_levels(position, price_at_tp3)
        assert action1.tp_level == 1
        levels_hit.append(action1.tp_level)
        position.tp_levels_hit.append(1)
        position.quantity *= (1.0 - action1.close_pct)
        
        # Check TP2
        action2 = manager.check_take_profit_levels(position, price_at_tp3)
        assert action2.tp_level == 2
        levels_hit.append(action2.tp_level)
        position.tp_levels_hit.append(2)
        position.quantity *= (1.0 - action2.close_pct)
        
        # Check TP3
        action3 = manager.check_take_profit_levels(position, price_at_tp3)
        assert action3.tp_level == 3
        levels_hit.append(action3.tp_level)
        position.tp_levels_hit.append(3)
        
        # Verify order
        assert levels_hit == [1, 2, 3], "TP levels must be hit in order 1, 2, 3"
    
    def test_no_tp_triggered_when_disabled(self):
        """No TP levels should trigger when scaled TP is disabled."""
        config = Config()
        config.enable_scaled_take_profit = False  # Disabled
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
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
        
        # Price at TP1 level
        price_at_tp1 = 50000.0 * 1.03
        
        # Should return None when disabled
        action = manager.check_take_profit_levels(position, price_at_tp1)
        assert action is None, "No TP should trigger when scaled TP is disabled"
    
    def test_already_hit_levels_not_retriggered(self):
        """TP levels already marked as hit should not be triggered again."""
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
            quantity=0.06,  # 40% already closed
            leverage=3,
            stop_loss=50000.0,  # Moved to breakeven
            trailing_stop=50000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[{"tp_level": 1, "quantity": 0.04}],
            tp_levels_hit=[1]  # TP1 already hit
        )
        
        # Price at TP1 level
        price_at_tp1 = 50000.0 * 1.03
        
        # Should not trigger TP1 again, should return None or TP2
        action = manager.check_take_profit_levels(position, price_at_tp1)
        
        if action is not None:
            assert action.tp_level != 1, "TP1 should not be triggered again"


# Feature: scaled-take-profit, Property 2: Position size conservation
@given(
    position=position_strategy(),
    num_partials=st.integers(min_value=1, max_value=5)
)
def test_position_size_conservation(position, num_partials):
    """For any position after partial closes, sum of closed + remaining must equal original.
    
    This property verifies that when we execute partial closes, the total quantity
    is conserved. The sum of all closed quantities plus the remaining quantity
    must always equal the original quantity.
    
    Property 2: Position size conservation
    Validates: Requirements 1.1, 1.2, 1.3
    """
    # Setup config with scaled TP enabled
    config = Config()
    config.enable_scaled_take_profit = True
    
    # Generate random close percentages that sum to 1.0
    # We'll create num_partials partial closes
    close_percentages = []
    remaining = 1.0
    
    for i in range(num_partials - 1):
        # Each partial takes a random portion of what's remaining
        # Leave at least 0.1 for subsequent partials
        max_pct = remaining - (0.1 * (num_partials - i - 1))
        if max_pct <= 0.1:
            max_pct = 0.1
        
        pct = min(max_pct, remaining * 0.5)  # Take at most 50% of remaining
        close_percentages.append(pct)
        remaining -= pct
    
    # Last partial takes whatever is left
    close_percentages.append(remaining)
    
    # Ensure we have valid percentages
    assume(all(0.0 < pct <= 1.0 for pct in close_percentages))
    assume(abs(sum(close_percentages) - 1.0) < 0.0001)  # Should sum to 1.0
    
    # Create TP levels from close percentages
    # Use increasing profit percentages
    tp_levels = []
    for i, close_pct in enumerate(close_percentages):
        profit_pct = 0.02 * (i + 1)  # 2%, 4%, 6%, etc.
        tp_levels.append({"profit_pct": profit_pct, "close_pct": close_pct})
    
    config.scaled_tp_levels = tp_levels
    
    manager = ScaledTakeProfitManager(config, client=None)
    
    # Track original quantity
    original_quantity = position.quantity
    position.original_quantity = original_quantity
    
    # Track all closed quantities
    total_closed = 0.0
    
    # Simulate partial closes
    for i, tp_config in enumerate(tp_levels):
        tp_level = i + 1
        
        # Calculate target price
        if position.side == "LONG":
            target_price = position.entry_price * (1 + tp_config["profit_pct"])
        else:
            target_price = position.entry_price * (1 - tp_config["profit_pct"])
        
        # Check if TP level should trigger
        action = manager.check_take_profit_levels(position, target_price)
        
        if action is not None:
            # Record the quantity being closed
            closed_quantity = action.quantity
            total_closed += closed_quantity
            
            # Update position (simulate partial close)
            position.quantity -= closed_quantity
            position.tp_levels_hit.append(tp_level)
            
            # Record in partial exits
            position.partial_exits.append({
                "tp_level": tp_level,
                "quantity": closed_quantity,
                "price": target_price
            })
    
    # Property: Sum of closed quantities + remaining quantity = original quantity
    remaining_quantity = position.quantity
    total_accounted = total_closed + remaining_quantity
    
    # Allow for small floating point errors
    assert abs(total_accounted - original_quantity) < 0.0001, \
        f"Position size not conserved: original={original_quantity:.6f}, " \
        f"closed={total_closed:.6f}, remaining={remaining_quantity:.6f}, " \
        f"total={total_accounted:.6f}"
    
    # Additional check: remaining quantity should be non-negative (allow tiny floating point errors)
    assert remaining_quantity >= -0.0001, \
        f"Remaining quantity cannot be negative: {remaining_quantity:.6f}"
    
    # Additional check: we shouldn't close more than we started with (allow tiny floating point errors)
    assert total_closed <= original_quantity + 0.0001, \
        f"Cannot close more than original quantity: closed={total_closed:.6f}, " \
        f"original={original_quantity:.6f}"


# Feature: scaled-take-profit, Property 2: Position size conservation (unit test variant)
class TestPositionSizeConservation:
    """Unit tests for position size conservation property."""
    
    def test_single_partial_close_conserves_size(self):
        """A single partial close should conserve total position size."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # Close 40%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        original_qty = 1.0
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=original_qty,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=original_qty,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Price reaches TP1
        price_at_tp1 = 50000.0 * 1.03
        action = manager.check_take_profit_levels(position, price_at_tp1)
        
        assert action is not None
        closed_qty = action.quantity
        
        # Simulate the close
        position.quantity -= closed_qty
        
        # Check conservation
        total = closed_qty + position.quantity
        assert abs(total - original_qty) < 0.0001, \
            f"Size not conserved: {closed_qty} + {position.quantity} != {original_qty}"
    
    def test_multiple_partial_closes_conserve_size(self):
        """Multiple partial closes should conserve total position size."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # Close 40%
            {"profit_pct": 0.05, "close_pct": 0.30},  # Close 30%
            {"profit_pct": 0.08, "close_pct": 0.30}   # Close 30%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        original_qty = 1.0
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=original_qty,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=original_qty,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Track all closes
        total_closed = 0.0
        
        # Hit all three TP levels
        for i, tp_config in enumerate(config.scaled_tp_levels):
            tp_level = i + 1
            target_price = 50000.0 * (1 + tp_config["profit_pct"])
            
            action = manager.check_take_profit_levels(position, target_price)
            assert action is not None
            
            closed_qty = action.quantity
            total_closed += closed_qty
            
            # Simulate the close
            position.quantity -= closed_qty
            position.tp_levels_hit.append(tp_level)
        
        # Check conservation
        total = total_closed + position.quantity
        assert abs(total - original_qty) < 0.0001, \
            f"Size not conserved: {total_closed} + {position.quantity} != {original_qty}"
        
        # After all TPs hit, remaining should be ~0
        assert abs(position.quantity) < 0.0001, \
            f"After all TPs, remaining should be ~0, got {position.quantity}"
    
    def test_partial_close_percentages_applied_to_original(self):
        """Close percentages should be applied to original quantity, not remaining."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.50},  # Close 50% of original
            {"profit_pct": 0.05, "close_pct": 0.50},  # Close 50% of original
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        original_qty = 1.0
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=original_qty,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=original_qty,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Hit TP1 - should close 50% of 1.0 = 0.5
        price_at_tp1 = 50000.0 * 1.03
        action1 = manager.check_take_profit_levels(position, price_at_tp1)
        assert action1 is not None
        assert abs(action1.quantity - 0.5) < 0.0001, \
            f"TP1 should close 0.5 (50% of original), got {action1.quantity}"
        
        # Simulate close
        position.quantity -= action1.quantity
        position.tp_levels_hit.append(1)
        
        # Hit TP2 - should close 50% of original 1.0 = 0.5 (not 50% of remaining 0.5)
        price_at_tp2 = 50000.0 * 1.05
        action2 = manager.check_take_profit_levels(position, price_at_tp2)
        assert action2 is not None
        assert abs(action2.quantity - 0.5) < 0.0001, \
            f"TP2 should close 0.5 (50% of original 1.0), got {action2.quantity}"
        
        # Simulate close
        position.quantity -= action2.quantity
        
        # Check final state - should be 0 (closed 100% total)
        assert abs(position.quantity) < 0.0001, \
            f"Final remaining should be 0, got {position.quantity}"
        
        # Check conservation
        total = action1.quantity + action2.quantity + position.quantity
        assert abs(total - original_qty) < 0.0001, \
            f"Size not conserved: {total} != {original_qty}"
    
    def test_short_position_size_conservation(self):
        """Position size conservation should work for SHORT positions too."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a SHORT position
        original_qty = 1.0
        position = Position(
            symbol="BTCUSDT",
            side="SHORT",
            entry_price=50000.0,
            quantity=original_qty,
            leverage=3,
            stop_loss=51000.0,
            trailing_stop=51000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=original_qty,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Track all closes
        total_closed = 0.0
        
        # Hit all three TP levels
        for i, tp_config in enumerate(config.scaled_tp_levels):
            tp_level = i + 1
            target_price = 50000.0 * (1 - tp_config["profit_pct"])
            
            action = manager.check_take_profit_levels(position, target_price)
            assert action is not None
            
            closed_qty = action.quantity
            total_closed += closed_qty
            
            # Simulate the close
            position.quantity -= closed_qty
            position.tp_levels_hit.append(tp_level)
        
        # Check conservation
        total = total_closed + position.quantity
        assert abs(total - original_qty) < 0.0001, \
            f"Size not conserved for SHORT: {total_closed} + {position.quantity} != {original_qty}"


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


# Feature: scaled-take-profit, Property 6: Minimum order size compliance
@given(
    original_quantity=st.floats(min_value=0.001, max_value=10.0),
    min_order_size=st.floats(min_value=0.0001, max_value=0.1),
    close_percentages=st.lists(
        st.floats(min_value=0.1, max_value=0.5),
        min_size=3,
        max_size=3
    )
)
def test_minimum_order_size_compliance(original_quantity, min_order_size, close_percentages):
    """For any partial close action, if the calculated quantity is below the minimum order size,
    the action must be skipped or adjusted.
    
    This property verifies that:
    1. Partial closes below minimum are skipped
    2. Remaining position below minimum is closed entirely
    3. All partials below minimum triggers fallback to single TP
    
    Property 6: Minimum order size compliance
    Validates: Requirements 3.1, 3.2, 3.3
    """
    # Normalize close percentages to sum to 1.0
    total = sum(close_percentages)
    close_percentages = [pct / total for pct in close_percentages]
    
    # Ensure we have valid test data
    assume(original_quantity > min_order_size)
    assume(all(0.0 < pct <= 1.0 for pct in close_percentages))
    assume(abs(sum(close_percentages) - 1.0) < 0.0001)
    
    # Setup config with scaled TP enabled
    config = Config()
    config.enable_scaled_take_profit = True
    config.scaled_tp_min_order_size = min_order_size
    config.scaled_tp_fallback_to_single = True
    
    # Create TP levels from close percentages
    tp_levels = []
    for i, close_pct in enumerate(close_percentages):
        profit_pct = 0.02 * (i + 1)  # 2%, 4%, 6%
        tp_levels.append({"profit_pct": profit_pct, "close_pct": close_pct})
    
    config.scaled_tp_levels = tp_levels
    
    manager = ScaledTakeProfitManager(config, client=None)
    
    # Create a LONG position
    position = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=50000.0,
        quantity=original_quantity,
        leverage=3,
        stop_loss=49000.0,
        trailing_stop=49000.0,
        entry_time=1708450000000,
        unrealized_pnl=0.0,
        original_quantity=original_quantity,
        partial_exits=[],
        tp_levels_hit=[]
    )
    
    # Track all actions taken
    actions_taken = []
    fallback_triggered = False
    
    # Simulate hitting each TP level
    for i, tp_config in enumerate(tp_levels):
        tp_level = i + 1
        
        # Calculate target price
        target_price = position.entry_price * (1 + tp_config["profit_pct"])
        
        # Check if TP level should trigger
        action = manager.check_take_profit_levels(position, target_price)
        
        if action is None:
            # Could be fallback or just no action
            # Check if this is a fallback scenario
            calculated_qty = position.original_quantity * tp_config["close_pct"]
            if calculated_qty < min_order_size and tp_level == 1:
                # Check if all partials are below minimum
                all_below = all(
                    position.original_quantity * tp["close_pct"] < min_order_size
                    for tp in tp_levels
                )
                if all_below:
                    fallback_triggered = True
            break
        
        # Property 1: If action is returned, quantity must be >= minimum order size
        assert action.quantity >= min_order_size, \
            f"Action quantity {action.quantity:.6f} is below minimum {min_order_size:.6f}"
        
        # Record the action
        actions_taken.append({
            "tp_level": action.tp_level,
            "quantity": action.quantity,
            "close_pct": action.close_pct
        })
        
        # Simulate the partial close
        old_quantity = position.quantity
        position.quantity -= action.quantity
        position.tp_levels_hit.append(tp_level)
        
        # Property 2: Remaining quantity should not be below minimum (unless it's zero)
        if position.quantity > 0:
            # Allow for small floating point errors
            assert position.quantity >= min_order_size - 0.0001 or abs(position.quantity) < 0.0001, \
                f"Remaining quantity {position.quantity:.6f} is below minimum {min_order_size:.6f}"
        
        # Record in partial exits
        position.partial_exits.append({
            "tp_level": tp_level,
            "quantity": action.quantity,
            "price": target_price
        })
    
    # Property 3: If all partials would be below minimum, fallback should be triggered
    all_partials_below_min = all(
        original_quantity * tp["close_pct"] < min_order_size
        for tp in tp_levels
    )
    
    if all_partials_below_min and config.scaled_tp_fallback_to_single:
        assert fallback_triggered or len(actions_taken) == 0, \
            "Fallback should be triggered when all partials are below minimum"
    
    # Property 4: No action should close less than minimum (unless closing entire remaining)
    for action_info in actions_taken:
        assert action_info["quantity"] >= min_order_size, \
            f"Action closed {action_info['quantity']:.6f} which is below minimum {min_order_size:.6f}"


# Unit tests for minimum order size handling
class TestMinimumOrderSizeHandling:
    """Unit tests for minimum order size compliance."""
    
    def test_skip_tp_level_below_minimum(self):
        """TP levels with quantity below minimum should be skipped."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_min_order_size = 0.05  # Set high minimum
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # Will be 0.04 (below min)
            {"profit_pct": 0.05, "close_pct": 0.30},  # Will be 0.03 (below min)
            {"profit_pct": 0.08, "close_pct": 0.30}   # Will be 0.03 (below min)
        ]
        config.scaled_tp_fallback_to_single = False  # Don't fallback
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position with small quantity
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,  # Small quantity
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Price reaches TP1 (40% of 0.1 = 0.04, below 0.05 minimum)
        price_at_tp1 = 50000.0 * 1.03
        action = manager.check_take_profit_levels(position, price_at_tp1)
        
        # Should be None (skipped) because quantity is below minimum
        assert action is None, "TP1 should be skipped when quantity is below minimum"
    
    def test_close_remaining_when_below_minimum(self):
        """When remaining position would be below minimum, close entire remaining."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_min_order_size = 0.025  # Set minimum
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.80},  # Close 80%, leaving 20%
            {"profit_pct": 0.05, "close_pct": 0.20}   # Close remaining 20%
        ]
        config.scaled_tp_fallback_to_single = False
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
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
        
        # Price reaches TP1 (80% of 0.1 = 0.08, leaving 0.02 which is below 0.025 minimum)
        price_at_tp1 = 50000.0 * 1.03
        action = manager.check_take_profit_levels(position, price_at_tp1)
        
        # Should close entire position (0.1) instead of just 0.08
        assert action is not None
        assert action.quantity == 0.1, \
            f"Should close entire position (0.1) when remaining would be below minimum, got {action.quantity}"
    
    def test_fallback_to_single_tp_when_all_below_minimum(self):
        """When all partial closes are below minimum, fall back to single TP."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_min_order_size = 0.5  # Set very high minimum
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # Will be 0.04 (below min)
            {"profit_pct": 0.05, "close_pct": 0.30},  # Will be 0.03 (below min)
            {"profit_pct": 0.08, "close_pct": 0.30}   # Will be 0.03 (below min)
        ]
        config.scaled_tp_fallback_to_single = True  # Enable fallback
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position with small quantity
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,  # Small quantity
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.1,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Price reaches TP1
        price_at_tp1 = 50000.0 * 1.03
        action = manager.check_take_profit_levels(position, price_at_tp1)
        
        # Should return None (fallback to single TP)
        assert action is None, \
            "Should fallback to single TP when all partials are below minimum"
    
    def test_no_fallback_when_disabled(self):
        """When fallback is disabled, should skip levels even if all are below minimum."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_min_order_size = 0.5  # Set very high minimum
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        config.scaled_tp_fallback_to_single = False  # Disable fallback
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position with small quantity
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
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
        
        # Price reaches TP1
        price_at_tp1 = 50000.0 * 1.03
        action = manager.check_take_profit_levels(position, price_at_tp1)
        
        # Should return None (skipped, not fallback)
        assert action is None
    
    def test_partial_close_meets_minimum(self):
        """Partial closes that meet minimum should proceed normally."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_min_order_size = 0.01  # Low minimum
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # Will be 0.4 (above min)
            {"profit_pct": 0.05, "close_pct": 0.30},  # Will be 0.3 (above min)
            {"profit_pct": 0.08, "close_pct": 0.30}   # Will be 0.3 (above min)
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=1.0,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Price reaches TP1
        price_at_tp1 = 50000.0 * 1.03
        action = manager.check_take_profit_levels(position, price_at_tp1)
        
        # Should proceed normally
        assert action is not None
        assert action.quantity == 0.4, f"Expected 0.4, got {action.quantity}"
        assert action.quantity >= config.scaled_tp_min_order_size
    
    def test_mixed_scenario_some_below_some_above(self):
        """Test scenario where some TP levels are below minimum and some are above."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_min_order_size = 0.035  # Set medium minimum
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.30},  # Will be 0.03 (below min)
            {"profit_pct": 0.05, "close_pct": 0.40},  # Will be 0.04 (above min)
            {"profit_pct": 0.08, "close_pct": 0.30}   # Will be 0.03 (below min)
        ]
        config.scaled_tp_fallback_to_single = False
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a LONG position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
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
        
        # Price reaches TP1 (0.03, below minimum) - should be skipped
        price_at_tp1 = 50000.0 * 1.03
        action1 = manager.check_take_profit_levels(position, price_at_tp1)
        assert action1 is None, "TP1 should be skipped (below minimum)"
        
        # Price reaches TP2 (0.04, above minimum) - should proceed
        price_at_tp2 = 50000.0 * 1.05
        action2 = manager.check_take_profit_levels(position, price_at_tp2)
        assert action2 is not None, "TP2 should proceed (above minimum)"
        assert action2.tp_level == 2, "Should trigger TP2 after skipping TP1"
        assert action2.quantity >= config.scaled_tp_min_order_size


# Tests for Task 8: TP status tracking and reset
class TestTPStatusTracking:
    """Unit tests for TP status tracking and reset functionality."""
    
    def test_get_tp_status_returns_empty_for_untracked_symbol(self):
        """get_tp_status should return empty status for symbols not being tracked."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Get status for a symbol that hasn't been tracked yet
        status = manager.get_tp_status("ETHUSDT")
        
        assert status.symbol == "ETHUSDT"
        assert status.levels_hit == []
        assert status.remaining_size_pct == 1.0
        assert status.current_stop_loss == 0.0
        assert status.next_tp_level == 1
        assert status.next_tp_price is None
    
    def test_tracking_initialized_on_first_check(self):
        """Tracking should be initialized when check_take_profit_levels is first called."""
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
            quantity=1.0,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Check TP levels (this should initialize tracking)
        price_below_tp1 = 50000.0 * 1.01  # Below TP1
        manager.check_take_profit_levels(position, price_below_tp1)
        
        # Now get status - should be initialized
        status = manager.get_tp_status("BTCUSDT")
        
        assert status.symbol == "BTCUSDT"
        assert status.levels_hit == []
        assert status.remaining_size_pct == 1.0
        assert status.current_stop_loss == 49000.0
        assert status.next_tp_level == 1
        assert status.next_tp_price is not None
        assert abs(status.next_tp_price - 51500.0) < 0.01  # TP1 at +3%
    
    def test_tracking_updated_after_tp_hit(self):
        """Tracking should be updated when update_stop_loss_ladder is called."""
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
            quantity=1.0,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Initialize tracking
        price_at_tp1 = 50000.0 * 1.03
        action = manager.check_take_profit_levels(position, price_at_tp1)
        assert action is not None
        
        # Simulate partial close
        position.quantity -= action.quantity
        position.tp_levels_hit.append(1)
        
        # Update stop loss (this should update tracking)
        new_sl = manager.update_stop_loss_ladder(position, 1)
        position.stop_loss = new_sl
        
        # Get status - should reflect TP1 hit
        status = manager.get_tp_status("BTCUSDT")
        
        assert status.symbol == "BTCUSDT"
        assert 1 in status.levels_hit
        assert abs(status.remaining_size_pct - 0.6) < 0.01  # 60% remaining after 40% close
        assert status.current_stop_loss == 50000.0  # Moved to breakeven
        assert status.next_tp_level == 2
        assert status.next_tp_price is not None
        assert abs(status.next_tp_price - 52500.0) < 0.01  # TP2 at +5%
    
    def test_tracking_shows_all_levels_hit(self):
        """Tracking should show all TP levels that have been hit."""
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
            quantity=1.0,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Hit all three TP levels
        for i in range(3):
            tp_level = i + 1
            profit_pct = config.scaled_tp_levels[i]["profit_pct"]
            close_pct = config.scaled_tp_levels[i]["close_pct"]
            
            price = 50000.0 * (1 + profit_pct)
            action = manager.check_take_profit_levels(position, price)
            assert action is not None
            
            # Simulate partial close
            position.quantity -= action.quantity
            position.tp_levels_hit.append(tp_level)
            
            # Update stop loss
            new_sl = manager.update_stop_loss_ladder(position, tp_level)
            position.stop_loss = new_sl
        
        # Get status - should show all levels hit
        status = manager.get_tp_status("BTCUSDT")
        
        assert status.symbol == "BTCUSDT"
        assert status.levels_hit == [1, 2, 3]
        assert abs(status.remaining_size_pct) < 0.01  # ~0% remaining
        assert status.next_tp_level is None  # All levels hit
        assert status.next_tp_price is None
    
    def test_reset_tracking_clears_symbol(self):
        """reset_tracking should remove tracking for the specified symbol."""
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
            quantity=1.0,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Initialize tracking
        price_at_tp1 = 50000.0 * 1.03
        manager.check_take_profit_levels(position, price_at_tp1)
        
        # Verify tracking exists
        status_before = manager.get_tp_status("BTCUSDT")
        assert status_before.next_tp_level == 1
        
        # Reset tracking
        manager.reset_tracking("BTCUSDT")
        
        # Get status again - should be empty
        status_after = manager.get_tp_status("BTCUSDT")
        assert status_after.symbol == "BTCUSDT"
        assert status_after.levels_hit == []
        assert status_after.remaining_size_pct == 1.0
        assert status_after.current_stop_loss == 0.0
        assert status_after.next_tp_level == 1
        assert status_after.next_tp_price is None
    
    def test_reset_tracking_for_nonexistent_symbol(self):
        """reset_tracking should handle symbols that aren't being tracked."""
        config = Config()
        config.enable_scaled_take_profit = True
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Reset tracking for a symbol that was never tracked
        # Should not raise an error
        manager.reset_tracking("ETHUSDT")
        
        # Verify status is still empty
        status = manager.get_tp_status("ETHUSDT")
        assert status.levels_hit == []
    
    def test_tracking_multiple_symbols_independently(self):
        """Tracking should work independently for multiple symbols."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create two positions for different symbols
        position_btc = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=1.0,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        position_eth = Position(
            symbol="ETHUSDT",
            side="LONG",
            entry_price=3000.0,
            quantity=10.0,
            leverage=3,
            stop_loss=2940.0,
            trailing_stop=2940.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=10.0,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Initialize tracking for both
        manager.check_take_profit_levels(position_btc, 50000.0)
        manager.check_take_profit_levels(position_eth, 3000.0)
        
        # Hit TP1 for BTC only
        price_btc_tp1 = 50000.0 * 1.03
        action_btc = manager.check_take_profit_levels(position_btc, price_btc_tp1)
        position_btc.quantity -= action_btc.quantity
        position_btc.tp_levels_hit.append(1)
        new_sl_btc = manager.update_stop_loss_ladder(position_btc, 1)
        position_btc.stop_loss = new_sl_btc
        
        # Get status for both symbols
        status_btc = manager.get_tp_status("BTCUSDT")
        status_eth = manager.get_tp_status("ETHUSDT")
        
        # BTC should have TP1 hit
        assert 1 in status_btc.levels_hit
        assert status_btc.next_tp_level == 2
        
        # ETH should have no TPs hit
        assert status_eth.levels_hit == []
        assert status_eth.next_tp_level == 1
        
        # Reset BTC tracking
        manager.reset_tracking("BTCUSDT")
        
        # BTC should be reset, ETH should be unchanged
        status_btc_after = manager.get_tp_status("BTCUSDT")
        status_eth_after = manager.get_tp_status("ETHUSDT")
        
        assert status_btc_after.levels_hit == []
        assert status_eth_after.levels_hit == []  # Still unchanged
    
    def test_update_tracking_after_partial_close_method(self):
        """update_tracking_after_partial_close should update tracking correctly."""
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
            quantity=1.0,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Initialize tracking
        manager.check_take_profit_levels(position, 50000.0)
        
        # Simulate TP1 hit and partial close
        position.quantity = 0.6  # 40% closed
        position.tp_levels_hit.append(1)
        new_sl = 50000.0  # Breakeven
        position.stop_loss = new_sl
        
        # Update tracking using the public method
        manager.update_tracking_after_partial_close(position, 1, new_sl)
        
        # Verify tracking was updated
        status = manager.get_tp_status("BTCUSDT")
        assert 1 in status.levels_hit
        assert abs(status.remaining_size_pct - 0.6) < 0.01
        assert status.current_stop_loss == 50000.0
        assert status.next_tp_level == 2
    
    def test_tracking_with_position_already_having_tp_hits(self):
        """Tracking should initialize correctly for positions that already have TP hits."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a position that already has TP1 hit (e.g., after bot restart)
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.6,  # 40% already closed
            leverage=3,
            stop_loss=50000.0,  # Already at breakeven
            trailing_stop=50000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[{"tp_level": 1, "quantity": 0.4}],
            tp_levels_hit=[1]  # TP1 already hit
        )
        
        # Initialize tracking (should recognize TP1 is already hit)
        manager.check_take_profit_levels(position, 50000.0)
        
        # Get status
        status = manager.get_tp_status("BTCUSDT")
        
        assert 1 in status.levels_hit
        assert abs(status.remaining_size_pct - 0.6) < 0.01
        assert status.current_stop_loss == 50000.0
        assert status.next_tp_level == 2  # Next should be TP2
        assert status.next_tp_price is not None
        assert abs(status.next_tp_price - 52500.0) < 0.01  # TP2 at +5%
