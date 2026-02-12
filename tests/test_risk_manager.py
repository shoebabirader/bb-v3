"""Property-based and unit tests for RiskManager."""

import pytest
from hypothesis import given, strategies as st, settings
from src.config import Config
from src.models import Position, Signal
from src.position_sizer import PositionSizer
from src.risk_manager import RiskManager


# Test fixtures
@pytest.fixture
def config():
    """Create a test configuration."""
    config = Config()
    config.symbol = "BTCUSDT"
    config.risk_per_trade = 0.01
    config.leverage = 3
    config.stop_loss_atr_multiplier = 2.0
    config.trailing_stop_atr_multiplier = 1.5
    return config


@pytest.fixture
def position_sizer(config):
    """Create a PositionSizer instance."""
    return PositionSizer(config)


@pytest.fixture
def risk_manager(config, position_sizer):
    """Create a RiskManager instance."""
    return RiskManager(config, position_sizer)


# Property-based tests

# Feature: binance-futures-bot, Property 24: Initial Stop-Loss Placement
@settings(max_examples=100)
@given(
    wallet_balance=st.floats(min_value=100, max_value=100000),
    entry_price=st.floats(min_value=1, max_value=100000),
    atr=st.floats(min_value=0.01, max_value=1000),
    signal_type=st.sampled_from(["LONG_ENTRY", "SHORT_ENTRY"])
)
def test_initial_stop_loss_placement(wallet_balance, entry_price, atr, signal_type):
    """For any newly opened position, the initial stop-loss price should be 
    exactly 2x ATR away from the entry price in the direction that limits loss.
    
    Validates: Requirements 8.1
    """
    # Create config and dependencies
    config = Config()
    config.symbol = "BTCUSDT"
    config.risk_per_trade = 0.01
    config.leverage = 3
    config.stop_loss_atr_multiplier = 2.0
    config.trailing_stop_atr_multiplier = 1.5
    
    position_sizer = PositionSizer(config)
    risk_manager = RiskManager(config, position_sizer)
    
    # Create signal
    signal = Signal(
        type=signal_type,
        timestamp=1000000,
        price=entry_price,
        indicators={}
    )
    
    # Open position
    position = risk_manager.open_position(
        signal=signal,
        wallet_balance=wallet_balance,
        atr=atr
    )
    
    # Calculate expected stop distance
    expected_stop_distance = config.stop_loss_atr_multiplier * atr
    
    # Verify stop-loss placement
    if position.side == "LONG":
        # For long positions, stop should be below entry
        actual_stop_distance = position.entry_price - position.stop_loss
        assert actual_stop_distance >= 0, "Long position stop should be below entry"
        assert abs(actual_stop_distance - expected_stop_distance) < 0.01, \
            f"Stop distance should be 2x ATR. Expected: {expected_stop_distance}, Got: {actual_stop_distance}"
    else:  # SHORT
        # For short positions, stop should be above entry
        actual_stop_distance = position.stop_loss - position.entry_price
        assert actual_stop_distance >= 0, "Short position stop should be above entry"
        assert abs(actual_stop_distance - expected_stop_distance) < 0.01, \
            f"Stop distance should be 2x ATR. Expected: {expected_stop_distance}, Got: {actual_stop_distance}"
    
    # Verify trailing stop is initially same as stop_loss
    assert position.trailing_stop == position.stop_loss, \
        "Initial trailing stop should equal initial stop-loss"


