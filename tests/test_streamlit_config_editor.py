"""
Tests for Streamlit Config Editor

Tests configuration loading, saving, validation, and round-trip properties.
"""

import json
import os
import tempfile
from hypothesis import given, strategies as st
import pytest

from src.streamlit_config_editor import ConfigEditor


# Strategy for generating valid config values
def valid_config_strategy():
    """Generate valid configuration dictionaries."""
    return st.fixed_dictionaries({
        "symbol": st.sampled_from(["BTCUSDT", "ETHUSDT", "XAUUSDT", "BNBUSDT"]),
        "timeframe": st.sampled_from(["1m", "5m", "15m", "30m", "1h", "4h", "1d"]),
        "risk_per_trade": st.floats(min_value=0.001, max_value=1.0),
        "leverage": st.integers(min_value=1, max_value=125),
        "adx_threshold": st.floats(min_value=0.0, max_value=100.0),
        "rvol_threshold": st.floats(min_value=0.0, max_value=10.0),
        "stop_loss_pct": st.floats(min_value=0.001, max_value=1.0),
        "take_profit_pct": st.floats(min_value=0.001, max_value=10.0),
    })


class TestConfigEditor:
    """Test suite for ConfigEditor."""
    
    def test_load_config_missing_file(self):
        """Test loading config when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "nonexistent.json")
            editor = ConfigEditor(config_path)
            
            config = editor.load_config()
            assert config == {}
    
    def test_load_config_corrupted_file(self):
        """Test loading config with corrupted JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            
            # Write invalid JSON
            with open(config_path, 'w') as f:
                f.write("{ invalid json }")
            
            editor = ConfigEditor(config_path)
            config = editor.load_config()
            assert config == {}
    
    def test_save_config_valid(self):
        """Test saving valid configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            editor = ConfigEditor(config_path)
            
            valid_config = {
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "risk_per_trade": 0.01,
                "leverage": 3,
                "adx_threshold": 20.0,
                "rvol_threshold": 1.2,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.05,
            }
            
            success, message = editor.save_config(valid_config)
            assert success is True
            assert "successfully" in message.lower()
            
            # Verify file was created
            assert os.path.exists(config_path)
    
    def test_save_config_invalid(self):
        """Test saving invalid configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            editor = ConfigEditor(config_path)
            
            invalid_config = {
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "risk_per_trade": 2.0,  # Invalid: > 1.0
                "leverage": 3,
                "adx_threshold": 20.0,
                "rvol_threshold": 1.2,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.05,
            }
            
            success, message = editor.save_config(invalid_config)
            assert success is False
            assert "risk_per_trade" in message.lower()


class TestConfigValidation:
    """Test suite for configuration validation."""
    
    def test_validate_risk_per_trade_invalid(self):
        """Test validation of invalid risk_per_trade."""
        editor = ConfigEditor()
        
        # Test too high
        config = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "risk_per_trade": 1.5,
            "leverage": 3,
            "adx_threshold": 20.0,
            "rvol_threshold": 1.2,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.05,
        }
        is_valid, error = editor.validate_config(config)
        assert is_valid is False
        assert "risk_per_trade" in error
        
        # Test too low
        config["risk_per_trade"] = 0.0
        is_valid, error = editor.validate_config(config)
        assert is_valid is False
        assert "risk_per_trade" in error
    
    def test_validate_leverage_invalid(self):
        """Test validation of invalid leverage."""
        editor = ConfigEditor()
        
        # Test too high
        config = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "risk_per_trade": 0.01,
            "leverage": 200,
            "adx_threshold": 20.0,
            "rvol_threshold": 1.2,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.05,
        }
        is_valid, error = editor.validate_config(config)
        assert is_valid is False
        assert "leverage" in error
        
        # Test too low
        config["leverage"] = 0
        is_valid, error = editor.validate_config(config)
        assert is_valid is False
        assert "leverage" in error
    
    def test_validate_adx_threshold_invalid(self):
        """Test validation of invalid ADX threshold."""
        editor = ConfigEditor()
        
        config = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "risk_per_trade": 0.01,
            "leverage": 3,
            "adx_threshold": 150.0,
            "rvol_threshold": 1.2,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.05,
        }
        is_valid, error = editor.validate_config(config)
        assert is_valid is False
        assert "adx_threshold" in error
    
    def test_validate_timeframe_invalid(self):
        """Test validation of invalid timeframe."""
        editor = ConfigEditor()
        
        config = {
            "symbol": "BTCUSDT",
            "timeframe": "2h",  # Invalid
            "risk_per_trade": 0.01,
            "leverage": 3,
            "adx_threshold": 20.0,
            "rvol_threshold": 1.2,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.05,
        }
        is_valid, error = editor.validate_config(config)
        assert is_valid is False
        assert "timeframe" in error
    
    def test_validate_symbol_empty(self):
        """Test validation of empty symbol."""
        editor = ConfigEditor()
        
        config = {
            "symbol": "",
            "timeframe": "15m",
            "risk_per_trade": 0.01,
            "leverage": 3,
            "adx_threshold": 20.0,
            "rvol_threshold": 1.2,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.05,
        }
        is_valid, error = editor.validate_config(config)
        assert is_valid is False
        assert "symbol" in error


