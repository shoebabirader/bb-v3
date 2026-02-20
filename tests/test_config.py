"""Property-based and unit tests for configuration management."""

import json
import os
import tempfile
import pytest
from hypothesis import given, strategies as st
from src.config import Config


# Feature: binance-futures-bot, Property 38: Configuration Validation
@given(
    risk_per_trade=st.floats(min_value=0.0001, max_value=0.1),
    leverage=st.integers(min_value=1, max_value=125),
    atr_period=st.integers(min_value=1, max_value=100),
    adx_period=st.integers(min_value=1, max_value=100),
    adx_threshold=st.floats(min_value=0, max_value=100),
    rvol_period=st.integers(min_value=1, max_value=100),
    rvol_threshold=st.floats(min_value=0.1, max_value=10.0),
    backtest_days=st.integers(min_value=1, max_value=365),
    trading_fee=st.floats(min_value=0, max_value=0.01),
    slippage=st.floats(min_value=0, max_value=0.01),
    stop_loss_atr_multiplier=st.floats(min_value=0.1, max_value=10.0),
    trailing_stop_atr_multiplier=st.floats(min_value=0.1, max_value=10.0),
    run_mode=st.sampled_from(["BACKTEST", "PAPER", "LIVE"])
)
def test_valid_configuration_passes_validation(
    risk_per_trade, leverage, atr_period, adx_period, adx_threshold,
    rvol_period, rvol_threshold, backtest_days, trading_fee, slippage,
    stop_loss_atr_multiplier, trailing_stop_atr_multiplier, run_mode
):
    """For any valid configuration parameters, validation should pass without errors.
    
    Property 38: Configuration Validation
    Validates: Requirements 14.2
    """
    config = Config()
    config.risk_per_trade = risk_per_trade
    config.leverage = leverage
    config.atr_period = atr_period
    config.adx_period = adx_period
    config.adx_threshold = adx_threshold
    config.rvol_period = rvol_period
    config.rvol_threshold = rvol_threshold
    config.backtest_days = backtest_days
    config.trading_fee = trading_fee
    config.slippage = slippage
    config.stop_loss_atr_multiplier = stop_loss_atr_multiplier
    config.trailing_stop_atr_multiplier = trailing_stop_atr_multiplier
    config.run_mode = run_mode
    
    # For PAPER and LIVE modes, set dummy API keys
    if run_mode in ["PAPER", "LIVE"]:
        config.api_key = "test_api_key"
        config.api_secret = "test_api_secret"
    
    # Should not raise any exception
    config.validate()


# Feature: binance-futures-bot, Property 40: Default Configuration Values
@given(
    missing_params=st.lists(
        st.sampled_from([
            "symbol", "timeframe_entry", "timeframe_filter",
            "risk_per_trade", "leverage", "stop_loss_atr_multiplier",
            "trailing_stop_atr_multiplier", "atr_period", "adx_period",
            "adx_threshold", "rvol_period", "rvol_threshold",
            "backtest_days", "trading_fee", "slippage", "log_file"
        ]),
        min_size=1,
        max_size=5,
        unique=True
    )
)
def test_missing_optional_parameters_use_defaults(missing_params):
    """For any optional configuration parameter that is missing, 
    the system should use documented default values.
    
    Property 40: Default Configuration Values
    Validates: Requirements 14.5
    """
    # Create a minimal config dict (only required for BACKTEST mode)
    config_data = {
        "run_mode": "BACKTEST",
        "symbol": "BTCUSDT",
        "timeframe_entry": "15m",
        "timeframe_filter": "1h",
        "risk_per_trade": 0.01,
        "leverage": 3,
        "stop_loss_atr_multiplier": 2.0,
        "trailing_stop_atr_multiplier": 1.5,
        "atr_period": 14,
        "adx_period": 14,
        "adx_threshold": 20.0,
        "rvol_period": 20,
        "rvol_threshold": 1.2,
        "backtest_days": 90,
        "trading_fee": 0.0005,
        "slippage": 0.0002,
        "log_file": "binance_results.json"
    }
    
    # Remove the parameters we want to test as missing
    for param in missing_params:
        if param in config_data:
            del config_data[param]
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name
    
    try:
        # Load config from file
        config = Config.load_from_file(temp_path)
        
        # Verify that defaults were applied
        applied_defaults = config.get_applied_defaults()
        
        # At least one default should have been applied for missing params
        assert len(applied_defaults) > 0, "Expected defaults to be applied for missing parameters"
        
        # Verify the config is still valid
        config.validate()
        
    finally:
        # Clean up temp file
        os.unlink(temp_path)