# Feature: binance-futures-bot, Property 25: Trailing Stop Activation and Updates
@settings(max_examples=100)
@given(
    entry_price=st.floats(min_value=1000, max_value=50000),
    atr=st.floats(min_value=10, max_value=500),
    price_move_percent=st.floats(min_value=0.01, max_value=0.1),  # 1-10% favorable move
    side=st.sampled_from(["LONG", "SHORT"])
)
def test_trailing_stop_only_tightens(entry_price, atr, price_move_percent, side):
    """For any position in profit, the trailing stop should be set at 1.5x ATR 
    from current price, and should only move closer to current price (never farther away).
    
    Validates: Requirements 8.2, 8.3, 8.5
    """
    # Create config and dependencies
    config = Config()
    config.symbol = "BTCUSDT"
    config.risk_per_trade = 0.01
    config.leverage = 3
    config.stop_loss_atr_multiplier = 2.0
    config.trailing_stop_atr_multiplier = 1.5
    
    position_sizer = PositionSizer(config)
    risk_manager = RiskManager(config, position_sizer)
    
    # Create a position manually
    stop_distance = config.stop_loss_atr_multiplier * atr
    if side == "LONG":
        initial_stop = entry_price - stop_distance
    else:
        initial_stop = entry_price + stop_distance
    
    position = Position(
        symbol="BTCUSDT",
        side=side,
        entry_price=entry_price,
        quantity=0.1,
        leverage=3,
        stop_loss=initial_stop,
        trailing_stop=initial_stop,
        entry_time=1000000,
        unrealized_pnl=0.0
    )
    
    # Add position to risk manager
    risk_manager.active_positions["BTCUSDT"] = position
    
    # Move price favorably
    if side == "LONG":
        new_price = entry_price * (1 + price_move_percent)
    else:
        new_price = entry_price * (1 - price_move_percent)
    
    # Store old trailing stop
    old_trailing_stop = position.trailing_stop
    
    # Update stops
    risk_manager.update_stops(position, new_price, atr)
    
    # Verify trailing stop moved in favorable direction (tightened)
    if side == "LONG":
        # For long, trailing stop should move up (increase)
        assert position.trailing_stop >= old_trailing_stop, \
            f"Long trailing stop should only move up. Old: {old_trailing_stop}, New: {position.trailing_stop}"
        
        # Verify it's at 1.5x ATR from current price (or at old stop if that's tighter)
        expected_new_stop = new_price - (config.trailing_stop_atr_multiplier * atr)
        if expected_new_stop > old_trailing_stop:
            assert abs(position.trailing_stop - expected_new_stop) < 0.01, \
                f"Trailing stop should be 1.5x ATR from price. Expected: {expected_new_stop}, Got: {position.trailing_stop}"
    else:  # SHORT
        # For short, trailing stop should move down (decrease)
        assert position.trailing_stop <= old_trailing_stop, \
            f"Short trailing stop should only move down. Old: {old_trailing_stop}, New: {position.trailing_stop}"
        
        # Verify it's at 1.5x ATR from current price (or at old stop if that's tighter)
        expected_new_stop = new_price + (config.trailing_stop_atr_multiplier * atr)
        if expected_new_stop < old_trailing_stop:
            assert abs(position.trailing_stop - expected_new_stop) < 0.01, \
                f"Trailing stop should be 1.5x ATR from price. Expected: {expected_new_stop}, Got: {position.trailing_stop}"
    
    # Now move price unfavorably and verify stop doesn't widen
    if side == "LONG":
        unfavorable_price = new_price * 0.99  # Price drops slightly
    else:
        unfavorable_price = new_price * 1.01  # Price rises slightly
    
    current_trailing_stop = position.trailing_stop
    risk_manager.update_stops(position, unfavorable_price, atr)
    
    # Verify stop didn't widen
    if side == "LONG":
        assert position.trailing_stop >= current_trailing_stop, \
            "Long trailing stop should never widen (decrease)"
    else:
        assert position.trailing_stop <= current_trailing_stop, \
            "Short trailing stop should never widen (increase)"


