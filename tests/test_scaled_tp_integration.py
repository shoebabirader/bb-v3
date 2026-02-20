"""Integration tests for Scaled Take Profit Manager with TradingBot.

This module tests the integration of ScaledTakeProfitManager into TradingBot,
verifying that partial closes are executed correctly and positions are updated.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.trading_bot import TradingBot
from src.config import Config
from src.models import Position, Signal, PartialCloseAction, PartialCloseResult


@pytest.fixture
def config_with_scaled_tp():
    """Create a config with scaled TP enabled."""
    config = Config(
        api_key="test_key",
        api_secret="test_secret",
        run_mode="PAPER",
        symbol="BTCUSDT",
        enable_scaled_take_profit=True,
        scaled_tp_levels=[
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ],
        scaled_tp_min_order_size=0.001,
        scaled_tp_fallback_to_single=True
    )
    return config


@pytest.fixture
def mock_client():
    """Create a mock Binance client."""
    client = Mock()
    client.futures_create_order = Mock(return_value={
        "orderId": 12345,
        "status": "FILLED",
        "executedQty": "0.04",
        "avgPrice": "51500.0"
    })
    client.futures_get_order = Mock(return_value={
        "orderId": 12345,
        "status": "FILLED",
        "executedQty": "0.04",
        "avgPrice": "51500.0"
    })
    return client


def test_scaled_tp_manager_initialized(config_with_scaled_tp):
    """Test that ScaledTakeProfitManager is initialized in TradingBot."""
    with patch('src.trading_bot.Client') as mock_client_class:
        mock_client_class.return_value = Mock()
        
        bot = TradingBot(config_with_scaled_tp)
        
        # Verify scaled TP manager exists
        assert bot.scaled_tp_manager is not None
        assert bot.scaled_tp_manager.config == config_with_scaled_tp


def test_scaled_tp_check_in_position_monitoring(config_with_scaled_tp, mock_client):
    """Test that scaled TP is checked during position monitoring."""
    with patch('src.trading_bot.Client') as mock_client_class:
        mock_client_class.return_value = mock_client
        
        bot = TradingBot(config_with_scaled_tp)
        
        # Create a mock position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            original_quantity=0.1,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            leverage=10,
            entry_time=datetime.now(),
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Add position to risk manager
        bot.risk_manager.active_positions["BTCUSDT"] = position
        
        # Mock data manager to return candles
        mock_candles_15m = [Mock(close=51500.0) for _ in range(100)]  # Sufficient data
        mock_candles_1h = [Mock(close=51500.0) for _ in range(50)]  # Sufficient data
        bot.data_manager.fetch_historical_data = Mock(side_effect=lambda days, timeframe, symbol, use_cache=True: 
            mock_candles_15m if timeframe == "15m" else mock_candles_1h
        )
        bot.data_manager.get_latest_candles = Mock(side_effect=lambda tf, count, symbol: 
            mock_candles_15m if tf == "15m" else mock_candles_1h
        )
        
        # Mock strategy indicators
        bot.strategy.current_indicators = Mock(
            adx=30.0,
            rvol=2.0,
            atr_15m=100.0
        )
        bot.strategy.update_indicators = Mock()
        bot.strategy.check_long_entry = Mock(return_value=None)
        bot.strategy.check_short_entry = Mock(return_value=None)
        
        # Mock scaled TP manager to return a partial close action
        partial_action = PartialCloseAction(
            tp_level=1,
            profit_pct=0.03,
            close_pct=0.40,
            target_price=51500.0,
            quantity=0.04,
            new_stop_loss=50000.0
        )
        bot.scaled_tp_manager.check_take_profit_levels = Mock(return_value=partial_action)
        
        # Process symbol (simulated execution)
        bot._process_symbol("BTCUSDT", simulate_execution=True)
        
        # Verify check_take_profit_levels was called
        bot.scaled_tp_manager.check_take_profit_levels.assert_called_once()
        
        # Verify position was updated
        assert abs(position.quantity - 0.06) < 0.0001  # 0.1 - 0.04 (with floating point tolerance)
        assert position.stop_loss == 50000.0  # Moved to breakeven
        assert 1 in position.tp_levels_hit
        assert len(position.partial_exits) == 1


def test_partial_close_execution_live_mode(config_with_scaled_tp, mock_client):
    """Test that partial closes are executed in LIVE mode."""
    config_with_scaled_tp.run_mode = "LIVE"
    
    with patch('src.trading_bot.Client') as mock_client_class:
        mock_client_class.return_value = mock_client
        
        bot = TradingBot(config_with_scaled_tp)
        
        # Create a mock position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            original_quantity=0.1,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            leverage=10,
            entry_time=datetime.now(),
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Add position to risk manager
        bot.risk_manager.active_positions["BTCUSDT"] = position
        
        # Mock data manager to return candles
        mock_candles_15m = [Mock(close=51500.0) for _ in range(100)]
        mock_candles_1h = [Mock(close=51500.0) for _ in range(50)]
        bot.data_manager.fetch_historical_data = Mock(side_effect=lambda days, timeframe, symbol, use_cache=True: 
            mock_candles_15m if timeframe == "15m" else mock_candles_1h
        )
        bot.data_manager.get_latest_candles = Mock(side_effect=lambda tf, count, symbol: 
            mock_candles_15m if tf == "15m" else mock_candles_1h
        )
        
        # Mock strategy indicators
        bot.strategy.current_indicators = Mock(
            adx=30.0,
            rvol=2.0,
            atr_15m=100.0
        )
        bot.strategy.update_indicators = Mock()
        bot.strategy.check_long_entry = Mock(return_value=None)
        bot.strategy.check_short_entry = Mock(return_value=None)
        
        # Mock scaled TP manager
        partial_action = PartialCloseAction(
            tp_level=1,
            profit_pct=0.03,
            close_pct=0.40,
            target_price=51500.0,
            quantity=0.04,
            new_stop_loss=50000.0
        )
        bot.scaled_tp_manager.check_take_profit_levels = Mock(return_value=partial_action)
        
        partial_result = PartialCloseResult(
            success=True,
            order_id="12345",
            filled_quantity=0.04,
            fill_price=51500.0,
            realized_profit=60.0,
            error_message=None
        )
        bot.scaled_tp_manager.execute_partial_close = Mock(return_value=partial_result)
        
        # Process symbol (live execution)
        bot._process_symbol("BTCUSDT", simulate_execution=False)
        
        # Verify execute_partial_close was called
        bot.scaled_tp_manager.execute_partial_close.assert_called_once()
        
        # Verify position was updated
        assert abs(position.quantity - 0.06) < 0.0001
        assert position.stop_loss == 50000.0
        assert 1 in position.tp_levels_hit
        
        # Verify balance was updated
        assert bot.wallet_balance > 10000.0  # Initial balance + profit


def test_all_tp_levels_hit_closes_position(config_with_scaled_tp, mock_client):
    """Test that position is closed when all TP levels are hit."""
    with patch('src.trading_bot.Client') as mock_client_class:
        mock_client_class.return_value = mock_client
        
        bot = TradingBot(config_with_scaled_tp)
        
        # Create a position with 2 TP levels already hit
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.03,  # Only 30% remaining
            original_quantity=0.1,
            stop_loss=51500.0,  # Already at TP1
            trailing_stop=51500.0,
            leverage=10,
            entry_time=datetime.now(),
            partial_exits=[
                {"tp_level": 1, "quantity_closed": 0.04, "profit": 60.0},
                {"tp_level": 2, "quantity_closed": 0.03, "profit": 75.0}
            ],
            tp_levels_hit=[1, 2]
        )
        
        # Add position to risk manager
        bot.risk_manager.active_positions["BTCUSDT"] = position
        
        # Mock data manager to return candles at TP3 price
        mock_candles_15m = [Mock(close=54000.0) for _ in range(100)]  # 8% profit
        mock_candles_1h = [Mock(close=54000.0) for _ in range(50)]
        bot.data_manager.fetch_historical_data = Mock(side_effect=lambda days, timeframe, symbol, use_cache=True: 
            mock_candles_15m if timeframe == "15m" else mock_candles_1h
        )
        bot.data_manager.get_latest_candles = Mock(side_effect=lambda tf, count, symbol: 
            mock_candles_15m if tf == "15m" else mock_candles_1h
        )
        
        # Mock strategy indicators
        bot.strategy.current_indicators = Mock(
            adx=30.0,
            rvol=2.0,
            atr_15m=100.0
        )
        bot.strategy.update_indicators = Mock()
        bot.strategy.check_long_entry = Mock(return_value=None)
        bot.strategy.check_short_entry = Mock(return_value=None)
        
        # Mock scaled TP manager to return TP3 action
        partial_action = PartialCloseAction(
            tp_level=3,
            profit_pct=0.08,
            close_pct=0.30,
            target_price=54000.0,
            quantity=0.03,
            new_stop_loss=52500.0
        )
        bot.scaled_tp_manager.check_take_profit_levels = Mock(return_value=partial_action)
        bot.scaled_tp_manager.reset_tracking = Mock()  # Mock reset_tracking
        
        # Process symbol (simulated execution)
        bot._process_symbol("BTCUSDT", simulate_execution=True)
        
        # Verify position was closed
        assert "BTCUSDT" not in bot.risk_manager.active_positions
        
        # Verify tracking was reset
        bot.scaled_tp_manager.reset_tracking.assert_called_once_with("BTCUSDT")


def test_scaled_tp_disabled_uses_regular_tp(config_with_scaled_tp, mock_client):
    """Test that regular TP is used when scaled TP is disabled."""
    config_with_scaled_tp.enable_scaled_take_profit = False
    config_with_scaled_tp.take_profit_pct = 0.05
    
    with patch('src.trading_bot.Client') as mock_client_class:
        mock_client_class.return_value = mock_client
        
        bot = TradingBot(config_with_scaled_tp)
        
        # Create a mock position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            original_quantity=0.1,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            leverage=10,
            entry_time=datetime.now(),
            partial_exits=[],
            tp_levels_hit=[]
        )
        
        # Add position to risk manager
        bot.risk_manager.active_positions["BTCUSDT"] = position
        
        # Mock data manager to return candles at 5% profit
        mock_candles_15m = [Mock(close=52500.0) for _ in range(100)]
        mock_candles_1h = [Mock(close=52500.0) for _ in range(50)]
        bot.data_manager.fetch_historical_data = Mock(side_effect=lambda days, timeframe, symbol, use_cache=True: 
            mock_candles_15m if timeframe == "15m" else mock_candles_1h
        )
        bot.data_manager.get_latest_candles = Mock(side_effect=lambda tf, count, symbol: 
            mock_candles_15m if tf == "15m" else mock_candles_1h
        )
        
        # Mock strategy indicators
        bot.strategy.current_indicators = Mock(
            adx=30.0,
            rvol=2.0,
            atr_15m=100.0
        )
        bot.strategy.update_indicators = Mock()
        bot.strategy.check_long_entry = Mock(return_value=None)
        bot.strategy.check_short_entry = Mock(return_value=None)
        
        # Mock scaled TP manager to return None (disabled)
        bot.scaled_tp_manager.check_take_profit_levels = Mock(return_value=None)
        
        # Process symbol (simulated execution)
        bot._process_symbol("BTCUSDT", simulate_execution=True)
        
        # Verify position was closed via regular TP
        assert "BTCUSDT" not in bot.risk_manager.active_positions
        
        # Verify closed trades list has the trade
        closed_trades = bot.risk_manager.get_closed_trades()
        assert len(closed_trades) == 1
        assert closed_trades[0].exit_reason == "TAKE_PROFIT"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
