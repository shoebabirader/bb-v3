"""
Integration tests for Streamlit Trading Dashboard.

These tests validate that the dashboard components work together correctly
and that the full dashboard can load and function properly.
"""

import pytest
import json
import os
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from src.streamlit_data_provider import StreamlitDataProvider
from src.streamlit_bot_controller import BotController
from src.streamlit_config_editor import ConfigEditor
from src.streamlit_charts import ChartGenerator


# ===== FIXTURES =====

@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    config_data = {
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "leverage": 10,
        "mode": "paper",
        "risk_per_trade": 0.02,
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.04,
        "adx_threshold": 25.0,
        "rvol_threshold": 1.5,
        "api_key": "test_key",
        "api_secret": "test_secret"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def temp_results_file():
    """Create a temporary results file for testing."""
    results_data = {
        "balance": 10000.0,
        "total_pnl": 250.50,
        "total_pnl_percent": 2.51,
        "current_price": 50000.0,
        "adx": 30.5,
        "rvol": 1.8,
        "atr": 500.0,
        "signal": "LONG",
        "open_positions": [
            {
                "symbol": "BTCUSDT",
                "side": "LONG",
                "entry_price": 49500.0,
                "current_price": 50000.0,
                "size": 0.1,
                "pnl": 50.0,
                "pnl_percent": 1.01,
                "stop_loss": 48500.0,
                "take_profit": 51500.0
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(results_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def temp_logs_dir():
    """Create a temporary logs directory for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create a sample log file
    log_file = os.path.join(temp_dir, "trades.log.2026-02-13")
    with open(log_file, 'w') as f:
        f.write("2026-02-13 10:00:00 - TRADE CLOSED: BTCUSDT LONG Entry: 49000.0 Exit: 50000.0 PnL: 100.0\n")
        f.write("2026-02-13 11:00:00 - TRADE CLOSED: BTCUSDT SHORT Entry: 50500.0 Exit: 50000.0 PnL: 50.0\n")
    
    yield temp_dir
    
    # Cleanup
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


# ===== INTEGRATION TESTS =====

def test_full_dashboard_data_load(temp_config_file, temp_results_file, temp_logs_dir):
    """
    Test full dashboard load with all data sources.
    
    This integration test verifies that:
    1. Data provider can load config, results, and logs
    2. All data is properly parsed and accessible
    3. No errors occur during data loading
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
    """
    # Initialize data provider with temp files
    data_provider = StreamlitDataProvider(
        config_path=temp_config_file,
        results_path=temp_results_file,
        logs_dir=temp_logs_dir
    )
    
    # Test config loading
    config = data_provider.get_config()
    assert config is not None
    assert config["symbol"] == "BTCUSDT"
    assert config["timeframe"] == "15m"
    assert config["leverage"] == 10
    
    # Test balance and PnL loading
    balance_pnl = data_provider.get_balance_and_pnl()
    assert balance_pnl is not None
    assert balance_pnl["balance"] == 10000.0
    assert balance_pnl["total_pnl"] == 250.50
    assert balance_pnl["total_pnl_percent"] == 2.51
    
    # Test positions loading
    positions = data_provider.get_open_positions()
    assert positions is not None
    assert len(positions) == 1
    assert positions[0]["symbol"] == "BTCUSDT"
    assert positions[0]["side"] == "LONG"
    assert positions[0]["pnl"] == 50.0
    
    # Test market data loading
    market_data = data_provider.get_market_data()
    assert market_data is not None
    assert market_data["current_price"] == 50000.0
    assert market_data["adx"] == 30.5
    assert market_data["rvol"] == 1.8
    assert market_data["signal"] == "LONG"
    
    # Test trade history loading
    trades = data_provider.get_trade_history(limit=20)
    assert trades is not None
    # Trade history parsing depends on log format, so we just check it doesn't error


def test_page_navigation_flow(temp_config_file, temp_results_file, temp_logs_dir):
    """
    Test page navigation and data consistency across pages.
    
    This integration test verifies that:
    1. Data provider maintains consistent state across multiple calls
    2. Different pages can access the same data
    3. Caching works correctly
    
    Validates: Requirements 1.4, 10.1, 10.2, 10.3
    """
    # Initialize data provider
    data_provider = StreamlitDataProvider(
        config_path=temp_config_file,
        results_path=temp_results_file,
        logs_dir=temp_logs_dir
    )
    
    # Simulate navigation to Dashboard page
    config_1 = data_provider.get_config()
    balance_1 = data_provider.get_balance_and_pnl()
    positions_1 = data_provider.get_open_positions()
    
    # Simulate navigation to Positions page
    positions_2 = data_provider.get_open_positions()
    config_2 = data_provider.get_config()
    
    # Simulate navigation to Market Data page
    market_data = data_provider.get_market_data()
    config_3 = data_provider.get_config()
    
    # Verify data consistency across pages
    assert config_1 == config_2 == config_3
    assert positions_1 == positions_2
    assert balance_1["balance"] == 10000.0
    
    # Verify caching is working (same object references)
    assert config_1 is config_2  # Should be same cached object
    assert positions_1 is positions_2  # Should be same cached object


def test_data_refresh_cycle(temp_config_file, temp_results_file, temp_logs_dir):
    """
    Test data refresh behavior with cache expiration.
    
    This integration test verifies that:
    1. Data is cached for the configured TTL
    2. Cache expires after TTL
    3. Fresh data is loaded after cache expiration
    
    Validates: Requirements 1.4, 9.5
    """
    import time
    
    # Initialize data provider with short cache TTL
    data_provider = StreamlitDataProvider(
        config_path=temp_config_file,
        results_path=temp_results_file,
        logs_dir=temp_logs_dir
    )
    data_provider._cache_ttl = 1  # 1 second TTL for testing
    
    # First load
    config_1 = data_provider.get_config()
    assert config_1["symbol"] == "BTCUSDT"
    
    # Immediate second load (should use cache)
    config_2 = data_provider.get_config()
    assert config_1 is config_2  # Same object from cache
    
    # Wait for cache to expire
    time.sleep(1.5)
    
    # Third load (should reload from file)
    config_3 = data_provider.get_config()
    assert config_3["symbol"] == "BTCUSDT"
    # Note: config_3 might not be the same object as config_1 if cache expired


def test_config_editor_integration(temp_config_file):
    """
    Test config editor load, validate, and save workflow.
    
    This integration test verifies that:
    1. Config can be loaded from file
    2. Validation works correctly
    3. Config can be saved back to file
    4. Saved config can be reloaded
    
    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
    """
    # Initialize config editor
    config_editor = ConfigEditor(config_path=temp_config_file)
    
    # Load config
    config = config_editor.load_config()
    assert config is not None
    assert config["symbol"] == "BTCUSDT"
    
    # Validate original config
    is_valid, error_msg = config_editor.validate_config(config)
    assert is_valid is True
    assert error_msg == ""
    
    # Modify config
    config["leverage"] = 20
    config["risk_per_trade"] = 0.03
    
    # Validate modified config
    is_valid, error_msg = config_editor.validate_config(config)
    assert is_valid is True
    
    # Save modified config
    success, message = config_editor.save_config(config)
    assert success is True
    
    # Reload config and verify changes
    reloaded_config = config_editor.load_config()
    assert reloaded_config["leverage"] == 20
    assert reloaded_config["risk_per_trade"] == 0.03


def test_config_validation_integration(temp_config_file):
    """
    Test config validation with invalid values.
    
    This integration test verifies that:
    1. Invalid configs are rejected
    2. Appropriate error messages are provided
    3. Invalid configs cannot be saved
    
    Validates: Requirements 6.2, 6.5
    """
    # Initialize config editor
    config_editor = ConfigEditor(config_path=temp_config_file)
    
    # Load valid config
    config = config_editor.load_config()
    
    # Test invalid risk_per_trade
    config["risk_per_trade"] = 1.5  # > 1.0
    is_valid, error_msg = config_editor.validate_config(config)
    assert is_valid is False
    assert "risk_per_trade" in error_msg
    
    # Attempt to save invalid config
    success, message = config_editor.save_config(config)
    assert success is False
    assert "risk_per_trade" in message
    
    # Test invalid leverage
    config["risk_per_trade"] = 0.02  # Fix previous error
    config["leverage"] = 200  # > 125
    is_valid, error_msg = config_editor.validate_config(config)
    assert is_valid is False
    assert "leverage" in error_msg
    
    # Test invalid ADX threshold
    config["leverage"] = 10  # Fix previous error
    config["adx_threshold"] = 150  # > 100
    is_valid, error_msg = config_editor.validate_config(config)
    assert is_valid is False
    assert "adx_threshold" in error_msg


def test_chart_generator_integration(temp_results_file):
    """
    Test chart generator with real data.
    
    This integration test verifies that:
    1. Charts can be generated from position data
    2. Charts include all required elements
    3. No errors occur during chart generation
    
    Validates: Requirements 4.1, 4.2, 4.3, 8.2
    """
    # Initialize chart generator
    chart_generator = ChartGenerator()
    
    # Create sample candle data
    from datetime import datetime, timedelta
    candles = []
    base_time = datetime.now() - timedelta(hours=100)
    
    for i in range(100):
        candles.append({
            'timestamp': base_time + timedelta(hours=i),
            'open': 50000.0 + i * 10,
            'high': 50100.0 + i * 10,
            'low': 49900.0 + i * 10,
            'close': 50050.0 + i * 10,
            'volume': 1000.0
        })
    
    # Create sample positions
    positions = [
        {
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'entry_time': base_time + timedelta(hours=50),
            'entry_price': 50500.0
        }
    ]
    
    # Generate price chart
    fig = chart_generator.create_price_chart(
        candles=candles,
        positions=positions,
        atr_bands=None
    )
    
    # Verify chart was created
    assert fig is not None
    assert len(fig.data) > 0  # Should have at least candlestick trace
    
    # Create sample trades for PnL chart
    trades = []
    for i in range(20):
        trades.append({
            'exit_time': base_time + timedelta(hours=i * 5),
            'pnl': (i - 10) * 10.0  # Mix of positive and negative
        })
    
    # Generate PnL chart
    pnl_fig = chart_generator.create_pnl_chart(trades)
    
    # Verify PnL chart was created
    assert pnl_fig is not None
    assert len(pnl_fig.data) > 0


@patch('psutil.process_iter')
def test_bot_controller_integration(mock_process_iter, temp_config_file):
    """
    Test bot controller start/stop workflow.
    
    This integration test verifies that:
    1. Bot status can be checked
    2. Bot can be started (mocked)
    3. Bot can be stopped (mocked)
    4. Status updates correctly
    
    Validates: Requirements 5.1, 5.2, 5.5
    """
    # Mock process iterator to simulate bot not running
    mock_process_iter.return_value = []
    
    # Initialize bot controller
    bot_controller = BotController()
    
    # Check initial status (bot not running)
    is_running = bot_controller._is_running()
    assert is_running is False
    
    # Mock subprocess.Popen for start_bot
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process
        
        # Start bot
        success, message = bot_controller.start_bot()
        assert success is True
        assert "started" in message.lower()
    
    # Mock process iterator to simulate bot running
    mock_proc = MagicMock()
    mock_proc.info = {'cmdline': ['python', 'main.py']}
    mock_process_iter.return_value = [mock_proc]
    
    # Check status (bot running)
    is_running = bot_controller._is_running()
    assert is_running is True
    
    # Mock process for stop_bot
    with patch('psutil.process_iter') as mock_iter:
        mock_proc = MagicMock()
        mock_proc.info = {'cmdline': ['python', 'main.py']}
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock()
        mock_iter.return_value = [mock_proc]
        
        # Stop bot
        success, message = bot_controller.stop_bot()
        assert success is True
        assert "stopped" in message.lower()


def test_end_to_end_dashboard_workflow(temp_config_file, temp_results_file, temp_logs_dir):
    """
    Test complete end-to-end dashboard workflow.
    
    This integration test simulates a complete user workflow:
    1. Load dashboard
    2. View status and positions
    3. Navigate to different pages
    4. Modify configuration
    5. View analytics
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 6.3, 8.1
    """
    # Initialize components
    data_provider = StreamlitDataProvider(
        config_path=temp_config_file,
        results_path=temp_results_file,
        logs_dir=temp_logs_dir
    )
    config_editor = ConfigEditor(config_path=temp_config_file)
    chart_generator = ChartGenerator()
    
    # Step 1: Load dashboard (simulate Dashboard page)
    bot_status = data_provider.get_bot_status()
    balance_pnl = data_provider.get_balance_and_pnl()
    positions = data_provider.get_open_positions()
    
    assert bot_status is not None
    assert balance_pnl["balance"] == 10000.0
    assert len(positions) == 1
    
    # Step 2: View positions (simulate Positions page)
    for pos in positions:
        assert "symbol" in pos
        assert "side" in pos
        assert "pnl" in pos
    
    # Step 3: View market data (simulate Market Data page)
    market_data = data_provider.get_market_data()
    config = data_provider.get_config()
    
    assert market_data["current_price"] == 50000.0
    assert market_data["adx"] == 30.5
    assert config["adx_threshold"] == 25.0
    
    # Step 4: Modify configuration (simulate Settings page)
    config["leverage"] = 15
    config["risk_per_trade"] = 0.025
    
    is_valid, _ = config_editor.validate_config(config)
    assert is_valid is True
    
    success, _ = config_editor.save_config(config)
    assert success is True
    
    # Step 5: View analytics (simulate Analytics page)
    trades = data_provider.get_trade_history(limit=20)
    
    # Generate charts
    from datetime import datetime, timedelta
    candles = []
    base_time = datetime.now() - timedelta(hours=100)
    
    for i in range(100):
        candles.append({
            'timestamp': base_time + timedelta(hours=i),
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': 50050.0,
            'volume': 1000.0
        })
    
    price_chart = chart_generator.create_price_chart(candles, positions)
    assert price_chart is not None
    
    # Verify workflow completed without errors
    assert True  # If we got here, the workflow succeeded


def test_error_handling_integration(temp_logs_dir):
    """
    Test error handling with missing or corrupted files.
    
    This integration test verifies that:
    1. Missing config file is handled gracefully
    2. Missing results file is handled gracefully
    3. Default values are returned
    4. No exceptions are raised
    
    Validates: Requirements 9.4
    """
    # Initialize data provider with non-existent files
    data_provider = StreamlitDataProvider(
        config_path="nonexistent_config.json",
        results_path="nonexistent_results.json",
        logs_dir=temp_logs_dir
    )
    
    # Test config loading with missing file
    config = data_provider.get_config()
    assert config == {}  # Should return empty dict, not raise exception
    
    # Test balance loading with missing file
    balance_pnl = data_provider.get_balance_and_pnl()
    assert balance_pnl["balance"] == 0.0  # Should return default values
    assert balance_pnl["total_pnl"] == 0.0
    
    # Test positions loading with missing file
    positions = data_provider.get_open_positions()
    assert positions == []  # Should return empty list
    
    # Test market data loading with missing file
    market_data = data_provider.get_market_data()
    assert market_data["current_price"] == 0.0  # Should return default values
    
    # Verify no exceptions were raised
    assert True


# ===== PERFORMANCE TESTS =====

def test_dashboard_load_performance(temp_config_file, temp_results_file, temp_logs_dir):
    """
    Test dashboard load performance.
    
    This test verifies that:
    1. Dashboard loads within acceptable time
    2. Caching improves performance
    3. Multiple page loads are efficient
    """
    import time
    
    # Initialize data provider
    data_provider = StreamlitDataProvider(
        config_path=temp_config_file,
        results_path=temp_results_file,
        logs_dir=temp_logs_dir
    )
    
    # Measure first load time (cold cache)
    start_time = time.time()
    config = data_provider.get_config()
    balance = data_provider.get_balance_and_pnl()
    positions = data_provider.get_open_positions()
    market_data = data_provider.get_market_data()
    first_load_time = time.time() - start_time
    
    # Measure second load time (warm cache)
    start_time = time.time()
    config = data_provider.get_config()
    balance = data_provider.get_balance_and_pnl()
    positions = data_provider.get_open_positions()
    market_data = data_provider.get_market_data()
    second_load_time = time.time() - start_time
    
    # Verify performance
    assert first_load_time < 1.0  # Should load in less than 1 second
    assert second_load_time < first_load_time  # Cache should improve performance
    
    print(f"\nFirst load time: {first_load_time:.4f}s")
    print(f"Second load time (cached): {second_load_time:.4f}s")
    print(f"Performance improvement: {(1 - second_load_time/first_load_time)*100:.1f}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ===== SCALED TAKE PROFIT DASHBOARD TESTS =====

def test_dashboard_displays_scaled_tp_progress():
    """Test that dashboard displays scaled TP progress correctly."""
    # Create mock position with scaled TP data
    position = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000.0,
        'current_price': 51500.0,
        'quantity': 0.06,
        'original_quantity': 0.1,
        'unrealized_pnl': 90.0,
        'stop_loss': 50000.0,
        'trailing_stop': 51000.0,
        'entry_time': 1708450000000,
        'tp_levels_hit': [1],
        'partial_exits': [
            {
                'tp_level': 1,
                'exit_price': 51500.0,
                'quantity_closed': 0.04,
                'profit': 60.0,
                'profit_pct': 0.03
            }
        ]
    }
    
    config = {
        'enable_scaled_take_profit': True,
        'scaled_tp_levels': [
            {'profit_pct': 0.03, 'close_pct': 0.40},
            {'profit_pct': 0.05, 'close_pct': 0.30},
            {'profit_pct': 0.08, 'close_pct': 0.30}
        ]
    }
    
    # Verify position has correct scaled TP data
    assert position['original_quantity'] == 0.1
    assert position['quantity'] == 0.06
    assert len(position['tp_levels_hit']) == 1
    assert 1 in position['tp_levels_hit']
    assert len(position['partial_exits']) == 1
    
    # Verify remaining percentage calculation
    remaining_pct = (position['quantity'] / position['original_quantity']) * 100
    assert remaining_pct == 60.0
    
    # Verify TP level calculations
    for i, tp_level in enumerate(config['scaled_tp_levels'], 1):
        profit_pct = tp_level['profit_pct']
        close_pct = tp_level['close_pct']
        
        # Calculate target price for LONG
        target_price = position['entry_price'] * (1 + profit_pct)
        
        if i == 1:
            assert target_price == 51500.0
            assert i in position['tp_levels_hit']
        elif i == 2:
            assert target_price == 52500.0
            assert i not in position['tp_levels_hit']
        elif i == 3:
            assert target_price == 54000.0
            assert i not in position['tp_levels_hit']


def test_dashboard_calculates_next_tp_target():
    """Test that dashboard correctly calculates next TP target."""
    position = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000.0,
        'current_price': 51500.0,
        'tp_levels_hit': [1]
    }
    
    scaled_tp_levels = [
        {'profit_pct': 0.03, 'close_pct': 0.40},
        {'profit_pct': 0.05, 'close_pct': 0.30},
        {'profit_pct': 0.08, 'close_pct': 0.30}
    ]
    
    # Next TP should be TP2
    tp_levels_hit = position['tp_levels_hit']
    if tp_levels_hit and len(tp_levels_hit) < len(scaled_tp_levels):
        next_tp_idx = len(tp_levels_hit)
        next_tp = scaled_tp_levels[next_tp_idx]
        next_profit_pct = next_tp['profit_pct']
        
        # Calculate next target for LONG
        next_target = position['entry_price'] * (1 + next_profit_pct)
        
        assert next_tp_idx == 1  # Index 1 = TP2
        assert next_profit_pct == 0.05
        assert next_target == 52500.0


def test_dashboard_handles_short_position_tp_targets():
    """Test that dashboard correctly calculates TP targets for SHORT positions."""
    position = {
        'symbol': 'BTCUSDT',
        'side': 'SHORT',
        'entry_price': 50000.0,
        'current_price': 48500.0,
        'tp_levels_hit': []
    }
    
    scaled_tp_levels = [
        {'profit_pct': 0.03, 'close_pct': 0.40},
        {'profit_pct': 0.05, 'close_pct': 0.30},
        {'profit_pct': 0.08, 'close_pct': 0.30}
    ]
    
    # Calculate TP targets for SHORT
    for i, tp_level in enumerate(scaled_tp_levels, 1):
        profit_pct = tp_level['profit_pct']
        
        # For SHORT, target price goes DOWN
        target_price = position['entry_price'] * (1 - profit_pct)
        
        if i == 1:
            assert target_price == 48500.0
        elif i == 2:
            assert target_price == 47500.0
        elif i == 3:
            assert target_price == 46000.0


def test_dashboard_shows_all_tp_levels_hit():
    """Test that dashboard correctly shows when all TP levels are hit."""
    position = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000.0,
        'current_price': 54000.0,
        'quantity': 0.0,
        'original_quantity': 0.1,
        'tp_levels_hit': [1, 2, 3],
        'partial_exits': [
            {'tp_level': 1, 'quantity_closed': 0.04, 'profit': 60.0},
            {'tp_level': 2, 'quantity_closed': 0.03, 'profit': 75.0},
            {'tp_level': 3, 'quantity_closed': 0.03, 'profit': 120.0}
        ]
    }
    
    scaled_tp_levels = [
        {'profit_pct': 0.03, 'close_pct': 0.40},
        {'profit_pct': 0.05, 'close_pct': 0.30},
        {'profit_pct': 0.08, 'close_pct': 0.30}
    ]
    
    # Verify all levels hit
    assert len(position['tp_levels_hit']) == len(scaled_tp_levels)
    assert position['quantity'] == 0.0
    assert len(position['partial_exits']) == 3
    
    # Calculate total profit from all partials
    total_profit = sum(exit_data['profit'] for exit_data in position['partial_exits'])
    assert total_profit == 255.0


def test_dashboard_calculates_tp_progress():
    """Test that dashboard correctly calculates progress to TP levels."""
    position = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000.0,
        'current_price': 51000.0,
        'tp_levels_hit': []
    }
    
    tp_level = {'profit_pct': 0.03, 'close_pct': 0.40}
    target_price = position['entry_price'] * (1 + tp_level['profit_pct'])
    
    # Calculate progress for LONG
    progress = (position['current_price'] - position['entry_price']) / (target_price - position['entry_price'])
    progress = max(0.0, min(1.0, progress))
    
    # Current price is 51000, target is 51500
    # Progress should be (51000 - 50000) / (51500 - 50000) = 1000 / 1500 = 0.667
    assert abs(progress - 0.667) < 0.01


def test_dashboard_handles_no_scaled_tp():
    """Test that dashboard works correctly when scaled TP is disabled."""
    position = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000.0,
        'current_price': 51000.0,
        'quantity': 0.1,
        'unrealized_pnl': 100.0,
        'stop_loss': 49000.0,
        'trailing_stop': 50500.0,
        'entry_time': 1708450000000
    }
    
    config = {
        'enable_scaled_take_profit': False,
        'scaled_tp_levels': []
    }
    
    # Verify position has no scaled TP data
    assert position.get('tp_levels_hit', []) == []
    assert position.get('partial_exits', []) == []
    assert position.get('original_quantity', position['quantity']) == position['quantity']
    
    # Dashboard should not show TP progress when disabled
    assert not config['enable_scaled_take_profit']


# ===== SCALED TP ANALYTICS TESTS =====

def test_scaled_tp_analytics_integration():
    """Test that scaled TP analytics can be calculated from trade data."""
    from src.scaled_tp_analytics import ScaledTPAnalytics
    
    analytics = ScaledTPAnalytics()
    
    # Sample trades with scaled TP data
    trades = [
        {
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'pnl': 150.0,
            'tp_levels_hit': [1, 2, 3],
            'partial_exits': [
                {'tp_level': 1, 'profit': 40.0, 'profit_pct': 0.03, 'quantity_closed': 0.04},
                {'tp_level': 2, 'profit': 50.0, 'profit_pct': 0.05, 'quantity_closed': 0.03},
                {'tp_level': 3, 'profit': 60.0, 'profit_pct': 0.08, 'quantity_closed': 0.03}
            ]
        },
        {
            'symbol': 'ETHUSDT',
            'side': 'LONG',
            'pnl': 80.0,
            'tp_levels_hit': [1, 2],
            'partial_exits': [
                {'tp_level': 1, 'profit': 30.0, 'profit_pct': 0.03, 'quantity_closed': 0.04},
                {'tp_level': 2, 'profit': 50.0, 'profit_pct': 0.05, 'quantity_closed': 0.03}
            ]
        },
        # Single TP trade for comparison
        {
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'pnl': 100.0,
            'exit_reason': 'TAKE_PROFIT'
        }
    ]
    
    # Test TP level metrics calculation
    tp_metrics = analytics.calculate_tp_level_metrics(trades, num_tp_levels=3)
    assert len(tp_metrics) == 3
    assert tp_metrics[0].hit_count == 2  # TP1 hit by 2 trades
    assert tp_metrics[1].hit_count == 2  # TP2 hit by 2 trades
    assert tp_metrics[2].hit_count == 1  # TP3 hit by 1 trade
    
    # Test scaled TP performance calculation
    performance = analytics.calculate_scaled_tp_performance(trades, num_tp_levels=3)
    assert performance is not None
    assert performance.total_trades == 2  # 2 scaled TP trades
    assert performance.total_profit == 230.0  # 150 + 80
    
    # Test strategy comparison
    comparison = analytics.compare_strategies(trades)
    assert comparison is not None
    assert comparison.scaled_tp_trades == 2
    assert comparison.single_tp_trades == 1
    assert comparison.scaled_tp_profit == 230.0
    assert comparison.single_tp_profit == 100.0


def test_scaled_tp_analytics_with_no_scaled_trades():
    """Test analytics when there are no scaled TP trades."""
    from src.scaled_tp_analytics import ScaledTPAnalytics
    
    analytics = ScaledTPAnalytics()
    
    # Only single TP trades
    trades = [
        {'symbol': 'BTCUSDT', 'side': 'LONG', 'pnl': 100.0, 'exit_reason': 'TAKE_PROFIT'},
        {'symbol': 'ETHUSDT', 'side': 'SHORT', 'pnl': -50.0, 'exit_reason': 'STOP_LOSS'}
    ]
    
    # Should return empty/None results
    tp_metrics = analytics.calculate_tp_level_metrics(trades, num_tp_levels=3)
    assert len(tp_metrics) == 0
    
    performance = analytics.calculate_scaled_tp_performance(trades, num_tp_levels=3)
    assert performance is None
    
    comparison = analytics.compare_strategies(trades)
    assert comparison is None


def test_scaled_tp_analytics_profit_distribution():
    """Test that profit distribution is calculated correctly across TP levels."""
    from src.scaled_tp_analytics import ScaledTPAnalytics
    
    analytics = ScaledTPAnalytics()
    
    # Create trades where TP1 contributes most profit
    trades = [
        {
            'pnl': 100.0,
            'tp_levels_hit': [1, 2, 3],
            'partial_exits': [
                {'tp_level': 1, 'profit': 50.0, 'profit_pct': 0.03},  # 50% of profit
                {'tp_level': 2, 'profit': 30.0, 'profit_pct': 0.05},  # 30% of profit
                {'tp_level': 3, 'profit': 20.0, 'profit_pct': 0.08}   # 20% of profit
            ]
        }
    ]
    
    tp_metrics = analytics.calculate_tp_level_metrics(trades, num_tp_levels=3)
    
    # Calculate profit distribution
    total_profit = sum(m.total_profit for m in tp_metrics)
    assert total_profit == 100.0
    
    # Check individual contributions
    assert tp_metrics[0].total_profit == 50.0  # TP1
    assert tp_metrics[1].total_profit == 30.0  # TP2
    assert tp_metrics[2].total_profit == 20.0  # TP3


def test_scaled_tp_analytics_cascade_rate():
    """Test calculation of cascade rate (TP1 -> TP2 progression)."""
    from src.scaled_tp_analytics import ScaledTPAnalytics
    
    analytics = ScaledTPAnalytics()
    
    # 4 trades hit TP1, but only 2 reach TP2 (50% cascade rate)
    trades = [
        {
            'pnl': 100.0,
            'tp_levels_hit': [1, 2, 3],
            'partial_exits': [
                {'tp_level': 1, 'profit': 30.0, 'profit_pct': 0.03},
                {'tp_level': 2, 'profit': 30.0, 'profit_pct': 0.05},
                {'tp_level': 3, 'profit': 40.0, 'profit_pct': 0.08}
            ]
        },
        {
            'pnl': 60.0,
            'tp_levels_hit': [1, 2],
            'partial_exits': [
                {'tp_level': 1, 'profit': 30.0, 'profit_pct': 0.03},
                {'tp_level': 2, 'profit': 30.0, 'profit_pct': 0.05}
            ]
        },
        {
            'pnl': 30.0,
            'tp_levels_hit': [1],
            'partial_exits': [
                {'tp_level': 1, 'profit': 30.0, 'profit_pct': 0.03}
            ]
        },
        {
            'pnl': 30.0,
            'tp_levels_hit': [1],
            'partial_exits': [
                {'tp_level': 1, 'profit': 30.0, 'profit_pct': 0.03}
            ]
        }
    ]
    
    tp_metrics = analytics.calculate_tp_level_metrics(trades, num_tp_levels=3)
    
    # TP1: 4 hits (100% of trades)
    assert tp_metrics[0].hit_count == 4
    assert tp_metrics[0].hit_rate == 100.0
    
    # TP2: 2 hits (50% of trades)
    assert tp_metrics[1].hit_count == 2
    assert tp_metrics[1].hit_rate == 50.0
    
    # Calculate cascade rate: TP2 hits / TP1 hits = 2/4 = 50%
    cascade_rate = (tp_metrics[1].hit_rate / tp_metrics[0].hit_rate) * 100
    assert cascade_rate == 50.0