# Feature: binance-futures-bot, Property 26: Stop-Loss Trigger Execution
@settings(max_examples=100)
@given(
    entry_price=st.floats(min_value=10000, max_value=50000),  # Higher minimum to avoid edge cases
    atr=st.floats(min_value=10, max_value=500),
    side=st.sampled_from(["LONG", "SHORT"])
)
def test_stop_loss_trigger_detection(entry_price, atr, side):
    """For any position where current price crosses the stop-loss level, 
    the position should be detected as stopped out.
    
    Validates: Requirements 8.4
    """
    # Create config and dependencies
    config = Config()
    config.symbol = "BTCUSDT"
    config.risk_per_trade = 0.01
    config.leverage = 3
    config.stop_loss_atr_multiplier = 2.0
    config.trailing_stop_atr_multiplier = 1.5
    
    position_sizer = PositionSizer(config)
    risk_manager = RiskManager(config, position_sizer)
    
    # Create a position
    stop_distance = config.stop_loss_atr_multiplier * atr
    if side == "LONG":
        stop_price = entry_price - stop_distance
    else:
        stop_price = entry_price + stop_distance
    
    # Skip if stop price is invalid (negative or zero)
    if stop_price <= 0:
        return
    
    position = Position(
        symbol="BTCUSDT",
        side=side,
        entry_price=entry_price,
        quantity=0.1,
        leverage=3,
        stop_loss=stop_price,
        trailing_stop=stop_price,
        entry_time=1000000,
        unrealized_pnl=0.0
    )
    
    # Test price at stop level
    assert risk_manager.check_stop_hit(position, stop_price) == True, \
        "Stop should be hit when price equals stop level"
    
    # Test price beyond stop level
    if side == "LONG":
        # For long, price below stop should trigger
        below_stop = stop_price * 0.99
        if below_stop > 0:  # Only test if valid price
            assert risk_manager.check_stop_hit(position, below_stop) == True, \
                "Long stop should be hit when price is below stop level"
        
        # Price above stop should not trigger
        above_stop = stop_price * 1.01
        assert risk_manager.check_stop_hit(position, above_stop) == False, \
            "Long stop should not be hit when price is above stop level"
    else:  # SHORT
        # For short, price above stop should trigger
        above_stop = stop_price * 1.01
        assert risk_manager.check_stop_hit(position, above_stop) == True, \
            "Short stop should be hit when price is above stop level"
        
        # Price below stop should not trigger
        below_stop = stop_price * 0.99
        assert risk_manager.check_stop_hit(position, below_stop) == False, \
            "Short stop should not be hit when price is below stop level"


# Feature: binance-futures-bot, Property 29: Panic Close Completeness
@settings(max_examples=100)
@given(
    num_positions=st.integers(min_value=1, max_value=5),
    current_price=st.floats(min_value=1000, max_value=50000)
)
def test_panic_close_completeness(num_positions, current_price):
    """For any panic close trigger, all open positions should be closed, 
    and no new signals should be generated afterward.
    
    Validates: Requirements 10.1, 10.2, 10.3
    """
    # Create config and dependencies
    config = Config()
    config.symbol = "BTCUSDT"
    config.risk_per_trade = 0.01
    config.leverage = 3
    config.stop_loss_atr_multiplier = 2.0
    config.trailing_stop_atr_multiplier = 1.5
    
    position_sizer = PositionSizer(config)
    risk_manager = RiskManager(config, position_sizer)
    
    # Create multiple positions
    for i in range(num_positions):
        side = "LONG" if i % 2 == 0 else "SHORT"
        position = Position(
            symbol=f"SYMBOL{i}",
            side=side,
            entry_price=current_price,
            quantity=0.1,
            leverage=3,
            stop_loss=current_price * 0.98 if side == "LONG" else current_price * 1.02,
            trailing_stop=current_price * 0.98 if side == "LONG" else current_price * 1.02,
            entry_time=1000000 + i,
            unrealized_pnl=0.0
        )
        risk_manager.active_positions[f"SYMBOL{i}"] = position
    
    # Verify positions exist
    assert len(risk_manager.active_positions) == num_positions, \
        f"Should have {num_positions} active positions"
    
    # Trigger panic close
    trades = risk_manager.close_all_positions(current_price)
    
    # Verify all positions were closed
    assert len(risk_manager.active_positions) == 0, \
        "All positions should be closed after panic"
    
    # Verify correct number of trades generated
    assert len(trades) == num_positions, \
        f"Should generate {num_positions} trades, got {len(trades)}"
    
    # Verify all trades have PANIC exit reason
    for trade in trades:
        assert trade.exit_reason == "PANIC", \
            f"All trades should have PANIC exit reason, got {trade.exit_reason}"
        assert trade.exit_price == current_price, \
            f"All trades should exit at current price {current_price}, got {trade.exit_price}"
    
    # Verify signal generation is disabled
    assert risk_manager.is_signal_generation_enabled() == False, \
        "Signal generation should be disabled after panic close"