# Feature: binance-futures-bot, Property 39: Invalid Configuration Rejection
class TestInvalidConfigurationRejection:
    """Unit tests for invalid configuration scenarios.
    
    Property 39: Invalid Configuration Rejection
    Validates: Requirements 14.3
    """
    
    def test_negative_risk_per_trade_rejected(self):
        """Negative risk_per_trade should be rejected."""
        config = Config()
        config.risk_per_trade = -0.01
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "risk_per_trade" in str(exc_info.value).lower()
    
    def test_excessive_risk_per_trade_rejected(self):
        """Risk per trade > 10% should be rejected."""
        config = Config()
        config.risk_per_trade = 0.15
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "risk_per_trade" in str(exc_info.value).lower()
    
    def test_invalid_run_mode_rejected(self):
        """Invalid run_mode should be rejected."""
        config = Config()
        config.run_mode = "INVALID_MODE"
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "run_mode" in str(exc_info.value).lower()
    
    def test_invalid_leverage_rejected(self):
        """Leverage outside 1-125 range should be rejected."""
        config = Config()
        config.leverage = 0
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "leverage" in str(exc_info.value).lower()
        
        config.leverage = 200
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "leverage" in str(exc_info.value).lower()
    
    def test_negative_atr_period_rejected(self):
        """Negative or zero ATR period should be rejected."""
        config = Config()
        config.atr_period = 0
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "atr_period" in str(exc_info.value).lower()
    
    def test_invalid_timeframe_rejected(self):
        """Invalid timeframe strings should be rejected."""
        config = Config()
        config.timeframe_entry = "invalid"
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "timeframe_entry" in str(exc_info.value).lower()
    
    def test_missing_api_keys_for_live_mode_rejected(self):
        """Missing API keys in LIVE mode should be rejected."""
        config = Config()
        config.run_mode = "LIVE"
        config.api_key = ""
        config.api_secret = ""
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        error_msg = str(exc_info.value).lower()
        assert "api_key" in error_msg or "api_secret" in error_msg
    
    def test_missing_api_keys_for_paper_mode_rejected(self):
        """Missing API keys in PAPER mode should be rejected."""
        config = Config()
        config.run_mode = "PAPER"
        config.api_key = ""
        config.api_secret = ""
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        error_msg = str(exc_info.value).lower()
        assert "api_key" in error_msg or "api_secret" in error_msg
    
    def test_negative_stop_loss_multiplier_rejected(self):
        """Negative stop loss multiplier should be rejected."""
        config = Config()
        config.stop_loss_atr_multiplier = -1.0
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "stop_loss_atr_multiplier" in str(exc_info.value).lower()
    
    def test_invalid_adx_threshold_rejected(self):
        """ADX threshold outside 0-100 range should be rejected."""
        config = Config()
        config.adx_threshold = 150.0
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "adx_threshold" in str(exc_info.value).lower()
    
    def test_multiple_errors_reported_together(self):
        """Multiple validation errors should be reported together."""
        config = Config()
        config.risk_per_trade = -0.01
        config.leverage = 0
        config.run_mode = "INVALID"
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        error_msg = str(exc_info.value).lower()
        # Should contain multiple error messages
        assert "risk_per_trade" in error_msg
        assert "leverage" in error_msg
        assert "run_mode" in error_msg


def test_api_key_redaction():
    """Test that API keys are properly redacted for logging."""
    config = Config()
    
    # Test with normal length key
    key = "abcdefghijklmnopqrstuvwxyz"
    redacted = config.redact_api_key(key)
    assert redacted == "abcd...wxyz"
    assert len(redacted) < len(key)
    
    # Test with short key
    short_key = "abc"
    redacted_short = config.redact_api_key(short_key)
    assert redacted_short == "****"
    
    # Test with empty key
    empty_key = ""
    redacted_empty = config.redact_api_key(empty_key)
    assert redacted_empty == "****"


