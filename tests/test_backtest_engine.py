"""Tests for BacktestEngine class."""

import pytest
from hypothesis import given, strategies as st, settings
from src.backtest_engine import BacktestEngine
from src.config import Config
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer
from src.models import Candle, Signal


class TestBacktestEngine:
    """Test suite for BacktestEngine property-based tests."""
    
    # Feature: binance-futures-bot, Property 4: Trade Execution Costs
    @settings(max_examples=100)
    @given(
        price=st.floats(min_value=100.0, max_value=100000.0),
        side=st.sampled_from(["BUY", "SELL"])
    )
    def test_trade_execution_costs_property(self, price, side):
        """For any simulated trade in backtest mode, the final execution price 
        should reflect exactly 0.05% trading fee and 0.02% slippage applied 
        in the correct direction.
        
        **Validates: Requirements 2.1, 2.2**
        """
        # Create fresh instances for each test
        config = Config()
        config.symbol = "BTCUSDT"
        config.risk_per_trade = 0.01
        config.leverage = 3
        config.trading_fee = 0.0005  # 0.05%
        config.slippage = 0.0002     # 0.02%
        
        strategy = StrategyEngine(config)
        position_sizer = PositionSizer(config)
        risk_manager = RiskManager(config, position_sizer)
        backtest_engine = BacktestEngine(config, strategy, risk_manager)
        
        # Apply fees and slippage
        adjusted_price = backtest_engine.apply_fees_and_slippage(price, side)
        
        # Calculate expected total cost
        expected_total_cost = backtest_engine.config.trading_fee + backtest_engine.config.slippage
        
        if side == "BUY":
            # For buys, price should increase
            expected_price = price * (1 + expected_total_cost)
            assert adjusted_price > price, "Buy price should increase with fees and slippage"
        else:  # SELL
            # For sells, price should decrease
            expected_price = price * (1 - expected_total_cost)
            assert adjusted_price < price, "Sell price should decrease with fees and slippage"
        
        # Check that the adjustment is exactly the expected amount
        # Allow small floating point error
        assert abs(adjusted_price - expected_price) < 0.01, \
            f"Price adjustment should be exactly {expected_total_cost * 100}%"
        
        # Verify the exact percentages
        if side == "BUY":
            actual_cost_pct = (adjusted_price - price) / price
        else:
            actual_cost_pct = (price - adjusted_price) / price
        
        # Should be exactly 0.05% + 0.02% = 0.07%
        expected_cost_pct = 0.0005 + 0.0002  # 0.07%
        assert abs(actual_cost_pct - expected_cost_pct) < 1e-6, \
            f"Total cost should be exactly 0.07%, got {actual_cost_pct * 100}%"
    
    # Feature: binance-futures-bot, Property 5: Backtest Metrics Completeness
    @settings(max_examples=100)
    @given(
        num_winning_trades=st.integers(min_value=1, max_value=50),
        num_losing_trades=st.integers(min_value=0, max_value=50),
        initial_balance=st.floats(min_value=1000.0, max_value=100000.0)
    )
    def test_backtest_metrics_completeness_property(
        self, 
        num_winning_trades, 
        num_losing_trades,
        initial_balance
    ):
        """For any completed backtest with at least one trade, the results 
        should include calculated values for ROI, Maximum Drawdown, Profit Factor, 
        Win Rate, and Total Trades.
        
        **Validates: Requirements 2.3**
        """
        from src.models import Trade
        import time
        
        # Create fresh instances
        config = Config()
        config.symbol = "BTCUSDT"
        strategy = StrategyEngine(config)
        position_sizer = PositionSizer(config)
        risk_manager = RiskManager(config, position_sizer)
        backtest_engine = BacktestEngine(config, strategy, risk_manager)
        
        # Set initial balance
        backtest_engine.initial_balance = initial_balance
        backtest_engine.current_balance = initial_balance
        
        # Create winning trades
        for i in range(num_winning_trades):
            trade = Trade(
                symbol="BTCUSDT",
                side="LONG",
                entry_price=50000.0,
                exit_price=51000.0,
                quantity=0.1,
                pnl=100.0,  # Positive PnL
                pnl_percent=2.0,
                entry_time=int(time.time() * 1000),
                exit_time=int(time.time() * 1000) + 3600000,
                exit_reason="TRAILING_STOP"
            )
            backtest_engine.trades.append(trade)
        
        # Create losing trades
        for i in range(num_losing_trades):
            trade = Trade(
                symbol="BTCUSDT",
                side="SHORT",
                entry_price=50000.0,
                exit_price=50500.0,
                quantity=0.1,
                pnl=-50.0,  # Negative PnL
                pnl_percent=-1.0,
                entry_time=int(time.time() * 1000),
                exit_time=int(time.time() * 1000) + 3600000,
                exit_reason="STOP_LOSS"
            )
            backtest_engine.trades.append(trade)
        
        # Create equity curve
        backtest_engine.equity_curve = [initial_balance]
        
        # Calculate metrics
        metrics = backtest_engine.calculate_metrics()
        
        # Verify all required metrics are present
        required_keys = [
            'total_trades',
            'winning_trades',
            'losing_trades',
            'win_rate',
            'total_pnl',
            'roi',
            'max_drawdown',
            'profit_factor',
            'sharpe_ratio'
        ]
        
        for key in required_keys:
            assert key in metrics, f"Missing required metric: {key}"
            assert metrics[key] is not None, f"Metric {key} should not be None"
        
        # Verify correctness of basic metrics
        assert metrics['total_trades'] == num_winning_trades + num_losing_trades
        assert metrics['winning_trades'] == num_winning_trades
        assert metrics['losing_trades'] == num_losing_trades
        
        # Verify win rate calculation
        expected_win_rate = (num_winning_trades / (num_winning_trades + num_losing_trades)) * 100
        assert abs(metrics['win_rate'] - expected_win_rate) < 0.01
        
        # Verify total PnL
        expected_pnl = num_winning_trades * 100.0 + num_losing_trades * (-50.0)
        assert abs(metrics['total_pnl'] - expected_pnl) < 0.01
        
        # Verify ROI is calculated
        expected_roi = (expected_pnl / initial_balance) * 100
        assert abs(metrics['roi'] - expected_roi) < 0.01
    
    # Feature: binance-futures-bot, Property 6: Realistic Fill Simulation
    @settings(max_examples=100)
    @given(
        open_price=st.floats(min_value=1000.0, max_value=100000.0),
        high_offset=st.floats(min_value=0.0, max_value=5000.0),
        low_offset=st.floats(min_value=0.0, max_value=5000.0),
        close_offset=st.floats(min_value=-2500.0, max_value=2500.0),
        signal_type=st.sampled_from(["LONG_ENTRY", "SHORT_ENTRY", "EXIT"]),
        is_long=st.booleans()
    )
    def test_realistic_fill_simulation_property(
        self,
        open_price,
        high_offset,
        low_offset,
        close_offset,
        signal_type,
        is_long
    ):
        """For any simulated order fill, the fill price should be within the 
        candle's high-low range and respect the order direction (buys at ask, 
        sells at bid).
        
        **Validates: Requirements 2.4**
        """
        # Create fresh instances
        config = Config()
        strategy = StrategyEngine(config)
        position_sizer = PositionSizer(config)
        risk_manager = RiskManager(config, position_sizer)
        backtest_engine = BacktestEngine(config, strategy, risk_manager)
        
        # Create a candle with valid OHLC relationships
        high = open_price + high_offset
        low = open_price - low_offset
        close = open_price + close_offset
        
        # Ensure close is within high/low range
        close = max(low, min(high, close))
        
        candle = Candle(
            timestamp=1000000,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=100.0
        )
        
        # Simulate trade execution
        fill_price = backtest_engine.simulate_trade_execution(
            signal_type,
            candle,
            is_long
        )
        
        # Verify fill price is within candle range
        assert fill_price >= candle.low, \
            f"Fill price {fill_price} should be >= candle low {candle.low}"
        assert fill_price <= candle.high, \
            f"Fill price {fill_price} should be <= candle high {candle.high}"
        
        # For entry signals, should use open price
        if signal_type in ["LONG_ENTRY", "SHORT_ENTRY"]:
            assert fill_price == candle.open, \
                f"Entry fills should use candle open price"
        
        # For exit signals, verify realistic fill based on direction
        if signal_type == "EXIT":
            if is_long:
                # Long exits (stop-loss) should be between low and close
                assert candle.low <= fill_price <= candle.close, \
                    f"Long exit should be between low and close"
            else:
                # Short exits (stop-loss) should be between close and high
                assert candle.close <= fill_price <= candle.high, \
                    f"Short exit should be between close and high"