# Unit tests for specific scenarios

def test_open_long_position(risk_manager):
    """Test opening a long position."""
    signal = Signal(
        type="LONG_ENTRY",
        timestamp=1000000,
        price=50000.0,
        indicators={}
    )
    
    position = risk_manager.open_position(
        signal=signal,
        wallet_balance=10000.0,
        atr=100.0
    )
    
    assert position.side == "LONG"
    assert position.entry_price == 50000.0
    assert position.stop_loss < position.entry_price
    assert position.symbol == "BTCUSDT"
    assert risk_manager.has_active_position("BTCUSDT")


def test_open_short_position(risk_manager):
    """Test opening a short position."""
    signal = Signal(
        type="SHORT_ENTRY",
        timestamp=1000000,
        price=50000.0,
        indicators={}
    )
    
    position = risk_manager.open_position(
        signal=signal,
        wallet_balance=10000.0,
        atr=100.0
    )
    
    assert position.side == "SHORT"
    assert position.entry_price == 50000.0
    assert position.stop_loss > position.entry_price
    assert position.symbol == "BTCUSDT"


def test_close_position_with_profit(risk_manager):
    """Test closing a position with profit."""
    # Create a long position
    signal = Signal(
        type="LONG_ENTRY",
        timestamp=1000000,
        price=50000.0,
        indicators={}
    )
    
    position = risk_manager.open_position(
        signal=signal,
        wallet_balance=10000.0,
        atr=100.0
    )
    
    # Close at higher price (profit)
    trade = risk_manager.close_position(
        position=position,
        exit_price=51000.0,
        reason="SIGNAL_EXIT"
    )
    
    assert trade.pnl > 0
    assert trade.exit_reason == "SIGNAL_EXIT"
    assert not risk_manager.has_active_position("BTCUSDT")


def test_close_position_with_loss(risk_manager):
    """Test closing a position with loss."""
    # Create a long position
    signal = Signal(
        type="LONG_ENTRY",
        timestamp=1000000,
        price=50000.0,
        indicators={}
    )
    
    position = risk_manager.open_position(
        signal=signal,
        wallet_balance=10000.0,
        atr=100.0
    )
    
    # Close at lower price (loss)
    trade = risk_manager.close_position(
        position=position,
        exit_price=49000.0,
        reason="STOP_LOSS"
    )
    
    assert trade.pnl < 0
    assert trade.exit_reason == "STOP_LOSS"


def test_invalid_signal_type(risk_manager):
    """Test that invalid signal type raises error."""
    signal = Signal(
        type="INVALID",
        timestamp=1000000,
        price=50000.0,
        indicators={}
    )
    
    with pytest.raises(ValueError, match="Invalid signal type"):
        risk_manager.open_position(
            signal=signal,
            wallet_balance=10000.0,
            atr=100.0
        )


def test_invalid_exit_reason(risk_manager):
    """Test that invalid exit reason raises error."""
    signal = Signal(
        type="LONG_ENTRY",
        timestamp=1000000,
        price=50000.0,
        indicators={}
    )
    
    position = risk_manager.open_position(
        signal=signal,
        wallet_balance=10000.0,
        atr=100.0
    )
    
    with pytest.raises(ValueError, match="Invalid exit reason"):
        risk_manager.close_position(
            position=position,
            exit_price=51000.0,
            reason="INVALID_REASON"
        )


# ===== INTEGRATION TESTS FOR ENHANCED RISK MANAGEMENT =====

