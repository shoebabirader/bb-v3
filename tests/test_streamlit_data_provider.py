"""Property-based and unit tests for Streamlit Data Provider."""

import json
import os
import tempfile
import time
from pathlib import Path
import pytest
from hypothesis import given, strategies as st, settings
from src.streamlit_data_provider import StreamlitDataProvider


# Feature: streamlit-ui, Property 16: Graceful File Handling
@given(
    file_scenario=st.sampled_from([
        "missing_config",
        "missing_results",
        "corrupted_config",
        "corrupted_results",
        "empty_config",
        "empty_results"
    ])
)
@settings(deadline=None)
def test_graceful_file_handling(file_scenario):
    """For any missing or corrupted data file, the Data_Provider must return 
    default values without raising exceptions.
    
    Property 16: Graceful File Handling
    Validates: Requirements 9.4
    """
    # Create temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, "config.json")
        results_path = os.path.join(temp_dir, "results.json")
        logs_dir = os.path.join(temp_dir, "logs")
        
        # Set up the scenario
        if file_scenario == "missing_config":
            # Don't create config file
            # Create valid results file
            with open(results_path, 'w') as f:
                json.dump({"balance": 1000.0}, f)
        
        elif file_scenario == "missing_results":
            # Create valid config file
            with open(config_path, 'w') as f:
                json.dump({"symbol": "BTCUSDT"}, f)
            # Don't create results file
        
        elif file_scenario == "corrupted_config":
            # Create corrupted config file
            with open(config_path, 'w') as f:
                f.write("{invalid json content")
            # Create valid results file
            with open(results_path, 'w') as f:
                json.dump({"balance": 1000.0}, f)
        
        elif file_scenario == "corrupted_results":
            # Create valid config file
            with open(config_path, 'w') as f:
                json.dump({"symbol": "BTCUSDT"}, f)
            # Create corrupted results file
            with open(results_path, 'w') as f:
                f.write("not valid json at all")
        
        elif file_scenario == "empty_config":
            # Create empty config file
            with open(config_path, 'w') as f:
                f.write("")
            # Create valid results file
            with open(results_path, 'w') as f:
                json.dump({"balance": 1000.0}, f)
        
        elif file_scenario == "empty_results":
            # Create valid config file
            with open(config_path, 'w') as f:
                json.dump({"symbol": "BTCUSDT"}, f)
            # Create empty results file
            with open(results_path, 'w') as f:
                f.write("")
        
        # Create data provider
        provider = StreamlitDataProvider(
            config_path=config_path,
            results_path=results_path,
            logs_dir=logs_dir
        )
        
        # All methods should return default values without raising exceptions
        try:
            config = provider.get_config()
            assert isinstance(config, dict), "get_config() should return a dict"
            
            balance_pnl = provider.get_balance_and_pnl()
            assert isinstance(balance_pnl, dict), "get_balance_and_pnl() should return a dict"
            assert "balance" in balance_pnl
            assert "total_pnl" in balance_pnl
            assert "total_pnl_percent" in balance_pnl
            
            positions = provider.get_open_positions()
            assert isinstance(positions, list), "get_open_positions() should return a list"
            
            market_data = provider.get_market_data()
            assert isinstance(market_data, dict), "get_market_data() should return a dict"
            assert "current_price" in market_data
            assert "adx" in market_data
            assert "rvol" in market_data
            assert "atr" in market_data
            assert "signal" in market_data
            
            trade_history = provider.get_trade_history()
            assert isinstance(trade_history, list), "get_trade_history() should return a list"
            
            bot_status = provider.get_bot_status()
            assert isinstance(bot_status, dict), "get_bot_status() should return a dict"
            assert "is_running" in bot_status
            assert "status" in bot_status
            
        except Exception as e:
            pytest.fail(f"Data provider raised exception for scenario '{file_scenario}': {e}")



# ===== UNIT TESTS =====