# ===== ADVANCED FEATURES CONFIGURATION TESTS =====

# Feature: advanced-trading-enhancements, Property 27: Configuration validation
@given(
    enable_adaptive_thresholds=st.booleans(),
    enable_multi_timeframe=st.booleans(),
    enable_volume_profile=st.booleans(),
    enable_ml_prediction=st.booleans(),
    enable_portfolio_management=st.booleans(),
    enable_advanced_exits=st.booleans(),
    enable_regime_detection=st.booleans(),
    adaptive_threshold_min_adx=st.floats(min_value=10.0, max_value=29.9),
    adaptive_threshold_max_adx=st.floats(min_value=30.1, max_value=50.0),
    adaptive_threshold_min_rvol=st.floats(min_value=0.5, max_value=1.4),
    adaptive_threshold_max_rvol=st.floats(min_value=1.6, max_value=3.0),
    min_timeframe_alignment=st.integers(min_value=1, max_value=4),
    volume_profile_lookback_days=st.integers(min_value=3, max_value=30),
    volume_profile_value_area_pct=st.floats(min_value=0.60, max_value=0.80),
    ml_min_accuracy=st.floats(min_value=0.50, max_value=0.70),
    ml_low_confidence_threshold=st.floats(min_value=0.1, max_value=0.4),
    ml_high_confidence_threshold=st.floats(min_value=0.6, max_value=0.9),
    portfolio_max_symbols=st.integers(min_value=1, max_value=5),
    portfolio_correlation_threshold=st.floats(min_value=0.5, max_value=0.9),
    portfolio_max_total_risk=st.floats(min_value=0.01, max_value=0.20),
    exit_partial_1_atr_multiplier=st.floats(min_value=1.0, max_value=2.0),
    exit_partial_2_atr_multiplier=st.floats(min_value=2.5, max_value=4.0),
    exit_final_atr_multiplier=st.floats(min_value=4.5, max_value=7.0),
    regime_ranging_adx_threshold=st.floats(min_value=15.0, max_value=24.9),
    regime_trending_adx_threshold=st.floats(min_value=25.1, max_value=40.0),
    max_memory_mb=st.integers(min_value=100, max_value=2000),
    api_rate_limit_per_minute=st.integers(min_value=100, max_value=2000)
)
def test_valid_advanced_features_configuration_passes_validation(
    enable_adaptive_thresholds, enable_multi_timeframe, enable_volume_profile,
    enable_ml_prediction, enable_portfolio_management, enable_advanced_exits,
    enable_regime_detection, adaptive_threshold_min_adx, adaptive_threshold_max_adx,
    adaptive_threshold_min_rvol, adaptive_threshold_max_rvol, min_timeframe_alignment,
    volume_profile_lookback_days, volume_profile_value_area_pct, ml_min_accuracy,
    ml_low_confidence_threshold, ml_high_confidence_threshold, portfolio_max_symbols,
    portfolio_correlation_threshold, portfolio_max_total_risk, exit_partial_1_atr_multiplier,
    exit_partial_2_atr_multiplier, exit_final_atr_multiplier, regime_ranging_adx_threshold,
    regime_trending_adx_threshold, max_memory_mb, api_rate_limit_per_minute
):
    """For any valid advanced features configuration parameters, validation should pass without errors.
    
    Property 27: Configuration validation
    Validates: Requirements 8.7
    """
    config = Config()
    
    # Set feature toggles
    config.enable_adaptive_thresholds = enable_adaptive_thresholds
    config.enable_multi_timeframe = enable_multi_timeframe
    config.enable_volume_profile = enable_volume_profile
    config.enable_ml_prediction = enable_ml_prediction
    config.enable_portfolio_management = enable_portfolio_management
    config.enable_advanced_exits = enable_advanced_exits
    config.enable_regime_detection = enable_regime_detection
    
    # Set adaptive threshold parameters
    config.adaptive_threshold_min_adx = adaptive_threshold_min_adx
    config.adaptive_threshold_max_adx = adaptive_threshold_max_adx
    config.adaptive_threshold_min_rvol = adaptive_threshold_min_rvol
    config.adaptive_threshold_max_rvol = adaptive_threshold_max_rvol
    
    # Set multi-timeframe parameters
    config.min_timeframe_alignment = min_timeframe_alignment
    config.timeframe_weights = {
        "5m": 0.1,
        "15m": 0.2,
        "1h": 0.3,
        "4h": 0.4
    }
    
    # Set volume profile parameters
    config.volume_profile_lookback_days = volume_profile_lookback_days
    config.volume_profile_value_area_pct = volume_profile_value_area_pct
    
    # Set ML parameters
    config.ml_min_accuracy = ml_min_accuracy
    config.ml_low_confidence_threshold = ml_low_confidence_threshold
    config.ml_high_confidence_threshold = ml_high_confidence_threshold
    
    # Set portfolio parameters
    config.portfolio_max_symbols = portfolio_max_symbols
    config.portfolio_symbols = ["BTCUSDT"]  # Valid single symbol
    config.portfolio_correlation_threshold = portfolio_correlation_threshold
    config.portfolio_max_total_risk = portfolio_max_total_risk
    
    # Set exit parameters
    config.exit_partial_1_atr_multiplier = exit_partial_1_atr_multiplier
    config.exit_partial_2_atr_multiplier = exit_partial_2_atr_multiplier
    config.exit_final_atr_multiplier = exit_final_atr_multiplier
    
    # Set regime parameters
    config.regime_ranging_adx_threshold = regime_ranging_adx_threshold
    config.regime_trending_adx_threshold = regime_trending_adx_threshold
    
    # Set performance parameters
    config.max_memory_mb = max_memory_mb
    config.api_rate_limit_per_minute = api_rate_limit_per_minute
    
    # Should not raise any exception
    config.validate()