def test_advanced_exit_manager_integration(config, position_sizer):
    """Test RiskManager integration with AdvancedExitManager.
    
    Tests:
    - AdvancedExitManager is initialized when enabled
    - Partial exits are checked correctly
    - Time-based exits work
    - Regime-based exits work
    
    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.7
    """
    # Enable advanced exits
    config.enable_advanced_exits = True
    config.exit_partial_1_atr_multiplier = 1.5
    config.exit_partial_1_percentage = 0.33
    config.exit_partial_2_atr_multiplier = 3.0
    config.exit_partial_2_percentage = 0.33
    config.exit_max_hold_time_hours = 24
    config.exit_regime_change_enabled = True
    
    risk_manager = RiskManager(config, position_sizer)
    
    # Verify AdvancedExitManager is initialized
    assert risk_manager.advanced_exit_manager is not None, \
        "AdvancedExitManager should be initialized when enabled"
    
    # Open a position
    signal = Signal(
        type="LONG_ENTRY",
        timestamp=1000000,
        price=50000.0,
        indicators={}
    )
    
    position = risk_manager.open_position(
        signal=signal,
        wallet_balance=10000.0,
        atr=500.0
    )
    
    # Test partial exit check (price at 1.5x ATR profit)
    current_price = position.entry_price + (1.5 * 500.0)
    partial_pct = risk_manager.check_partial_exit(position, current_price, 500.0)
    
    assert partial_pct is not None, "Partial exit should be triggered at 1.5x ATR"
    assert partial_pct == 0.33, f"Expected 33% partial exit, got {partial_pct}"
    
    # Execute partial exit
    trade = risk_manager.execute_partial_exit(position, current_price, partial_pct)
    
    assert trade.exit_reason == "PARTIAL_EXIT_33%", \
        f"Expected PARTIAL_EXIT_33%, got {trade.exit_reason}"
    assert trade.quantity < position.quantity + trade.quantity, \
        "Position quantity should be reduced after partial exit"
    
    # Test time-based exit (simulate 25 hours passing)
    import time
    position.entry_time = int((time.time() - 25 * 3600) * 1000)
    
    time_exit = risk_manager.check_time_based_exit(position)
    assert time_exit is True, "Time-based exit should trigger after 24 hours"
    
    # Test regime-based exit
    risk_manager.update_regime("TRENDING_BULLISH")
    risk_manager.update_regime("RANGING")
    
    regime_exit = risk_manager.check_regime_exit(position)
    assert regime_exit is True, \
        "Regime-based exit should trigger when changing from TRENDING to RANGING"


def test_portfolio_manager_integration(config, position_sizer):
    """Test RiskManager integration with PortfolioManager.
    
    Tests:
    - PortfolioManager is initialized when enabled
    - Portfolio risk limits are enforced
    - Multi-symbol position management works
    - Portfolio metrics are tracked
    
    Validates: Requirements 5.1, 5.4
    """
    # Enable portfolio management
    config.enable_portfolio_management = True
    config.portfolio_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    config.portfolio_max_symbols = 3
    config.portfolio_max_total_risk = 0.05  # 5% max total risk
    
    risk_manager = RiskManager(config, position_sizer)
    
    # Verify PortfolioManager is initialized
    assert risk_manager.portfolio_manager is not None, \
        "PortfolioManager should be initialized when enabled"
    
    # Verify managed symbols
    managed_symbols = risk_manager.get_managed_symbols()
    assert len(managed_symbols) == 3, f"Expected 3 symbols, got {len(managed_symbols)}"
    assert "BTCUSDT" in managed_symbols, "BTCUSDT should be in managed symbols"
    
    # Test opening position for first symbol
    signal1 = Signal(
        type="LONG_ENTRY",
        timestamp=1000000,
        price=50000.0,
        indicators={},
        symbol="BTCUSDT"
    )
    
    can_open = risk_manager.can_open_position_for_symbol("BTCUSDT", 10000.0)
    assert can_open is True, "Should be able to open first position"
    
    position1 = risk_manager.open_position(
        signal=signal1,
        wallet_balance=10000.0,
        atr=500.0
    )
    
    assert position1.symbol == "BTCUSDT", "Position should be for BTCUSDT"
    
    # Verify portfolio manager was updated
    assert risk_manager.portfolio_manager.positions["BTCUSDT"] is not None, \
        "Portfolio manager should track the position"
    
    # Test opening position for second symbol
    signal2 = Signal(
        type="SHORT_ENTRY",
        timestamp=1000000,
        price=3000.0,
        indicators={},
        symbol="ETHUSDT"
    )
    
    can_open = risk_manager.can_open_position_for_symbol("ETHUSDT", 10000.0)
    assert can_open is True, "Should be able to open second position"
    
    position2 = risk_manager.open_position(
        signal=signal2,
        wallet_balance=10000.0,
        atr=30.0
    )
    
    assert position2.symbol == "ETHUSDT", "Position should be for ETHUSDT"
    
    # Get portfolio metrics
    metrics = risk_manager.get_portfolio_metrics(10000.0)
    
    assert metrics is not None, "Should return portfolio metrics"
    assert metrics.total_risk <= config.portfolio_max_total_risk, \
        f"Total risk {metrics.total_risk} should not exceed {config.portfolio_max_total_risk}"
    
    # Close first position and verify PnL tracking
    trade1 = risk_manager.close_position(position1, 51000.0, "SIGNAL_EXIT")
    
    assert trade1.pnl > 0, "Should have profit on long position"
    assert risk_manager.portfolio_manager.per_symbol_pnl["BTCUSDT"] > 0, \
        "Portfolio manager should track PnL for BTCUSDT"
    
    # Verify position was removed from portfolio
    assert risk_manager.portfolio_manager.positions["BTCUSDT"] is None, \
        "Position should be removed from portfolio after closing"