class TestDataProviderWithSampleFiles:
    """Unit tests for data provider with sample JSON files.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    
    def test_get_config_with_valid_file(self):
        """Test loading configuration from valid JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            config_data = {
                "symbol": "BTCUSDT",
                "timeframe_entry": "15m",
                "risk_per_trade": 0.01
            }
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f)
            
            provider = StreamlitDataProvider(config_path=config_path)
            config = provider.get_config()
            
            assert config["symbol"] == "BTCUSDT"
            assert config["timeframe_entry"] == "15m"
            assert config["risk_per_trade"] == 0.01
    
    def test_get_balance_and_pnl_with_valid_file(self):
        """Test loading balance and PnL from valid results file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            results_path = os.path.join(temp_dir, "results.json")
            results_data = {
                "balance": 10000.0,
                "total_pnl": 1500.0,
                "total_pnl_percent": 15.0
            }
            
            with open(results_path, 'w') as f:
                json.dump(results_data, f)
            
            provider = StreamlitDataProvider(results_path=results_path)
            balance_pnl = provider.get_balance_and_pnl()
            
            assert balance_pnl["balance"] == 10000.0
            assert balance_pnl["total_pnl"] == 1500.0
            assert balance_pnl["total_pnl_percent"] == 15.0
    
    def test_get_open_positions_with_valid_file(self):
        """Test loading open positions from valid results file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            results_path = os.path.join(temp_dir, "results.json")
            results_data = {
                "open_positions": [
                    {
                        "symbol": "BTCUSDT",
                        "side": "LONG",
                        "entry_price": 50000.0,
                        "quantity": 0.1
                    },
                    {
                        "symbol": "ETHUSDT",
                        "side": "SHORT",
                        "entry_price": 3000.0,
                        "quantity": 1.0
                    }
                ]
            }
            
            with open(results_path, 'w') as f:
                json.dump(results_data, f)
            
            provider = StreamlitDataProvider(results_path=results_path)
            positions = provider.get_open_positions()
            
            assert len(positions) == 2
            assert positions[0]["symbol"] == "BTCUSDT"
            assert positions[0]["side"] == "LONG"
            assert positions[1]["symbol"] == "ETHUSDT"
            assert positions[1]["side"] == "SHORT"
    
    def test_get_market_data_with_valid_file(self):
        """Test loading market data from valid results file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            results_path = os.path.join(temp_dir, "results.json")
            results_data = {
                "current_price": 50000.0,
                "adx": 35.5,
                "rvol": 1.8,
                "atr": 500.0,
                "signal": "LONG"
            }
            
            with open(results_path, 'w') as f:
                json.dump(results_data, f)
            
            provider = StreamlitDataProvider(results_path=results_path)
            market_data = provider.get_market_data()
            
            assert market_data["current_price"] == 50000.0
            assert market_data["adx"] == 35.5
            assert market_data["rvol"] == 1.8
            assert market_data["atr"] == 500.0
            assert market_data["signal"] == "LONG"


class TestDataProviderWithMissingFiles:
    """Unit tests for data provider with missing files.
    
    Validates: Requirements 9.4
    """
    
    def test_get_config_with_missing_file(self):
        """Test that missing config file returns empty dict."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "nonexistent.json")
            provider = StreamlitDataProvider(config_path=config_path)
            config = provider.get_config()
            
            assert isinstance(config, dict)
            assert len(config) == 0
    
    def test_get_balance_and_pnl_with_missing_file(self):
        """Test that missing results file returns default values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            results_path = os.path.join(temp_dir, "nonexistent.json")
            provider = StreamlitDataProvider(results_path=results_path)
            balance_pnl = provider.get_balance_and_pnl()
            
            assert balance_pnl["balance"] == 0.0
            assert balance_pnl["total_pnl"] == 0.0
            assert balance_pnl["total_pnl_percent"] == 0.0
    
    def test_get_open_positions_with_missing_file(self):
        """Test that missing results file returns empty list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            results_path = os.path.join(temp_dir, "nonexistent.json")
            provider = StreamlitDataProvider(results_path=results_path)
            positions = provider.get_open_positions()
            
            assert isinstance(positions, list)
            assert len(positions) == 0
    
    def test_get_trade_history_with_missing_logs(self):
        """Test that missing log directory returns empty list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "nonexistent_logs")
            provider = StreamlitDataProvider(logs_dir=logs_dir)
            trades = provider.get_trade_history()
            
            assert isinstance(trades, list)
            assert len(trades) == 0


class TestDataProviderCaching:
    """Unit tests for data provider caching behavior.
    
    Validates: Requirements 9.5
    """
    
    def test_cache_returns_same_data_within_ttl(self):
        """Test that cache returns same data within TTL period."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            config_data = {"symbol": "BTCUSDT", "version": 1}
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f)
            
            provider = StreamlitDataProvider(config_path=config_path)
            
            # First read
            config1 = provider.get_config()
            assert config1["version"] == 1
            
            # Modify file
            config_data["version"] = 2
            with open(config_path, 'w') as f:
                json.dump(config_data, f)
            
            # Second read within TTL should return cached data
            config2 = provider.get_config()
            assert config2["version"] == 1  # Still cached
    
    def test_cache_refreshes_after_ttl(self):
        """Test that cache refreshes after TTL expires."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            config_data = {"symbol": "BTCUSDT", "version": 1}
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f)
            
            provider = StreamlitDataProvider(config_path=config_path)
            provider._cache_ttl = 1  # Set TTL to 1 second for testing
            
            # First read
            config1 = provider.get_config()
            assert config1["version"] == 1
            
            # Modify file
            config_data["version"] = 2
            with open(config_path, 'w') as f:
                json.dump(config_data, f)
            
            # Wait for TTL to expire
            time.sleep(1.1)
            
            # Second read after TTL should return new data
            config2 = provider.get_config()
            assert config2["version"] == 2  # Cache refreshed
    
    def test_different_cache_keys_are_independent(self):
        """Test that different cache keys maintain independent caches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            results_path = os.path.join(temp_dir, "results.json")
            
            config_data = {"symbol": "BTCUSDT"}
            results_data = {"balance": 10000.0}
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f)
            with open(results_path, 'w') as f:
                json.dump(results_data, f)
            
            provider = StreamlitDataProvider(
                config_path=config_path,
                results_path=results_path
            )
            
            # Read both
            config = provider.get_config()
            balance_pnl = provider.get_balance_and_pnl()
            
            assert config["symbol"] == "BTCUSDT"
            assert balance_pnl["balance"] == 10000.0
            
            # Verify both are cached independently
            assert "config" in provider._cache
            assert "results" in provider._cache


