"""Unit tests for Scaled Take Profit Manager edge cases.

This module tests edge case scenarios including:
- Price gaps through multiple TP levels
- Position restoration after restart
- Network interruption recovery
- API failure retry logic
- Insufficient balance scenarios

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.config import Config
from src.models import Position, PartialCloseAction, PartialCloseResult
from src.scaled_tp_manager import ScaledTakeProfitManager


class TestPriceGapHandling:
    """Test handling of price gaps through multiple TP levels (Requirement 6.1)."""
    
    def test_price_gap_through_all_tp_levels(self):
        """WHEN a position gaps through multiple TP levels in one candle 
        THEN the system SHALL execute all applicable partial closes at their respective levels.
        
        Requirement 6.1
        """
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
        
        # Price gaps directly to TP3 level (skipping TP1 and TP2)
        price_at_tp3 = 50000.0 * 1.08  # +8%
        
        # Track all TP levels that get triggered
        levels_triggered = []
        
        # First check - should trigger TP1 (even though price is at TP3)
        action1 = manager.check_take_profit_levels(position, price_at_tp3)
        assert action1 is not None, "TP1 should trigger when price gaps to TP3"
        assert action1.tp_level == 1, "First trigger should be TP1"
        levels_triggered.append(action1.tp_level)
        
        # Simulate partial close
        position.quantity -= action1.quantity
        position.tp_levels_hit.append(1)
        
        # Second check - should trigger TP2
        action2 = manager.check_take_profit_levels(position, price_at_tp3)
        assert action2 is not None, "TP2 should trigger after TP1"
        assert action2.tp_level == 2, "Second trigger should be TP2"
        levels_triggered.append(action2.tp_level)
        
        # Simulate partial close
        position.quantity -= action2.quantity
        position.tp_levels_hit.append(2)
        
        # Third check - should trigger TP3
        action3 = manager.check_take_profit_levels(position, price_at_tp3)
        assert action3 is not None, "TP3 should trigger after TP2"
        assert action3.tp_level == 3, "Third trigger should be TP3"
        levels_triggered.append(action3.tp_level)
        
        # Verify all levels were triggered in order
        assert levels_triggered == [1, 2, 3], \
            f"All TP levels should trigger in order, got {levels_triggered}"
    
    def test_price_gap_skips_tp1_hits_tp2(self):
        """Test price gap that skips TP1 and lands at TP2."""
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
        
        # Price gaps to TP2 level (skipping TP1)
        price_at_tp2 = 50000.0 * 1.05  # +5%
        
        # Should still trigger TP1 first
        action = manager.check_take_profit_levels(position, price_at_tp2)
        assert action is not None
        assert action.tp_level == 1, "TP1 must be hit first even if price is at TP2"

    def test_price_gap_for_short_position(self):
        """Test price gap handling for SHORT positions."""
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
            quantity=1.0,
            leverage=3,
            stop_loss=51000.0,
            trailing_stop=51000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Price gaps down to TP3 level (skipping TP1 and TP2)
        price_at_tp3 = 50000.0 * 0.92  # -8%
        
        # Should trigger TP1 first
        action1 = manager.check_take_profit_levels(position, price_at_tp3)
        assert action1 is not None
        assert action1.tp_level == 1, "TP1 should trigger first for SHORT positions"
        
        # Simulate partial close
        position.quantity -= action1.quantity
        position.tp_levels_hit.append(1)
        
        # Should trigger TP2 next
        action2 = manager.check_take_profit_levels(position, price_at_tp3)
        assert action2 is not None
        assert action2.tp_level == 2, "TP2 should trigger after TP1 for SHORT positions"


class TestPositionRestoration:
    """Test position restoration after bot restart (Requirement 6.3)."""
    
    def test_restore_position_with_tp1_already_hit(self):
        """WHEN the system restarts with open positions that have hit some TP levels 
        THEN it SHALL restore the correct remaining position size and stop loss level.
        
        Requirement 6.3
        """
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: +3%
            {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: +5%
            {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: +8%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a position that already has TP1 hit (simulating restart)
        original_qty = 1.0
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.6,  # 40% already closed at TP1
            leverage=3,
            stop_loss=50000.0,  # Moved to breakeven after TP1
            trailing_stop=50000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=original_qty,
            partial_exits=[
                {
                    "tp_level": 1,
                    "quantity": 0.4,
                    "price": 51500.0,
                    "profit": 600.0
                }
            ],
            tp_levels_hit=[1]  # TP1 already hit
        )
        
        # Price reaches TP2
        price_at_tp2 = 50000.0 * 1.05  # +5%
        
        # Should trigger TP2 (not TP1 again)
        action = manager.check_take_profit_levels(position, price_at_tp2)
        assert action is not None, "TP2 should trigger after restoration"
        assert action.tp_level == 2, "Should trigger TP2, not TP1"
        
        # Verify quantity calculation is based on original quantity
        expected_qty = original_qty * 0.30  # 30% of original
        assert abs(action.quantity - expected_qty) < 0.0001, \
            f"Quantity should be {expected_qty}, got {action.quantity}"

    def test_restore_position_with_multiple_tps_hit(self):
        """Test restoration when multiple TP levels have been hit."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: +3%
            {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: +5%
            {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: +8%
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a position with TP1 and TP2 already hit
        original_qty = 1.0
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.3,  # 70% already closed (40% + 30%)
            leverage=3,
            stop_loss=51500.0,  # Moved to TP1 level after TP2
            trailing_stop=51500.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=original_qty,
            partial_exits=[
                {"tp_level": 1, "quantity": 0.4, "price": 51500.0},
                {"tp_level": 2, "quantity": 0.3, "price": 52500.0}
            ],
            tp_levels_hit=[1, 2]  # TP1 and TP2 already hit
        )
        
        # Price reaches TP3
        price_at_tp3 = 50000.0 * 1.08  # +8%
        
        # Should trigger TP3 (not TP1 or TP2)
        action = manager.check_take_profit_levels(position, price_at_tp3)
        assert action is not None, "TP3 should trigger after restoration"
        assert action.tp_level == 3, "Should trigger TP3"
        
        # Verify quantity calculation
        expected_qty = original_qty * 0.30  # 30% of original
        assert abs(action.quantity - expected_qty) < 0.0001, \
            f"Quantity should be {expected_qty}, got {action.quantity}"
    
    def test_restore_tracking_state(self):
        """Test that TP tracking state is correctly initialized from position."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a position with TP1 already hit
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.6,
            leverage=3,
            stop_loss=50000.0,
            trailing_stop=50000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[{"tp_level": 1, "quantity": 0.4}],
            tp_levels_hit=[1]
        )
        
        # Trigger tracking initialization
        price = 50000.0 * 1.04
        manager.check_take_profit_levels(position, price)
        
        # Get TP status
        status = manager.get_tp_status("BTCUSDT")
        
        # Verify tracking state
        assert status.levels_hit == [1], "Should track TP1 as hit"
        assert status.next_tp_level == 2, "Next TP should be 2"
        assert abs(status.remaining_size_pct - 0.6) < 0.0001, "Should track 60% remaining"


class TestAPIFailureRetry:
    """Test API failure and retry logic (Requirement 6.2)."""
    
    def test_partial_close_retries_on_api_failure(self):
        """WHEN a partial close order fails THEN the system SHALL retry once 
        and log the failure if it persists.
        
        Requirement 6.2
        """
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40}
        ]
        
        # Create mock client that fails first time, succeeds second time
        mock_client = Mock()
        mock_client.futures_create_order = Mock(
            side_effect=[
                Exception("API Error: Internal server error"),  # First attempt fails
                {  # Second attempt succeeds
                    "orderId": 12345,
                    "status": "FILLED",
                    "executedQty": "0.4",
                    "avgPrice": "51500.0"
                }
            ]
        )
        mock_client.futures_get_order = Mock(return_value={
            "orderId": 12345,
            "status": "FILLED",
            "executedQty": "0.4",
            "avgPrice": "51500.0"
        })
        
        manager = ScaledTakeProfitManager(config, client=mock_client)
        
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
        
        action = PartialCloseAction(
            tp_level=1,
            profit_pct=0.03,
            close_pct=0.40,
            target_price=51500.0,
            quantity=0.4,
            new_stop_loss=50000.0
        )
        
        # Execute partial close
        result = manager.execute_partial_close(position, action)
        
        # Should succeed after retry
        assert result.success, "Should succeed after retry"
        assert result.filled_quantity == 0.4
        
        # Verify it was called twice (first attempt + retry)
        assert mock_client.futures_create_order.call_count == 2

    def test_partial_close_fails_after_all_retries(self):
        """Test that partial close fails gracefully after all retry attempts."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40}
        ]
        
        # Create mock client that always fails
        mock_client = Mock()
        mock_client.futures_create_order = Mock(
            side_effect=Exception("API Error: Internal server error")
        )
        
        manager = ScaledTakeProfitManager(config, client=mock_client)
        
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
        
        action = PartialCloseAction(
            tp_level=1,
            profit_pct=0.03,
            close_pct=0.40,
            target_price=51500.0,
            quantity=0.4,
            new_stop_loss=50000.0
        )
        
        # Execute partial close
        result = manager.execute_partial_close(position, action)
        
        # Should fail after all retries
        assert not result.success, "Should fail after all retries"
        assert result.error_message is not None
        assert "Failed after 2 attempts" in result.error_message
        
        # Verify it was called twice (initial + 1 retry)
        assert mock_client.futures_create_order.call_count == 2
    
    def test_order_verification_failure_triggers_retry(self):
        """Test that order verification failure triggers retry."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40}
        ]
        
        # Create mock client where order succeeds but verification fails first time
        mock_client = Mock()
        mock_client.futures_create_order = Mock(
            side_effect=[
                {"orderId": None},  # First attempt - missing order ID
                {  # Second attempt succeeds
                    "orderId": 12345,
                    "status": "FILLED",
                    "executedQty": "0.4",
                    "avgPrice": "51500.0"
                }
            ]
        )
        mock_client.futures_get_order = Mock(return_value={
            "orderId": 12345,
            "status": "FILLED",
            "executedQty": "0.4",
            "avgPrice": "51500.0"
        })
        
        manager = ScaledTakeProfitManager(config, client=mock_client)
        
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
        
        action = PartialCloseAction(
            tp_level=1,
            profit_pct=0.03,
            close_pct=0.40,
            target_price=51500.0,
            quantity=0.4,
            new_stop_loss=50000.0
        )
        
        # Execute partial close
        result = manager.execute_partial_close(position, action)
        
        # Should succeed after retry
        assert result.success, "Should succeed after retry"
        assert mock_client.futures_create_order.call_count == 2


class TestNetworkInterruption:
    """Test network interruption handling (Requirement 6.5)."""
    
    def test_network_timeout_triggers_retry(self):
        """WHEN network issues prevent a partial close THEN the system SHALL 
        maintain position integrity and not lose track of the remaining size.
        
        Requirement 6.5
        """
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40}
        ]
        
        # Create mock client that times out first time, succeeds second time
        mock_client = Mock()
        mock_client.futures_create_order = Mock(
            side_effect=[
                Exception("Connection timeout"),  # Network error
                {  # Retry succeeds
                    "orderId": 12345,
                    "status": "FILLED",
                    "executedQty": "0.4",
                    "avgPrice": "51500.0"
                }
            ]
        )
        mock_client.futures_get_order = Mock(return_value={
            "orderId": 12345,
            "status": "FILLED",
            "executedQty": "0.4",
            "avgPrice": "51500.0"
        })
        
        manager = ScaledTakeProfitManager(config, client=mock_client)
        
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
        
        action = PartialCloseAction(
            tp_level=1,
            profit_pct=0.03,
            close_pct=0.40,
            target_price=51500.0,
            quantity=0.4,
            new_stop_loss=50000.0
        )
        
        # Execute partial close
        result = manager.execute_partial_close(position, action)
        
        # Should succeed after retry
        assert result.success, "Should recover from network error"
        assert result.filled_quantity == 0.4
        
        # Position integrity maintained
        assert position.original_quantity == 1.0, "Original quantity should not change"


class TestInsufficientBalance:
    """Test insufficient balance scenarios (Requirement 6.4)."""
    
    def test_position_reverses_before_any_tp_hit(self):
        """WHEN a position reverses before hitting any TP level 
        THEN the system SHALL exit at the original stop loss.
        
        Requirement 6.4
        """
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
            stop_loss=49000.0,  # Original stop loss
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Price moves up but doesn't reach TP1
        price_below_tp1 = 50000.0 * 1.02  # +2% (TP1 is at +3%)
        
        # No TP should trigger
        action = manager.check_take_profit_levels(position, price_below_tp1)
        assert action is None, "No TP should trigger below TP1"
        
        # Stop loss should remain at original level
        assert position.stop_loss == 49000.0, "Stop loss should remain at original level"
        
        # If price drops to stop loss, position should exit with full quantity
        assert position.quantity == 1.0, "Full quantity should remain"

    def test_insufficient_quantity_for_partial_close(self):
        """Test handling when remaining quantity is insufficient for partial close."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        config.scaled_tp_min_order_size = 0.001
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a position with very small quantity
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.002,  # Very small remaining
            leverage=3,
            stop_loss=50000.0,
            trailing_stop=50000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.005,  # Original was also small
            partial_exits=[{"tp_level": 1, "quantity": 0.002}],
            tp_levels_hit=[1]
        )
        
        # Price reaches TP2
        price_at_tp2 = 50000.0 * 1.05
        
        # Check TP2 - should trigger but might adjust quantity
        action = manager.check_take_profit_levels(position, price_at_tp2)
        
        if action is not None:
            # If action is returned, quantity should be valid
            assert action.quantity >= config.scaled_tp_min_order_size or \
                   action.quantity == position.quantity, \
                   "Quantity should meet minimum or close entire remaining"
    
    def test_partial_close_below_minimum_order_size(self):
        """Test that partial closes below minimum order size are skipped."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        config.scaled_tp_min_order_size = 0.1  # High minimum
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a position where partials would be below minimum
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.05,  # Small position
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=0.05,
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Price reaches TP1
        price_at_tp1 = 50000.0 * 1.03
        
        # TP1 would close 0.02 (40% of 0.05), which is below minimum 0.1
        # Should either skip or fallback to single TP
        action = manager.check_take_profit_levels(position, price_at_tp1)
        
        # If fallback is enabled, should return None (use single TP instead)
        # If fallback is disabled, should skip and return None
        # Either way, we shouldn't get an action with quantity below minimum
        if action is not None:
            assert action.quantity >= config.scaled_tp_min_order_size, \
                "Should not return action with quantity below minimum"


class TestEdgeCaseIntegration:
    """Integration tests for multiple edge cases combined."""
    
    def test_price_gap_with_position_restoration(self):
        """Test price gap handling on a restored position."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a restored position with TP1 already hit
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.6,
            leverage=3,
            stop_loss=50000.0,
            trailing_stop=50000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[{"tp_level": 1, "quantity": 0.4}],
            tp_levels_hit=[1]
        )
        
        # Price gaps to TP3 (skipping TP2)
        price_at_tp3 = 50000.0 * 1.08
        
        # Should trigger TP2 first
        action2 = manager.check_take_profit_levels(position, price_at_tp3)
        assert action2 is not None
        assert action2.tp_level == 2, "Should trigger TP2 after restoration"
        
        # Simulate partial close
        position.quantity -= action2.quantity
        position.tp_levels_hit.append(2)
        
        # Should then trigger TP3
        action3 = manager.check_take_profit_levels(position, price_at_tp3)
        assert action3 is not None
        assert action3.tp_level == 3, "Should trigger TP3 after TP2"
    
    def test_stop_loss_protection_after_partial_closes(self):
        """Test that stop loss is properly protected after partial closes."""
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
        
        # Hit TP1
        price_at_tp1 = 50000.0 * 1.03
        action1 = manager.check_take_profit_levels(position, price_at_tp1)
        new_sl_1 = manager.update_stop_loss_ladder(position, 1)
        
        # Stop loss should move to breakeven
        assert new_sl_1 == 50000.0, "Stop loss should move to breakeven after TP1"
        
        # Update position
        position.stop_loss = new_sl_1
        position.quantity -= action1.quantity
        position.tp_levels_hit.append(1)
        
        # Hit TP2
        price_at_tp2 = 50000.0 * 1.05
        action2 = manager.check_take_profit_levels(position, price_at_tp2)
        new_sl_2 = manager.update_stop_loss_ladder(position, 2)
        
        # Stop loss should move to TP1 level
        expected_tp1_price = 50000.0 * 1.03
        assert new_sl_2 == expected_tp1_price, \
            f"Stop loss should move to TP1 level ({expected_tp1_price}), got {new_sl_2}"
        
        # Stop loss should only move up for LONG
        assert new_sl_2 >= new_sl_1, "Stop loss should only move up for LONG positions"