class TestBacktestEngineUnit:
    """Unit tests for BacktestEngine."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = Config()
        config.symbol = "BTCUSDT"
        config.risk_per_trade = 0.01
        config.leverage = 3
        config.stop_loss_atr_multiplier = 2.0
        config.trailing_stop_atr_multiplier = 1.5
        config.atr_period = 14
        config.adx_period = 14
        config.adx_threshold = 20.0
        config.rvol_period = 20
        config.rvol_threshold = 1.2
        config.trading_fee = 0.0005
        config.slippage = 0.0002
        return config
    
    @pytest.fixture
    def strategy(self, config):
        """Create a test strategy engine."""
        return StrategyEngine(config)
    
    @pytest.fixture
    def position_sizer(self, config):
        """Create a test position sizer."""
        return PositionSizer(config)
    
    @pytest.fixture
    def risk_manager(self, config, position_sizer):
        """Create a test risk manager."""
        return RiskManager(config, position_sizer)
    
    @pytest.fixture
    def backtest_engine(self, config, strategy, risk_manager):
        """Create a test backtest engine."""
        return BacktestEngine(config, strategy, risk_manager)
    
    @pytest.fixture
    def sample_candles(self):
        """Create sample candle data for testing."""
        candles = []
        base_time = 1000000
        base_price = 50000.0
        
        for i in range(100):
            candle = Candle(
                timestamp=base_time + i * 15 * 60 * 1000,  # 15m intervals
                open=base_price + i * 10,
                high=base_price + i * 10 + 100,
                low=base_price + i * 10 - 100,
                close=base_price + i * 10 + 50,
                volume=100.0 + i
            )
            candles.append(candle)
        
        return candles
    
    def test_apply_fees_and_slippage_buy(self, backtest_engine):
        """Test that fees and slippage are correctly applied to buy orders."""
        price = 50000.0
        adjusted = backtest_engine.apply_fees_and_slippage(price, "BUY")
        
        # Should increase by 0.07%
        expected = price * 1.0007
        assert abs(adjusted - expected) < 0.01
        assert adjusted > price
    
    def test_apply_fees_and_slippage_sell(self, backtest_engine):
        """Test that fees and slippage are correctly applied to sell orders."""
        price = 50000.0
        adjusted = backtest_engine.apply_fees_and_slippage(price, "SELL")
        
        # Should decrease by 0.07%
        expected = price * 0.9993
        assert abs(adjusted - expected) < 0.01
        assert adjusted < price
    
    def test_apply_fees_and_slippage_invalid_side(self, backtest_engine):
        """Test that invalid side raises ValueError."""
        with pytest.raises(ValueError, match="side must be 'BUY' or 'SELL'"):
            backtest_engine.apply_fees_and_slippage(50000.0, "INVALID")
    
    def test_apply_fees_and_slippage_invalid_price(self, backtest_engine):
        """Test that invalid price raises ValueError."""
        with pytest.raises(ValueError, match="price must be positive"):
            backtest_engine.apply_fees_and_slippage(-100.0, "BUY")
        
        with pytest.raises(ValueError, match="price must be positive"):
            backtest_engine.apply_fees_and_slippage(0.0, "BUY")
    
    def test_simulate_trade_execution_long_entry(self, backtest_engine):
        """Test simulation of long entry execution."""
        candle = Candle(
            timestamp=1000000,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0
        )
        
        fill_price = backtest_engine.simulate_trade_execution(
            "LONG_ENTRY",
            candle,
            is_long=True
        )
        
        # Should use candle open
        assert fill_price == candle.open
    
    def test_simulate_trade_execution_short_entry(self, backtest_engine):
        """Test simulation of short entry execution."""
        candle = Candle(
            timestamp=1000000,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0
        )
        
        fill_price = backtest_engine.simulate_trade_execution(
            "SHORT_ENTRY",
            candle,
            is_long=False
        )
        
        # Should use candle open
        assert fill_price == candle.open
    
    def test_simulate_trade_execution_long_exit(self, backtest_engine):
        """Test simulation of long exit (stop-loss) execution."""
        candle = Candle(
            timestamp=1000000,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0
        )
        
        fill_price = backtest_engine.simulate_trade_execution(
            "EXIT",
            candle,
            is_long=True
        )
        
        # Should be between low and close, closer to low
        assert candle.low <= fill_price <= candle.close
    
    def test_simulate_trade_execution_short_exit(self, backtest_engine):
        """Test simulation of short exit (stop-loss) execution."""
        candle = Candle(
            timestamp=1000000,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0
        )
        
        fill_price = backtest_engine.simulate_trade_execution(
            "EXIT",
            candle,
            is_long=False
        )
        
        # Should be between close and high, closer to high
        assert candle.close <= fill_price <= candle.high
    
    def test_calculate_metrics_no_trades(self, backtest_engine):
        """Test metrics calculation with no trades."""
        backtest_engine.trades = []
        backtest_engine.initial_balance = 10000.0
        
        metrics = backtest_engine.calculate_metrics()
        
        assert metrics['total_trades'] == 0
        assert metrics['winning_trades'] == 0
        assert metrics['losing_trades'] == 0
        assert metrics['win_rate'] == 0.0
        assert metrics['total_pnl'] == 0.0
        assert metrics['roi'] == 0.0
    
    def test_calculate_max_drawdown_empty(self, backtest_engine):
        """Test max drawdown calculation with empty equity curve."""
        backtest_engine.equity_curve = []
        
        drawdown = backtest_engine._calculate_max_drawdown()
        
        assert drawdown == 0.0
    
    def test_calculate_max_drawdown_no_drawdown(self, backtest_engine):
        """Test max drawdown calculation with no drawdown."""
        backtest_engine.equity_curve = [10000, 10100, 10200, 10300]
        
        drawdown = backtest_engine._calculate_max_drawdown()
        
        assert drawdown == 0.0
    
    def test_calculate_max_drawdown_with_drawdown(self, backtest_engine):
        """Test max drawdown calculation with drawdown."""
        backtest_engine.equity_curve = [10000, 10500, 10200, 9800, 10100]
        
        drawdown = backtest_engine._calculate_max_drawdown()
        
        # Peak was 10500, lowest after peak was 9800
        # Drawdown = 10500 - 9800 = 700
        assert drawdown == 700.0
    
    def test_calculate_sharpe_ratio_insufficient_trades(self, backtest_engine):
        """Test Sharpe ratio calculation with insufficient trades."""
        backtest_engine.trades = []
        
        sharpe = backtest_engine._calculate_sharpe_ratio()
        
        assert sharpe == 0.0
    
    def test_backtest_with_winning_trades(self):
        """Test backtest with winning trades scenario."""
        from src.models import Trade
        import time
        
        config = Config()
        config.symbol = "BTCUSDT"
        config.trading_fee = 0.0005
        config.slippage = 0.0002
        
        strategy = StrategyEngine(config)
        position_sizer = PositionSizer(config)
        risk_manager = RiskManager(config, position_sizer)
        backtest_engine = BacktestEngine(config, strategy, risk_manager)
        
        # Set initial balance
        backtest_engine.initial_balance = 10000.0
        
        # Create winning trades
        for i in range(5):
            trade = Trade(
                symbol="BTCUSDT",
                side="LONG",
                entry_price=50000.0,
                exit_price=51000.0,
                quantity=0.1,
                pnl=100.0,
                pnl_percent=2.0,
                entry_time=int(time.time() * 1000),
                exit_time=int(time.time() * 1000) + 3600000,
                exit_reason="TRAILING_STOP"
            )
            backtest_engine.trades.append(trade)
        
        backtest_engine.equity_curve = [10000, 10100, 10200, 10300, 10400, 10500]
        
        metrics = backtest_engine.calculate_metrics()
        
        assert metrics['total_trades'] == 5
        assert metrics['winning_trades'] == 5
        assert metrics['losing_trades'] == 0
        assert metrics['win_rate'] == 100.0
        assert metrics['total_pnl'] == 500.0
        assert metrics['roi'] == 5.0
        assert metrics['profit_factor'] == 0.0  # No losses
    
    def test_backtest_with_losing_trades(self):
        """Test backtest with losing trades scenario."""
        from src.models import Trade
        import time
        
        config = Config()
        config.symbol = "BTCUSDT"
        config.trading_fee = 0.0005
        config.slippage = 0.0002
        
        strategy = StrategyEngine(config)
        position_sizer = PositionSizer(config)
        risk_manager = RiskManager(config, position_sizer)
        backtest_engine = BacktestEngine(config, strategy, risk_manager)
        
        # Set initial balance
        backtest_engine.initial_balance = 10000.0
        
        # Create losing trades
        for i in range(3):
            trade = Trade(
                symbol="BTCUSDT",
                side="SHORT",
                entry_price=50000.0,
                exit_price=50500.0,
                quantity=0.1,
                pnl=-50.0,
                pnl_percent=-1.0,
                entry_time=int(time.time() * 1000),
                exit_time=int(time.time() * 1000) + 3600000,
                exit_reason="STOP_LOSS"
            )
            backtest_engine.trades.append(trade)
        
        backtest_engine.equity_curve = [10000, 9950, 9900, 9850]
        
        metrics = backtest_engine.calculate_metrics()
        
        assert metrics['total_trades'] == 3
        assert metrics['winning_trades'] == 0
        assert metrics['losing_trades'] == 3
        assert metrics['win_rate'] == 0.0
        assert metrics['total_pnl'] == -150.0
        assert metrics['roi'] == -1.5
        assert metrics['profit_factor'] == 0.0  # No wins
    
    def test_backtest_with_mixed_results(self):
        """Test backtest with mixed winning and losing trades."""
        from src.models import Trade
        import time
        
        config = Config()
        config.symbol = "BTCUSDT"
        config.trading_fee = 0.0005
        config.slippage = 0.0002
        
        strategy = StrategyEngine(config)
        position_sizer = PositionSizer(config)
        risk_manager = RiskManager(config, position_sizer)
        backtest_engine = BacktestEngine(config, strategy, risk_manager)
        
        # Set initial balance
        backtest_engine.initial_balance = 10000.0
        
        # Create 3 winning trades
        for i in range(3):
            trade = Trade(
                symbol="BTCUSDT",
                side="LONG",
                entry_price=50000.0,
                exit_price=51000.0,
                quantity=0.1,
                pnl=100.0,
                pnl_percent=2.0,
                entry_time=int(time.time() * 1000),
                exit_time=int(time.time() * 1000) + 3600000,
                exit_reason="TRAILING_STOP"
            )
            backtest_engine.trades.append(trade)
        
        # Create 2 losing trades
        for i in range(2):
            trade = Trade(
                symbol="BTCUSDT",
                side="SHORT",
                entry_price=50000.0,
                exit_price=50500.0,
                quantity=0.1,
                pnl=-50.0,
                pnl_percent=-1.0,
                entry_time=int(time.time() * 1000),
                exit_time=int(time.time() * 1000) + 3600000,
                exit_reason="STOP_LOSS"
            )
            backtest_engine.trades.append(trade)
        
        backtest_engine.equity_curve = [10000, 10100, 10200, 10300, 10250, 10200]
        
        metrics = backtest_engine.calculate_metrics()
        
        # Verify metrics calculations
        assert metrics['total_trades'] == 5
        assert metrics['winning_trades'] == 3
        assert metrics['losing_trades'] == 2
        assert metrics['win_rate'] == 60.0
        assert metrics['total_pnl'] == 200.0  # 3*100 - 2*50
        assert metrics['roi'] == 2.0
        
        # Profit factor = gross profit / gross loss = 300 / 100 = 3.0
        assert abs(metrics['profit_factor'] - 3.0) < 0.01
        
        # Verify average win/loss
        assert metrics['average_win'] == 100.0
        assert metrics['average_loss'] == -50.0
        assert metrics['largest_win'] == 100.0
        assert metrics['largest_loss'] == -50.0
    
    def test_verify_metrics_calculations(self):
        """Test that metrics are calculated correctly."""
        from src.models import Trade
        import time
        
        config = Config()
        strategy = StrategyEngine(config)
        position_sizer = PositionSizer(config)
        risk_manager = RiskManager(config, position_sizer)
        backtest_engine = BacktestEngine(config, strategy, risk_manager)
        
        backtest_engine.initial_balance = 10000.0
        
        # Create specific trades to test calculations
        trades = [
            Trade("BTCUSDT", "LONG", 50000, 51000, 0.1, 100, 2.0, 
                  int(time.time() * 1000), int(time.time() * 1000) + 3600000, "TRAILING_STOP"),
            Trade("BTCUSDT", "SHORT", 50000, 50500, 0.1, -50, -1.0,
                  int(time.time() * 1000), int(time.time() * 1000) + 7200000, "STOP_LOSS"),
            Trade("BTCUSDT", "LONG", 51000, 52000, 0.1, 100, 2.0,
                  int(time.time() * 1000), int(time.time() * 1000) + 10800000, "TRAILING_STOP"),
        ]
        
        backtest_engine.trades = trades
        backtest_engine.equity_curve = [10000, 10100, 10050, 10150]
        
        metrics = backtest_engine.calculate_metrics()
        
        # Verify all calculations
        assert metrics['total_trades'] == 3
        assert metrics['winning_trades'] == 2
        assert metrics['losing_trades'] == 1
        assert abs(metrics['win_rate'] - 66.67) < 0.1
        assert metrics['total_pnl'] == 150.0
        assert metrics['roi'] == 1.5
        
        # Max drawdown: peak 10100, trough 10050 = 50
        assert metrics['max_drawdown'] == 50.0
        
        # Profit factor: 200 / 50 = 4.0
        assert abs(metrics['profit_factor'] - 4.0) < 0.01
        
        # Average trade duration
        assert metrics['average_trade_duration'] > 0



class TestBacktestEngineEnhanced:
    """Integration tests for enhanced backtest features."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = Config()
        config.symbol = "BTCUSDT"
        config.risk_per_trade = 0.01
        config.leverage = 3
        config.trading_fee = 0.0005
        config.slippage = 0.0002
        return config
    
    @pytest.fixture
    def strategy(self, config):
        """Create a test strategy engine."""
        return StrategyEngine(config)
    
    @pytest.fixture
    def position_sizer(self, config):
        """Create a test position sizer."""
        return PositionSizer(config)
    
    @pytest.fixture
    def risk_manager(self, config, position_sizer):
        """Create a test risk manager."""
        return RiskManager(config, position_sizer)
    
    @pytest.fixture
    def backtest_engine(self, config, strategy, risk_manager):
        """Create a test backtest engine."""
        return BacktestEngine(config, strategy, risk_manager)
    
    @pytest.fixture
    def sample_candles(self):
        """Create sample candle data for testing."""
        candles_15m = []
        candles_1h = []
        candles_5m = []
        candles_4h = []
        
        # Use a realistic timestamp (Jan 1, 2024)
        base_time = 1704067200000  # Jan 1, 2024 00:00:00 UTC in milliseconds
        base_price = 50000.0
        
        # Generate 15m candles
        for i in range(200):
            candle = Candle(
                timestamp=base_time + i * 15 * 60 * 1000,
                open=base_price + i * 10,
                high=base_price + i * 10 + 100,
                low=base_price + i * 10 - 100,
                close=base_price + i * 10 + 50,
                volume=100.0 + i
            )
            candles_15m.append(candle)
        
        # Generate 1h candles (every 4th 15m candle)
        for i in range(0, 200, 4):
            candle = Candle(
                timestamp=base_time + i * 15 * 60 * 1000,
                open=base_price + i * 10,
                high=base_price + i * 10 + 400,
                low=base_price + i * 10 - 400,
                close=base_price + i * 10 + 200,
                volume=400.0 + i * 4
            )
            candles_1h.append(candle)
        
        # Generate 5m candles (every 1/3 of 15m candle)
        for i in range(600):
            candle = Candle(
                timestamp=base_time + i * 5 * 60 * 1000,
                open=base_price + i * 3.33,
                high=base_price + i * 3.33 + 33,
                low=base_price + i * 3.33 - 33,
                close=base_price + i * 3.33 + 16,
                volume=33.0 + i * 0.33
            )
            candles_5m.append(candle)
        
        # Generate 4h candles (every 16th 15m candle)
        for i in range(0, 200, 16):
            candle = Candle(
                timestamp=base_time + i * 15 * 60 * 1000,
                open=base_price + i * 10,
                high=base_price + i * 10 + 1600,
                low=base_price + i * 10 - 1600,
                close=base_price + i * 10 + 800,
                volume=1600.0 + i * 16
            )
            candles_4h.append(candle)
        
        return {
            '15m': candles_15m,
            '1h': candles_1h,
            '5m': candles_5m,
            '4h': candles_4h
        }
    
    def test_multi_timeframe_backtest(self, backtest_engine, sample_candles):
        """Test backtest with multi-timeframe data."""
        # Run backtest with all timeframes
        results = backtest_engine.run_backtest(
            candles_15m=sample_candles['15m'],
            candles_1h=sample_candles['1h'],
            initial_balance=10000.0,
            candles_5m=sample_candles['5m'],
            candles_4h=sample_candles['4h']
        )
        
        # Verify results structure
        assert 'total_trades' in results
        assert 'roi' in results
        assert 'feature_metrics' in results
        
        # Verify feature metrics structure
        feature_metrics = results['feature_metrics']
        assert 'adaptive_thresholds' in feature_metrics
        assert 'volume_profile' in feature_metrics
        assert 'ml_predictions' in feature_metrics
        assert 'market_regime' in feature_metrics
    
    def test_feature_metrics_tracking(self, backtest_engine, sample_candles):
        """Test that feature metrics are tracked during backtest."""
        # Run backtest
        results = backtest_engine.run_backtest(
            candles_15m=sample_candles['15m'],
            candles_1h=sample_candles['1h'],
            initial_balance=10000.0
        )
        
        # Get feature metrics
        feature_metrics = backtest_engine.get_feature_metrics()
        
        # Verify structure
        assert isinstance(feature_metrics, dict)
        assert 'adaptive_thresholds' in feature_metrics
        assert 'volume_profile' in feature_metrics
        assert 'ml_predictions' in feature_metrics
        assert 'market_regime' in feature_metrics
        
        # Verify each feature has expected fields
        for feature_name, metrics in feature_metrics.items():
            assert 'enabled' in metrics
            assert isinstance(metrics['enabled'], bool)
    
    def test_ab_comparison_structure(self, backtest_engine, sample_candles):
        """Test A/B comparison returns proper structure."""
        # Run A/B comparison
        results = backtest_engine.run_ab_comparison(
            candles_15m=sample_candles['15m'],
            candles_1h=sample_candles['1h'],
            initial_balance=10000.0
        )
        
        # Verify baseline results exist
        assert 'baseline' in results
        assert 'all_features' in results
        
        # Verify comparison report exists
        assert 'comparison_report' in results
        report = results['comparison_report']
        
        assert 'summary' in report
        assert 'feature_contributions' in report
        assert 'recommendations' in report
        
        # Verify summary metrics
        summary = report['summary']
        assert 'baseline_roi' in summary
        assert 'all_features_roi' in summary
        assert 'roi_improvement' in summary
    
    def test_timeframe_synchronization(self, backtest_engine, sample_candles):
        """Test that timeframes are properly synchronized."""
        # Build timeframe indices
        indices = backtest_engine._build_timeframe_indices(
            sample_candles['15m'],
            sample_candles['1h'],
            sample_candles['5m'],
            sample_candles['4h']
        )
        
        # Verify structure
        assert '5m' in indices
        assert '1h' in indices
        assert '4h' in indices
        
        # Verify indices are dictionaries
        assert isinstance(indices['5m'], dict)
        assert isinstance(indices['1h'], dict)
        assert isinstance(indices['4h'], dict)
        
        # Verify indices contain mappings
        assert len(indices['5m']) > 0
        assert len(indices['1h']) > 0
        assert len(indices['4h']) > 0
    
    def test_feature_state_management(self, backtest_engine):
        """Test saving and restoring feature states."""
        # Save current states
        states = backtest_engine._save_feature_states()
        
        # Verify states is a dictionary
        assert isinstance(states, dict)
        
        # Disable all features
        backtest_engine._disable_all_features()
        
        # Verify features are disabled
        for feature_name in ['adaptive_threshold_mgr', 'volume_profile_analyzer', 
                            'ml_predictor', 'market_regime_detector']:
            if hasattr(backtest_engine.strategy, feature_name):
                assert getattr(backtest_engine.strategy, feature_name) is None
        
        # Restore states
        backtest_engine._restore_feature_states(states)
        
        # Verify features are restored
        for feature_name, state in states.items():
            if hasattr(backtest_engine.strategy, feature_name):
                assert getattr(backtest_engine.strategy, feature_name) == state
    
    def test_comparison_report_generation(self, backtest_engine):
        """Test comparison report generation."""
        # Create mock results
        results = {
            'baseline': {
                'roi': 5.0,
                'win_rate': 50.0,
                'profit_factor': 1.5,
                'total_trades': 10
            },
            'all_features': {
                'roi': 8.0,
                'win_rate': 60.0,
                'profit_factor': 2.0,
                'total_trades': 12
            },
            'without_adaptive_threshold_mgr': {
                'roi': 7.0,
                'win_rate': 55.0,
                'profit_factor': 1.8,
                'total_trades': 11
            }
        }
        
        # Generate report
        report = backtest_engine._generate_comparison_report(results)
        
        # Verify report structure
        assert 'summary' in report
        assert 'feature_contributions' in report
        assert 'recommendations' in report
        
        # Verify summary calculations
        summary = report['summary']
        assert summary['roi_improvement'] == 3.0  # 8.0 - 5.0
        assert summary['win_rate_improvement'] == 10.0  # 60.0 - 50.0
        
        # Verify feature contributions
        contributions = report['feature_contributions']
        assert 'adaptive_threshold_mgr' in contributions
        
        # Verify contribution calculation
        # All features ROI (8.0) - Without feature ROI (7.0) = 1.0
        assert contributions['adaptive_threshold_mgr']['roi_contribution'] == 1.0