class TestTradeHistoryParsing:
    """Unit tests for trade history parsing.
    
    Validates: Requirements 7.1, 9.3
    """
    
    def test_parse_trade_logs_with_valid_entries(self):
        """Test parsing valid trade log entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir)
            
            log_file = os.path.join(logs_dir, "trades.log.2026-02-05")
            log_content = '''2026-02-05 06:54:25 - trading_bot.trades - INFO - TRADE_EXECUTED: {"timestamp": "2026-02-05T06:54:25.875000", "symbol": "XAGUSDT", "side": "LONG", "entry_price": 84.44, "exit_price": 84.44, "quantity": 1.91, "pnl": 0.0, "pnl_percent": 0.0, "entry_time": 1770253337412, "exit_time": 1770254665875, "exit_reason": "PANIC"}
2026-02-05 06:56:31 - trading_bot.trades - INFO - TRADE_EXECUTED: {"timestamp": "2026-02-05T06:56:31.372000", "symbol": "XAGUSDT", "side": "SHORT", "entry_price": 76.616331, "exit_price": 76.8307439, "quantity": 3055.07, "pnl": -655.05, "pnl_percent": -0.28, "entry_time": 1770254773074, "exit_time": 1770254773403, "exit_reason": "TRAILING_STOP"}
'''
            
            with open(log_file, 'w') as f:
                f.write(log_content)
            
            provider = StreamlitDataProvider(logs_dir=logs_dir)
            trades = provider.get_trade_history()
            
            assert len(trades) == 2
            assert trades[0]["symbol"] == "XAGUSDT"
            assert trades[0]["side"] == "LONG"
            assert trades[0]["exit_reason"] == "PANIC"
            assert trades[1]["side"] == "SHORT"
            assert trades[1]["exit_reason"] == "TRAILING_STOP"
    
    def test_parse_trade_logs_with_limit(self):
        """Test that trade history respects limit parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir)
            
            log_file = os.path.join(logs_dir, "trades.log.2026-02-05")
            # Create 30 trade entries
            log_content = ""
            for i in range(30):
                log_content += f'2026-02-05 06:54:{i:02d} - trading_bot.trades - INFO - TRADE_EXECUTED: {{"timestamp": "2026-02-05T06:54:{i:02d}", "symbol": "BTCUSDT", "side": "LONG", "entry_price": 50000.0, "exit_price": 50100.0, "quantity": 0.1, "pnl": 10.0, "pnl_percent": 0.2, "entry_time": 1770253337412, "exit_time": 1770254665875, "exit_reason": "SIGNAL_EXIT"}}\n'
            
            with open(log_file, 'w') as f:
                f.write(log_content)
            
            provider = StreamlitDataProvider(logs_dir=logs_dir)
            
            # Test with limit of 20
            trades = provider.get_trade_history(limit=20)
            assert len(trades) == 20
            
            # Test with limit of 10
            trades = provider.get_trade_history(limit=10)
            assert len(trades) == 10
    
    def test_parse_trade_logs_skips_malformed_entries(self):
        """Test that malformed log entries are skipped gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir)
            
            log_file = os.path.join(logs_dir, "trades.log.2026-02-05")
            log_content = '''2026-02-05 06:54:25 - trading_bot.trades - INFO - TRADE_EXECUTED: {"timestamp": "2026-02-05T06:54:25", "symbol": "XAGUSDT", "side": "LONG", "entry_price": 84.44, "exit_price": 84.44, "quantity": 1.91, "pnl": 0.0, "pnl_percent": 0.0, "entry_time": 1770253337412, "exit_time": 1770254665875, "exit_reason": "PANIC"}
2026-02-05 06:56:31 - trading_bot.trades - INFO - TRADE_EXECUTED: {invalid json here}
2026-02-05 06:57:00 - trading_bot.trades - INFO - TRADE_EXECUTED: {"timestamp": "2026-02-05T06:57:00", "symbol": "BTCUSDT", "side": "SHORT", "entry_price": 50000.0, "exit_price": 49900.0, "quantity": 0.1, "pnl": -10.0, "pnl_percent": -0.2, "entry_time": 1770254773074, "exit_time": 1770254773403, "exit_reason": "STOP_LOSS"}
'''
            
            with open(log_file, 'w') as f:
                f.write(log_content)
            
            provider = StreamlitDataProvider(logs_dir=logs_dir)
            trades = provider.get_trade_history()
            
            # Should have 2 valid trades, skipping the malformed one
            assert len(trades) == 2
            assert trades[0]["symbol"] == "XAGUSDT"
            assert trades[1]["symbol"] == "BTCUSDT"