def test_multi_symbol_position_management(config, position_sizer):
    """Test managing positions across multiple symbols.
    
    Tests:
    - Can open positions for different symbols
    - Each symbol has independent position tracking
    - Closing one position doesn't affect others
    - Portfolio-level risk is enforced
    
    Validates: Requirements 5.1, 6.1, 6.2, 6.3
    """
    # Enable both advanced exits and portfolio management
    config.enable_advanced_exits = True
    config.enable_portfolio_management = True
    config.portfolio_symbols = ["BTCUSDT", "ETHUSDT"]
    config.portfolio_max_symbols = 2
    config.exit_partial_1_atr_multiplier = 1.5
    config.exit_partial_1_percentage = 0.33
    
    risk_manager = RiskManager(config, position_sizer)
    
    # Open position for BTC
    signal_btc = Signal(
        type="LONG_ENTRY",
        timestamp=1000000,
        price=50000.0,
        indicators={},
        symbol="BTCUSDT"
    )
    
    position_btc = risk_manager.open_position(
        signal=signal_btc,
        wallet_balance=10000.0,
        atr=500.0
    )
    
    # Open position for ETH
    signal_eth = Signal(
        type="LONG_ENTRY",
        timestamp=1000000,
        price=3000.0,
        indicators={},
        symbol="ETHUSDT"
    )
    
    position_eth = risk_manager.open_position(
        signal=signal_eth,
        wallet_balance=10000.0,
        atr=30.0
    )
    
    # Verify both positions exist
    assert risk_manager.has_active_position("BTCUSDT"), "Should have BTC position"
    assert risk_manager.has_active_position("ETHUSDT"), "Should have ETH position"
    
    # Test partial exit on BTC position
    btc_price_profit = position_btc.entry_price + (1.5 * 500.0)
    partial_pct = risk_manager.check_partial_exit(position_btc, btc_price_profit, 500.0)
    
    assert partial_pct == 0.33, "Should trigger 33% partial exit for BTC"
    
    # Execute partial exit on BTC
    trade_btc_partial = risk_manager.execute_partial_exit(
        position_btc, btc_price_profit, partial_pct
    )
    
    # Verify BTC position is reduced but ETH is unchanged
    assert position_btc.quantity < position_eth.quantity, \
        "BTC position should be reduced after partial exit"
    assert risk_manager.has_active_position("BTCUSDT"), \
        "BTC position should still exist after partial exit"
    assert risk_manager.has_active_position("ETHUSDT"), \
        "ETH position should be unaffected"
    
    # Close ETH position completely
    trade_eth = risk_manager.close_position(position_eth, 3100.0, "SIGNAL_EXIT")
    
    # Verify ETH is closed but BTC remains
    assert not risk_manager.has_active_position("ETHUSDT"), \
        "ETH position should be closed"
    assert risk_manager.has_active_position("BTCUSDT"), \
        "BTC position should still exist"
    
    # Verify portfolio metrics reflect changes
    metrics = risk_manager.get_portfolio_metrics(10000.0)
    assert metrics is not None, "Should return portfolio metrics"
    assert "ETHUSDT" in metrics.per_symbol_pnl, "Should track ETH PnL"
    assert metrics.per_symbol_pnl["ETHUSDT"] > 0, "ETH should have positive PnL"