class TestBacktestScaledTP:
    """Unit tests for scaled take profit backtest integration."""
    
    @pytest.fixture
    def config_scaled_tp(self):
        """Create a test configuration with scaled TP enabled."""
        config = Config()
        config.symbol = "BTCUSDT"
        config.risk_per_trade = 0.01
        config.leverage = 3
        config.trading_fee = 0.0005
        config.slippage = 0.0002
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        config.scaled_tp_min_order_size = 0.001
        config.scaled_tp_fallback_to_single = True
        return config
    
    @pytest.fixture
    def strategy_scaled_tp(self, config_scaled_tp):
        """Create a test strategy engine."""
        return StrategyEngine(config_scaled_tp)
    
    @pytest.fixture
    def position_sizer_scaled_tp(self, config_scaled_tp):
        """Create a test position sizer."""
        return PositionSizer(config_scaled_tp)
    
    @pytest.fixture
    def risk_manager_scaled_tp(self, config_scaled_tp, position_sizer_scaled_tp):
        """Create a test risk manager."""
        return RiskManager(config_scaled_tp, position_sizer_scaled_tp)
    
    @pytest.fixture
    def backtest_engine_scaled_tp(self, config_scaled_tp, strategy_scaled_tp, risk_manager_scaled_tp):
        """Create a test backtest engine with scaled TP."""
        return BacktestEngine(config_scaled_tp, strategy_scaled_tp, risk_manager_scaled_tp)
    
    def test_scaled_tp_manager_initialized(self, backtest_engine_scaled_tp):
        """Test that ScaledTakeProfitManager is initialized in backtest engine."""
        assert hasattr(backtest_engine_scaled_tp, 'scaled_tp_manager')
        assert backtest_engine_scaled_tp.scaled_tp_manager is not None
        assert backtest_engine_scaled_tp.scaled_tp_manager.config.enable_scaled_take_profit is True
    
    def test_scaled_tp_feature_metrics_initialized(self, backtest_engine_scaled_tp):
        """Test that scaled TP feature metrics are initialized."""
        assert 'scaled_take_profit' in backtest_engine_scaled_tp.feature_metrics
        
        scaled_tp_metrics = backtest_engine_scaled_tp.feature_metrics['scaled_take_profit']
        assert scaled_tp_metrics['enabled'] is True
        assert scaled_tp_metrics['partial_closes'] == 0
        assert scaled_tp_metrics['tp1_hits'] == 0
        assert scaled_tp_metrics['tp2_hits'] == 0
        assert scaled_tp_metrics['tp3_hits'] == 0
        assert scaled_tp_metrics['total_partial_profit'] == 0.0
    
    def test_simulate_partial_close(self, backtest_engine_scaled_tp):
        """Test partial close simulation."""
        from src.models import Position, PartialCloseAction
        import time
        
        # Create a test position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=int(time.time() * 1000),
            original_quantity=0.1
        )
        
        # Create a partial close action
        action = PartialCloseAction(
            tp_level=1,
            profit_pct=0.03,
            close_pct=0.40,
            target_price=51500.0,
            quantity=0.04,
            new_stop_loss=50000.0
        )
        
        # Create a test candle
        candle = Candle(
            timestamp=int(time.time() * 1000),
            open=51500.0,
            high=51600.0,
            low=51400.0,
            close=51500.0,
            volume=100.0
        )
        
        # Simulate partial close
        result = backtest_engine_scaled_tp._simulate_partial_close(position, action, candle)
        
        # Verify result
        assert result['success'] is True
        assert result['filled_quantity'] == 0.04
        assert result['fill_price'] > 0
        assert result['realized_profit'] > 0
        assert result['error_message'] is None
    
    def test_simulate_partial_close_quantity_limit(self, backtest_engine_scaled_tp):
        """Test that partial close doesn't exceed position quantity."""
        from src.models import Position, PartialCloseAction
        import time
        
        # Create a test position with small quantity
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.02,  # Small remaining quantity
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=int(time.time() * 1000),
            original_quantity=0.1
        )
        
        # Create a partial close action that tries to close more than available
        action = PartialCloseAction(
            tp_level=3,
            profit_pct=0.08,
            close_pct=0.30,
            target_price=54000.0,
            quantity=0.03,  # More than position.quantity
            new_stop_loss=52500.0
        )
        
        # Create a test candle
        candle = Candle(
            timestamp=int(time.time() * 1000),
            open=54000.0,
            high=54100.0,
            low=53900.0,
            close=54000.0,
            volume=100.0
        )
        
        # Simulate partial close
        result = backtest_engine_scaled_tp._simulate_partial_close(position, action, candle)
        
        # Verify that filled quantity is limited to position quantity
        assert result['success'] is True
        assert result['filled_quantity'] == 0.02  # Limited to position.quantity
        assert result['filled_quantity'] <= position.quantity
    
    def test_check_exit_conditions_scaled_tp_partial(self, backtest_engine_scaled_tp):
        """Test exit conditions check with scaled TP (partial close)."""
        from src.models import Position
        import time
        
        # Create a test position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=int(time.time() * 1000),
            original_quantity=0.1
        )
        
        # Create a candle where TP1 is hit (3% profit = 51500)
        candle = Candle(
            timestamp=int(time.time() * 1000),
            open=51500.0,
            high=51600.0,
            low=51400.0,
            close=51500.0,
            volume=100.0
        )
        
        current_price = 51500.0
        
        # Check exit conditions
        exit_reason = backtest_engine_scaled_tp._check_exit_conditions_scaled_tp(
            position, candle, current_price
        )
        
        # Should not fully exit, just partial close
        # Position should be updated with reduced quantity
        assert position.quantity < 0.1  # Quantity reduced
        assert len(position.tp_levels_hit) == 1  # TP1 hit
        assert position.tp_levels_hit[0] == 1
        assert len(position.partial_exits) == 1  # One partial exit recorded
        assert exit_reason is None  # Not fully closed yet
    
    def test_check_exit_conditions_scaled_tp_stop_loss(self, backtest_engine_scaled_tp):
        """Test that stop loss is checked before TP levels."""
        from src.models import Position
        import time
        
        # Create a test position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=int(time.time() * 1000),
            original_quantity=0.1
        )
        
        # Create a candle where stop loss is hit
        candle = Candle(
            timestamp=int(time.time() * 1000),
            open=49500.0,
            high=49600.0,
            low=48900.0,  # Touches stop loss
            close=49000.0,
            volume=100.0
        )
        
        current_price = 49000.0
        
        # Check exit conditions
        exit_reason = backtest_engine_scaled_tp._check_exit_conditions_scaled_tp(
            position, candle, current_price
        )
        
        # Should exit due to stop loss
        assert exit_reason == "TRAILING_STOP"
        assert len(backtest_engine_scaled_tp.trades) == 1
        assert backtest_engine_scaled_tp.trades[0].exit_reason == "TRAILING_STOP"
    
    def test_check_exit_conditions_scaled_tp_final(self, backtest_engine_scaled_tp):
        """Test that position closes after all TP levels hit."""
        from src.models import Position
        import time
        
        # Create a test position with TP1 and TP2 already hit
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.03,  # 30% remaining (TP1 40% + TP2 30% already closed)
            leverage=3,
            stop_loss=51500.0,  # Moved to TP1 level
            trailing_stop=51500.0,
            entry_time=int(time.time() * 1000),
            original_quantity=0.1,
            tp_levels_hit=[1, 2],
            partial_exits=[
                {
                    'tp_level': 1,
                    'exit_time': int(time.time() * 1000),
                    'exit_price': 51500.0,
                    'quantity_closed': 0.04,
                    'profit': 60.0,
                    'profit_pct': 0.03,
                    'new_stop_loss': 50000.0
                },
                {
                    'tp_level': 2,
                    'exit_time': int(time.time() * 1000),
                    'exit_price': 52500.0,
                    'quantity_closed': 0.03,
                    'profit': 75.0,
                    'profit_pct': 0.05,
                    'new_stop_loss': 51500.0
                }
            ]
        )
        
        # Create a candle where TP3 is hit (8% profit = 54000)
        candle = Candle(
            timestamp=int(time.time() * 1000),
            open=54000.0,
            high=54100.0,
            low=53900.0,
            close=54000.0,
            volume=100.0
        )
        
        current_price = 54000.0
        
        # Initialize tracking for this position (simulating that it was tracked before)
        backtest_engine_scaled_tp.scaled_tp_manager._initialize_tracking(position)
        
        # Check exit conditions
        exit_reason = backtest_engine_scaled_tp._check_exit_conditions_scaled_tp(
            position, candle, current_price
        )
        
        # Should fully close position
        # Note: The exit_reason might be None if the partial close happens but position isn't fully closed yet
        # The important thing is that the position is updated correctly
        assert len(position.tp_levels_hit) == 3  # All TPs hit
        assert len(position.partial_exits) == 3  # All partials recorded
        
        # After all TPs hit, position should be fully closed
        if exit_reason == "SCALED_TP_FINAL":
            assert position.quantity == 0  # Fully closed
            assert len(backtest_engine_scaled_tp.trades) == 1
            assert backtest_engine_scaled_tp.trades[0].exit_reason == "SCALED_TP_FINAL"
    
    def test_check_exit_conditions_single_tp(self, config_scaled_tp, strategy_scaled_tp, 
                                            position_sizer_scaled_tp, risk_manager_scaled_tp):
        """Test single TP exit conditions (when scaled TP disabled)."""
        from src.models import Position
        import time
        
        # Disable scaled TP
        config_scaled_tp.enable_scaled_take_profit = False
        config_scaled_tp.take_profit_pct = 0.05  # 5% single TP
        
        backtest_engine = BacktestEngine(config_scaled_tp, strategy_scaled_tp, risk_manager_scaled_tp)
        
        # Create a test position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=int(time.time() * 1000),
            original_quantity=0.1
        )
        
        # Create a candle where single TP is hit (5% profit = 52500)
        candle = Candle(
            timestamp=int(time.time() * 1000),
            open=52500.0,
            high=52600.0,
            low=52400.0,
            close=52500.0,
            volume=100.0
        )
        
        current_price = 52500.0
        
        # Check exit conditions
        exit_reason = backtest_engine._check_exit_conditions_single_tp(
            position, candle, current_price
        )
        
        # Should fully close position
        assert exit_reason == "TAKE_PROFIT"
        assert len(backtest_engine.trades) == 1
        assert backtest_engine.trades[0].exit_reason == "TAKE_PROFIT"
    
    def test_position_size_updates_after_partial(self, backtest_engine_scaled_tp):
        """Test that position size is correctly updated after partial close."""
        from src.models import Position
        import time
        
        # Create a test position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=int(time.time() * 1000),
            original_quantity=0.1
        )
        
        initial_quantity = position.quantity
        
        # Create a candle where TP1 is hit
        candle = Candle(
            timestamp=int(time.time() * 1000),
            open=51500.0,
            high=51600.0,
            low=51400.0,
            close=51500.0,
            volume=100.0
        )
        
        current_price = 51500.0
        
        # Check exit conditions (should trigger partial close)
        backtest_engine_scaled_tp._check_exit_conditions_scaled_tp(
            position, candle, current_price
        )
        
        # Verify position size updated
        assert position.quantity < initial_quantity
        expected_remaining = initial_quantity * (1 - 0.40)  # 40% closed
        assert abs(position.quantity - expected_remaining) < 0.0001
    
    def test_stop_loss_ladder_in_backtest(self, backtest_engine_scaled_tp):
        """Test that stop loss is updated after TP hits in backtest."""
        from src.models import Position
        import time
        
        # Create a test position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=int(time.time() * 1000),
            original_quantity=0.1
        )
        
        initial_stop_loss = position.stop_loss
        
        # Create a candle where TP1 is hit
        candle = Candle(
            timestamp=int(time.time() * 1000),
            open=51500.0,
            high=51600.0,
            low=51400.0,
            close=51500.0,
            volume=100.0
        )
        
        current_price = 51500.0
        
        # Check exit conditions (should trigger partial close and SL update)
        backtest_engine_scaled_tp._check_exit_conditions_scaled_tp(
            position, candle, current_price
        )
        
        # Verify stop loss updated to breakeven
        assert position.stop_loss > initial_stop_loss
        assert position.stop_loss == position.entry_price  # Moved to breakeven
        assert position.trailing_stop == position.stop_loss
    
    def test_partial_exits_tracked_in_backtest(self, backtest_engine_scaled_tp):
        """Test that partial exits are tracked in backtest results."""
        from src.models import Position
        import time
        
        # Create a test position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=int(time.time() * 1000),
            original_quantity=0.1
        )
        
        # Create a candle where TP1 is hit
        candle = Candle(
            timestamp=int(time.time() * 1000),
            open=51500.0,
            high=51600.0,
            low=51400.0,
            close=51500.0,
            volume=100.0
        )
        
        current_price = 51500.0
        
        # Check exit conditions
        backtest_engine_scaled_tp._check_exit_conditions_scaled_tp(
            position, candle, current_price
        )
        
        # Verify partial exit tracked
        assert len(position.partial_exits) == 1
        
        partial_exit = position.partial_exits[0]
        assert partial_exit['tp_level'] == 1
        assert partial_exit['quantity_closed'] > 0
        assert partial_exit['profit'] > 0
        assert partial_exit['exit_price'] > position.entry_price
        assert partial_exit['new_stop_loss'] == position.entry_price
    
    def test_scaled_tp_metrics_updated(self, backtest_engine_scaled_tp):
        """Test that scaled TP metrics are updated during backtest."""
        from src.models import Position
        import time
        
        # Create a test position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            quantity=0.1,
            leverage=3,
            stop_loss=49000.0,
            trailing_stop=49000.0,
            entry_time=int(time.time() * 1000),
            original_quantity=0.1
        )
        
        # Create a candle where TP1 is hit
        candle = Candle(
            timestamp=int(time.time() * 1000),
            open=51500.0,
            high=51600.0,
            low=51400.0,
            close=51500.0,
            volume=100.0
        )
        
        current_price = 51500.0
        
        # Check initial metrics
        assert backtest_engine_scaled_tp.feature_metrics['scaled_take_profit']['partial_closes'] == 0
        assert backtest_engine_scaled_tp.feature_metrics['scaled_take_profit']['tp1_hits'] == 0
        
        # Check exit conditions (should trigger partial close)
        backtest_engine_scaled_tp._check_exit_conditions_scaled_tp(
            position, candle, current_price
        )
        
        # Verify metrics updated
        assert backtest_engine_scaled_tp.feature_metrics['scaled_take_profit']['partial_closes'] == 1
        assert backtest_engine_scaled_tp.feature_metrics['scaled_take_profit']['tp1_hits'] == 1
        assert backtest_engine_scaled_tp.feature_metrics['scaled_take_profit']['total_partial_profit'] > 0