class TestConfigRoundTrip:
    """Property-based tests for config round trip."""
    
    @given(valid_config_strategy())
    def test_config_round_trip(self, config):
        """Feature: streamlit-ui, Property 9: Config Round Trip
        
        For any valid configuration, saving then loading the configuration
        must produce equivalent values.
        
        Validates: Requirements 6.3
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            editor = ConfigEditor(config_path)
            
            # Save config
            success, message = editor.save_config(config)
            assert success is True, f"Failed to save config: {message}"
            
            # Load config
            loaded_config = editor.load_config()
            
            # Verify all fields match
            for key, value in config.items():
                assert key in loaded_config, f"Key {key} missing in loaded config"
                assert loaded_config[key] == value, \
                    f"Value mismatch for {key}: expected {value}, got {loaded_config[key]}"


class TestConfigValidationProperty:
    """Property-based tests for config validation."""
    
    @given(st.floats(min_value=-1000, max_value=0.0) | st.floats(min_value=1.01, max_value=1000))
    def test_invalid_risk_per_trade_rejected(self, invalid_risk):
        """Feature: streamlit-ui, Property 8: Config Validation
        
        For any configuration input that violates validation rules,
        the Config_Editor must reject the input and display an error message.
        
        Validates: Requirements 6.2, 6.5
        """
        editor = ConfigEditor()
        
        config = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "risk_per_trade": invalid_risk,
            "leverage": 3,
            "adx_threshold": 20.0,
            "rvol_threshold": 1.2,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.05,
        }
        
        is_valid, error = editor.validate_config(config)
        assert is_valid is False, f"Should reject risk_per_trade={invalid_risk}"
        assert error != "", "Error message should not be empty"
        assert "risk_per_trade" in error.lower(), \
            f"Error message should mention risk_per_trade: {error}"
    
    @given(st.integers(min_value=-1000, max_value=0) | st.integers(min_value=126, max_value=1000))
    def test_invalid_leverage_rejected(self, invalid_leverage):
        """Feature: streamlit-ui, Property 8: Config Validation
        
        For any configuration input that violates validation rules,
        the Config_Editor must reject the input and display an error message.
        
        Validates: Requirements 6.2, 6.5
        """
        editor = ConfigEditor()
        
        config = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "risk_per_trade": 0.01,
            "leverage": invalid_leverage,
            "adx_threshold": 20.0,
            "rvol_threshold": 1.2,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.05,
        }
        
        is_valid, error = editor.validate_config(config)
        assert is_valid is False, f"Should reject leverage={invalid_leverage}"
        assert error != "", "Error message should not be empty"
        assert "leverage" in error.lower(), \
            f"Error message should mention leverage: {error}"
    
    @given(st.floats(min_value=-1000, max_value=-0.01) | st.floats(min_value=100.01, max_value=1000))
    def test_invalid_adx_threshold_rejected(self, invalid_adx):
        """Feature: streamlit-ui, Property 8: Config Validation
        
        For any configuration input that violates validation rules,
        the Config_Editor must reject the input and display an error message.
        
        Validates: Requirements 6.2, 6.5
        """
        editor = ConfigEditor()
        
        config = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "risk_per_trade": 0.01,
            "leverage": 3,
            "adx_threshold": invalid_adx,
            "rvol_threshold": 1.2,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.05,
        }
        
        is_valid, error = editor.validate_config(config)
        assert is_valid is False, f"Should reject adx_threshold={invalid_adx}"
        assert error != "", "Error message should not be empty"
        assert "adx_threshold" in error.lower(), \
            f"Error message should mention adx_threshold: {error}"