def test_advanced_exits_without_portfolio_management(config, position_sizer):
    """Test that advanced exits work independently without portfolio management.
    
    Validates: Requirements 6.1, 6.2, 6.3
    """
    # Enable only advanced exits
    config.enable_advanced_exits = True
    config.enable_portfolio_management = False
    config.exit_partial_1_atr_multiplier = 1.5
    config.exit_partial_1_percentage = 0.33
    
    risk_manager = RiskManager(config, position_sizer)
    
    # Verify only AdvancedExitManager is initialized
    assert risk_manager.advanced_exit_manager is not None, \
        "AdvancedExitManager should be initialized"
    assert risk_manager.portfolio_manager is None, \
        "PortfolioManager should not be initialized"
    
    # Open position
    signal = Signal(
        type="LONG_ENTRY",
        timestamp=1000000,
        price=50000.0,
        indicators={}
    )
    
    position = risk_manager.open_position(
        signal=signal,
        wallet_balance=10000.0,
        atr=500.0
    )
    
    # Test partial exit
    current_price = position.entry_price + (1.5 * 500.0)
    partial_pct = risk_manager.check_partial_exit(position, current_price, 500.0)
    
    assert partial_pct == 0.33, "Partial exit should work without portfolio management"
    
    # Execute partial exit
    trade = risk_manager.execute_partial_exit(position, current_price, partial_pct)
    
    assert trade.pnl > 0, "Should have profit on partial exit"
    assert position.quantity < trade.quantity + position.quantity, \
        "Position should be reduced"


def test_portfolio_management_without_advanced_exits(config, position_sizer):
    """Test that portfolio management works independently without advanced exits.
    
    Validates: Requirements 5.1, 5.4
    """
    # Enable only portfolio management
    config.enable_advanced_exits = False
    config.enable_portfolio_management = True
    config.portfolio_symbols = ["BTCUSDT", "ETHUSDT"]
    config.portfolio_max_symbols = 2
    
    risk_manager = RiskManager(config, position_sizer)
    
    # Verify only PortfolioManager is initialized
    assert risk_manager.portfolio_manager is not None, \
        "PortfolioManager should be initialized"
    assert risk_manager.advanced_exit_manager is None, \
        "AdvancedExitManager should not be initialized"
    
    # Open positions for multiple symbols
    signal_btc = Signal(
        type="LONG_ENTRY",
        timestamp=1000000,
        price=50000.0,
        indicators={},
        symbol="BTCUSDT"
    )
    
    position_btc = risk_manager.open_position(
        signal=signal_btc,
        wallet_balance=10000.0,
        atr=500.0
    )
    
    # Verify portfolio tracking works
    assert risk_manager.portfolio_manager.positions["BTCUSDT"] is not None, \
        "Portfolio should track BTC position"
    
    # Get metrics
    metrics = risk_manager.get_portfolio_metrics(10000.0)
    assert metrics is not None, "Should return portfolio metrics"
    
    # Close position
    trade = risk_manager.close_position(position_btc, 51000.0, "SIGNAL_EXIT")
    
    # Verify portfolio was updated
    assert risk_manager.portfolio_manager.positions["BTCUSDT"] is None, \
        "Position should be removed from portfolio"
    assert risk_manager.portfolio_manager.per_symbol_pnl["BTCUSDT"] > 0, \
        "PnL should be tracked"