class TestAdvancedFeaturesConfiguration:
    """Unit tests for advanced features configuration validation.
    
    Validates: Requirements 8.1, 8.6, 8.7
    """
    
    def test_valid_advanced_features_config_accepted(self):
        """Valid advanced features configuration should be accepted."""
        config = Config()
        config.enable_adaptive_thresholds = True
        config.enable_multi_timeframe = True
        config.enable_volume_profile = True
        config.enable_ml_prediction = True
        config.enable_portfolio_management = True
        config.enable_advanced_exits = True
        config.enable_regime_detection = True
        
        # Should not raise any exception
        config.validate()
    
    def test_feature_toggles_work_correctly(self):
        """Feature toggles should enable/disable features independently."""
        config = Config()
        
        # All features disabled by default
        assert config.enable_adaptive_thresholds == False
        assert config.enable_multi_timeframe == False
        assert config.enable_volume_profile == False
        assert config.enable_ml_prediction == False
        assert config.enable_portfolio_management == False
        assert config.enable_advanced_exits == False
        assert config.enable_regime_detection == False
        
        # Enable individual features
        config.enable_adaptive_thresholds = True
        assert config.enable_adaptive_thresholds == True
        assert config.enable_multi_timeframe == False  # Others still disabled
        
        config.validate()
    
    def test_invalid_adaptive_threshold_min_max_rejected(self):
        """Adaptive threshold min >= max should be rejected."""
        config = Config()
        config.adaptive_threshold_min_adx = 30.0
        config.adaptive_threshold_max_adx = 20.0
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "adaptive_threshold_min_adx" in str(exc_info.value).lower()
        assert "adaptive_threshold_max_adx" in str(exc_info.value).lower()
    
    def test_invalid_adaptive_threshold_update_interval_rejected(self):
        """Update interval < 60 seconds should be rejected."""
        config = Config()
        config.adaptive_threshold_update_interval = 30
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "adaptive_threshold_update_interval" in str(exc_info.value).lower()
    
    def test_invalid_timeframe_weights_rejected(self):
        """Timeframe weights not summing to 1.0 should be rejected."""
        config = Config()
        config.timeframe_weights = {
            "5m": 0.2,
            "15m": 0.2,
            "1h": 0.2,
            "4h": 0.2  # Sum = 0.8, not 1.0
        }
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "timeframe_weights" in str(exc_info.value).lower()
        assert "sum" in str(exc_info.value).lower()
    
    def test_missing_timeframe_weight_keys_rejected(self):
        """Missing required timeframe weight keys should be rejected."""
        config = Config()
        config.timeframe_weights = {
            "5m": 0.5,
            "15m": 0.5
            # Missing 1h and 4h
        }
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "timeframe_weights" in str(exc_info.value).lower()
    
    def test_invalid_min_timeframe_alignment_rejected(self):
        """Min timeframe alignment outside 1-4 range should be rejected."""
        config = Config()
        config.min_timeframe_alignment = 5
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "min_timeframe_alignment" in str(exc_info.value).lower()
    
    def test_invalid_volume_profile_lookback_rejected(self):
        """Volume profile lookback outside valid range should be rejected."""
        config = Config()
        config.volume_profile_lookback_days = 50
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "volume_profile_lookback_days" in str(exc_info.value).lower()
    
    def test_invalid_volume_profile_value_area_rejected(self):
        """Volume profile value area > 1.0 should be rejected."""
        config = Config()
        config.volume_profile_value_area_pct = 1.5
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "volume_profile_value_area_pct" in str(exc_info.value).lower()
    
    def test_invalid_ml_confidence_thresholds_rejected(self):
        """ML low confidence >= high confidence should be rejected."""
        config = Config()
        config.ml_low_confidence_threshold = 0.8
        config.ml_high_confidence_threshold = 0.6
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "ml_low_confidence_threshold" in str(exc_info.value).lower()
        assert "ml_high_confidence_threshold" in str(exc_info.value).lower()
    
    def test_invalid_ml_min_accuracy_rejected(self):
        """ML min accuracy outside 0-1 range should be rejected."""
        config = Config()
        config.ml_min_accuracy = 1.5
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "ml_min_accuracy" in str(exc_info.value).lower()
    
    def test_invalid_ml_prediction_horizon_rejected(self):
        """ML prediction horizon outside valid range should be rejected."""
        config = Config()
        config.ml_prediction_horizon_hours = 48
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "ml_prediction_horizon_hours" in str(exc_info.value).lower()
    
    def test_empty_portfolio_symbols_rejected(self):
        """Empty portfolio symbols list should be rejected."""
        config = Config()
        config.portfolio_symbols = []
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "portfolio_symbols" in str(exc_info.value).lower()
    
    def test_too_many_portfolio_symbols_rejected(self):
        """Portfolio symbols exceeding max should be rejected."""
        config = Config()
        config.portfolio_max_symbols = 3
        config.portfolio_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "portfolio_symbols" in str(exc_info.value).lower()
    
    def test_invalid_portfolio_correlation_threshold_rejected(self):
        """Portfolio correlation threshold outside 0-1 range should be rejected."""
        config = Config()
        config.portfolio_correlation_threshold = 1.5
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "portfolio_correlation_threshold" in str(exc_info.value).lower()
    
    def test_invalid_portfolio_max_total_risk_rejected(self):
        """Portfolio max total risk > 20% should be rejected."""
        config = Config()
        config.portfolio_max_total_risk = 0.3
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "portfolio_max_total_risk" in str(exc_info.value).lower()
    
    def test_invalid_exit_levels_order_rejected(self):
        """Exit levels not in ascending order should be rejected."""
        config = Config()
        config.exit_partial_1_atr_multiplier = 3.0
        config.exit_partial_2_atr_multiplier = 1.5  # Should be > partial_1
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "exit_partial_1_atr_multiplier" in str(exc_info.value).lower()
        assert "exit_partial_2_atr_multiplier" in str(exc_info.value).lower()
    
    def test_invalid_exit_percentage_rejected(self):
        """Exit percentage outside 0-1 range should be rejected."""
        config = Config()
        config.exit_partial_1_percentage = 1.5
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "exit_partial_1_percentage" in str(exc_info.value).lower()
    
    def test_invalid_regime_adx_thresholds_rejected(self):
        """Regime ranging ADX >= trending ADX should be rejected."""
        config = Config()
        config.regime_ranging_adx_threshold = 35.0
        config.regime_trending_adx_threshold = 25.0
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "regime_ranging_adx_threshold" in str(exc_info.value).lower()
        assert "regime_trending_adx_threshold" in str(exc_info.value).lower()
    
    def test_invalid_regime_update_interval_rejected(self):
        """Regime update interval < 60 seconds should be rejected."""
        config = Config()
        config.regime_update_interval = 30
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "regime_update_interval" in str(exc_info.value).lower()
    
    def test_invalid_regime_volatile_size_reduction_rejected(self):
        """Regime volatile size reduction outside 0-1 range should be rejected."""
        config = Config()
        config.regime_volatile_size_reduction = 1.5
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "regime_volatile_size_reduction" in str(exc_info.value).lower()
    
    def test_invalid_max_memory_rejected(self):
        """Max memory < 100 MB should be rejected."""
        config = Config()
        config.max_memory_mb = 50
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "max_memory_mb" in str(exc_info.value).lower()
    
    def test_invalid_ml_prediction_timeout_rejected(self):
        """ML prediction timeout < 10 ms should be rejected."""
        config = Config()
        config.ml_prediction_timeout_ms = 5
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "ml_prediction_timeout_ms" in str(exc_info.value).lower()
    
    def test_invalid_api_rate_limit_rejected(self):
        """API rate limit < 100 should be rejected."""
        config = Config()
        config.api_rate_limit_per_minute = 50
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "api_rate_limit_per_minute" in str(exc_info.value).lower()
    
    def test_multiple_advanced_feature_errors_reported_together(self):
        """Multiple advanced feature validation errors should be reported together."""
        config = Config()
        config.adaptive_threshold_min_adx = 50.0
        config.adaptive_threshold_max_adx = 30.0
        config.ml_low_confidence_threshold = 0.9
        config.ml_high_confidence_threshold = 0.5
        config.portfolio_symbols = []
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        error_msg = str(exc_info.value).lower()
        # Should contain multiple error messages
        assert "adaptive_threshold" in error_msg
        assert "ml_" in error_msg
        assert "portfolio_symbols" in error_msg
    
    def test_advanced_features_config_from_file(self):
        """Advanced features configuration should load from file correctly."""
        config_data = {
            "run_mode": "BACKTEST",
            "enable_adaptive_thresholds": True,
            "enable_multi_timeframe": True,
            "adaptive_threshold_min_adx": 18.0,
            "adaptive_threshold_max_adx": 32.0,
            "timeframe_weights": {
                "5m": 0.15,
                "15m": 0.25,
                "1h": 0.30,
                "4h": 0.30
            },
            "portfolio_symbols": ["BTCUSDT", "ETHUSDT"],
            "portfolio_max_symbols": 5
        }
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            # Load config from file
            config = Config.load_from_file(temp_path)
            
            # Verify advanced features loaded correctly
            assert config.enable_adaptive_thresholds == True
            assert config.enable_multi_timeframe == True
            assert config.adaptive_threshold_min_adx == 18.0
            assert config.adaptive_threshold_max_adx == 32.0
            assert config.timeframe_weights["5m"] == 0.15
            assert config.portfolio_symbols == ["BTCUSDT", "ETHUSDT"]
            
            # Verify config is valid
            config.validate()
            
        finally:
            # Clean up temp file
            os.unlink(temp_path)
    
    def test_advanced_features_use_defaults_when_missing(self):
        """Advanced features should use defaults when not specified in config."""
        config_data = {
            "run_mode": "BACKTEST"
            # No advanced features specified
        }
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            # Load config from file
            config = Config.load_from_file(temp_path)
            
            # Verify defaults are applied
            assert config.enable_adaptive_thresholds == False
            assert config.enable_multi_timeframe == False
            assert config.adaptive_threshold_update_interval == 3600
            assert config.volume_profile_lookback_days == 7
            assert config.ml_min_accuracy == 0.55
            assert config.portfolio_max_symbols == 5
            
            # Verify defaults were tracked
            applied_defaults = config.get_applied_defaults()
            assert len(applied_defaults) > 0
            
            # Verify config is valid with defaults
            config.validate()
            
        finally:
            # Clean up temp file
            os.unlink(temp_path)