class TestPriceGapHelperMethod:
    """Test the helper method for getting all applicable TP levels at once."""
    
    def test_get_all_applicable_tp_levels_for_price_gap(self):
        """Test helper method that returns all applicable TP levels at once."""
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
        
        # Price gaps to TP3 level
        price_at_tp3 = 50000.0 * 1.08
        
        # Get all applicable TP levels
        actions = manager.get_all_applicable_tp_levels(position, price_at_tp3)
        
        # Should return all 3 TP levels
        assert len(actions) == 3, f"Should return 3 TP levels, got {len(actions)}"
        
        # Verify they are in order
        assert actions[0].tp_level == 1
        assert actions[1].tp_level == 2
        assert actions[2].tp_level == 3
        
        # Verify quantities
        assert abs(actions[0].quantity - 0.4) < 0.0001  # 40% of 1.0
        assert abs(actions[1].quantity - 0.3) < 0.0001  # 30% of 1.0
        assert abs(actions[2].quantity - 0.3) < 0.0001  # 30% of 1.0
    
    def test_get_all_applicable_tp_levels_partial_gap(self):
        """Test helper method when price only reaches some TP levels."""
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
        
        # Price only reaches TP2 level
        price_at_tp2 = 50000.0 * 1.05
        
        # Get all applicable TP levels
        actions = manager.get_all_applicable_tp_levels(position, price_at_tp2)
        
        # Should return only 2 TP levels (TP1 and TP2)
        assert len(actions) == 2, f"Should return 2 TP levels, got {len(actions)}"
        assert actions[0].tp_level == 1
        assert actions[1].tp_level == 2
    
    def test_get_all_applicable_tp_levels_with_some_already_hit(self):
        """Test helper method when some TP levels are already hit."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        manager = ScaledTakeProfitManager(config, client=None)
        
        # Create a position with TP1 already hit
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.6,  # 40% already closed
            leverage=3,
            stop_loss=50000.0,
            trailing_stop=50000.0,
            entry_time=1708450000000,
            unrealized_pnl=0.0,
            original_quantity=1.0,
            partial_exits=[{"tp_level": 1, "quantity": 0.4}],
            tp_levels_hit=[1]
        )
        
        # Price gaps to TP3 level
        price_at_tp3 = 50000.0 * 1.08
        
        # Get all applicable TP levels
        actions = manager.get_all_applicable_tp_levels(position, price_at_tp3)
        
        # Should return only TP2 and TP3 (TP1 already hit)
        assert len(actions) == 2, f"Should return 2 TP levels, got {len(actions)}"
        assert actions[0].tp_level == 2
        assert actions[1].tp_level == 3