# ===== SCALED TAKE PROFIT CONFIGURATION TESTS =====

# Feature: scaled-take-profit, Property 5: Close percentage sum
# Feature: scaled-take-profit, Property 7: Profit level monotonicity
@given(
    enable_scaled_take_profit=st.booleans(),
    num_levels=st.integers(min_value=2, max_value=5),
    min_order_size=st.floats(min_value=0.0001, max_value=0.01)
)
def test_valid_scaled_tp_configuration_passes_validation(
    enable_scaled_take_profit, num_levels, min_order_size
):
    """For any valid scaled take profit configuration, validation should pass without errors.
    
    Property 5: Close percentage sum
    Property 7: Profit level monotonicity
    Validates: Requirements 2.4, 2.5
    """
    config = Config()
    config.enable_scaled_take_profit = enable_scaled_take_profit
    config.scaled_tp_min_order_size = min_order_size
    
    # Generate valid TP levels with ascending profit percentages and close percentages that sum to 1.0
    scaled_tp_levels = []
    profit_step = 0.02  # 2% increments
    close_pct_per_level = 1.0 / num_levels
    
    for i in range(num_levels):
        profit_pct = 0.02 + (i * profit_step)  # Start at 2%, increment by 2%
        scaled_tp_levels.append({
            "profit_pct": profit_pct,
            "close_pct": close_pct_per_level
        })
    
    config.scaled_tp_levels = scaled_tp_levels
    
    # Should not raise any exception
    config.validate()


class TestScaledTakeProfitConfiguration:
    """Unit tests for scaled take profit configuration validation.
    
    Validates: Requirements 2.1, 2.2, 2.4, 2.5
    """
    
    def test_valid_scaled_tp_config_accepted(self):
        """Valid scaled take profit configuration should be accepted."""
        config = Config()
        config.enable_scaled_take_profit = True
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        config.scaled_tp_min_order_size = 0.001
        config.scaled_tp_fallback_to_single = True
        
        # Should not raise any exception
        config.validate()
    
    def test_scaled_tp_disabled_by_default(self):
        """Scaled take profit should be disabled by default."""
        config = Config()
        assert config.enable_scaled_take_profit == False
    
    def test_scaled_tp_levels_not_ascending_rejected(self):
        """TP levels not in ascending order should be rejected (Property 7)."""
        config = Config()
        config.scaled_tp_levels = [
            {"profit_pct": 0.05, "close_pct": 0.40},
            {"profit_pct": 0.03, "close_pct": 0.30},  # Lower than previous
            {"profit_pct": 0.08, "close_pct": 0.30}
        ]
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        error_msg = str(exc_info.value).lower()
        assert "ascending" in error_msg or "greater than" in error_msg
    
    def test_scaled_tp_close_percentages_not_summing_to_100_warned(self):
        """Close percentages not summing to 100% should generate warning (Property 5)."""
        config = Config()
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 0.40},
            {"profit_pct": 0.05, "close_pct": 0.30},
            {"profit_pct": 0.08, "close_pct": 0.20}  # Sum = 0.90, not 1.0
        ]
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        error_msg = str(exc_info.value).lower()
        assert "sum" in error_msg or "normalized" in error_msg
    
    def test_scaled_tp_negative_profit_pct_rejected(self):
        """Negative profit percentage should be rejected."""
        config = Config()
        config.scaled_tp_levels = [
            {"profit_pct": -0.03, "close_pct": 0.50},
            {"profit_pct": 0.05, "close_pct": 0.50}
        ]
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "profit_pct" in str(exc_info.value).lower()
        assert "positive" in str(exc_info.value).lower()
    
    def test_scaled_tp_negative_close_pct_rejected(self):
        """Negative close percentage should be rejected."""
        config = Config()
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": -0.50},
            {"profit_pct": 0.05, "close_pct": 0.50}
        ]
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "close_pct" in str(exc_info.value).lower()
        assert "positive" in str(exc_info.value).lower()
    
    def test_scaled_tp_excessive_profit_pct_rejected(self):
        """Profit percentage > 100% should be rejected."""
        config = Config()
        config.scaled_tp_levels = [
            {"profit_pct": 1.5, "close_pct": 0.50},
            {"profit_pct": 2.0, "close_pct": 0.50}
        ]
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "profit_pct" in str(exc_info.value).lower()
    
    def test_scaled_tp_excessive_close_pct_rejected(self):
        """Close percentage > 100% should be rejected."""
        config = Config()
        config.scaled_tp_levels = [
            {"profit_pct": 0.03, "close_pct": 1.5},
            {"profit_pct": 0.05, "close_pct": 0.50}
        ]
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "close_pct" in str(exc_info.value).lower()
    
    def test_scaled_tp_missing_profit_pct_rejected(self):
        """Missing profit_pct key should be rejected."""
        config = Config()
        config.scaled_tp_levels = [
            {"close_pct": 0.50},  # Missing profit_pct
            {"profit_pct": 0.05, "close_pct": 0.50}
        ]
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "profit_pct" in str(exc_info.value).lower()
        assert "missing" in str(exc_info.value).lower()
    
    def test_scaled_tp_missing_close_pct_rejected(self):
        """Missing close_pct key should be rejected."""
        config = Config()
        config.scaled_tp_levels = [
            {"profit_pct": 0.03},  # Missing close_pct
            {"profit_pct": 0.05, "close_pct": 0.50}
        ]
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "close_pct" in str(exc_info.value).lower()
        assert "missing" in str(exc_info.value).lower()
    
    def test_scaled_tp_empty_levels_rejected(self):
        """Empty TP levels list should be rejected."""
        config = Config()
        config.scaled_tp_levels = []
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "scaled_tp_levels" in str(exc_info.value).lower()
        assert "at least one" in str(exc_info.value).lower()
    
    def test_scaled_tp_not_list_rejected(self):
        """TP levels not being a list should be rejected."""
        config = Config()
        config.scaled_tp_levels = "not a list"
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "scaled_tp_levels" in str(exc_info.value).lower()
        assert "list" in str(exc_info.value).lower()
    
    def test_scaled_tp_level_not_dict_rejected(self):
        """TP level not being a dictionary should be rejected."""
        config = Config()
        config.scaled_tp_levels = [
            "not a dict",
            {"profit_pct": 0.05, "close_pct": 0.50}
        ]
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "scaled_tp_levels" in str(exc_info.value).lower()
        assert "dictionary" in str(exc_info.value).lower()
    
    def test_scaled_tp_negative_min_order_size_rejected(self):
        """Negative minimum order size should be rejected."""
        config = Config()
        config.scaled_tp_min_order_size = -0.001
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "scaled_tp_min_order_size" in str(exc_info.value).lower()
        assert "positive" in str(exc_info.value).lower()
    
    def test_scaled_tp_config_from_file(self):
        """Scaled take profit configuration should load from file correctly."""
        config_data = {
            "run_mode": "BACKTEST",
            "enable_scaled_take_profit": True,
            "scaled_tp_levels": [
                {"profit_pct": 0.03, "close_pct": 0.40},
                {"profit_pct": 0.05, "close_pct": 0.30},
                {"profit_pct": 0.08, "close_pct": 0.30}
            ],
            "scaled_tp_min_order_size": 0.002,
            "scaled_tp_fallback_to_single": False
        }
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            # Load config from file
            config = Config.load_from_file(temp_path)
            
            # Verify scaled TP loaded correctly
            assert config.enable_scaled_take_profit == True
            assert len(config.scaled_tp_levels) == 3
            assert config.scaled_tp_levels[0]["profit_pct"] == 0.03
            assert config.scaled_tp_levels[0]["close_pct"] == 0.40
            assert config.scaled_tp_min_order_size == 0.002
            assert config.scaled_tp_fallback_to_single == False
            
            # Verify config is valid
            config.validate()
            
        finally:
            # Clean up temp file
            os.unlink(temp_path)
    
    def test_scaled_tp_uses_defaults_when_missing(self):
        """Scaled take profit should use defaults when not specified in config."""
        config_data = {
            "run_mode": "BACKTEST"
            # No scaled TP specified
        }
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            # Load config from file
            config = Config.load_from_file(temp_path)
            
            # Verify defaults are applied
            assert config.enable_scaled_take_profit == False
            assert len(config.scaled_tp_levels) == 3
            assert config.scaled_tp_levels[0]["profit_pct"] == 0.03
            assert config.scaled_tp_min_order_size == 0.001
            assert config.scaled_tp_fallback_to_single == True
            
            # Verify defaults were tracked
            applied_defaults = config.get_applied_defaults()
            assert any("scaled_tp" in default.lower() for default in applied_defaults)
            
            # Verify config is valid with defaults
            config.validate()
            
        finally:
            # Clean up temp file
            os.unlink(temp_path)

