"""Configuration management for Binance Futures Trading Bot."""

import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Configuration class for the trading bot.
    
    Loads configuration from config.json and environment variables.
    Validates all parameters before allowing system initialization.
    """
    
    # API Configuration
    api_key: str = ""
    api_secret: str = ""
    
    # Trading Parameters
    symbol: str = "BTCUSDT"
    timeframe_entry: str = "15m"
    timeframe_filter: str = "1h"
    
    # Risk Parameters
    risk_per_trade: float = 0.01  # 1%
    leverage: int = 3
    stop_loss_atr_multiplier: float = 2.0
    trailing_stop_atr_multiplier: float = 1.5
    
    # Indicator Parameters
    atr_period: int = 14
    adx_period: int = 14
    adx_threshold: float = 20.0
    rvol_period: int = 20
    rvol_threshold: float = 1.2
    
    # Backtest Parameters
    backtest_days: int = 90
    trading_fee: float = 0.0005  # 0.05%
    slippage: float = 0.0002     # 0.02%
    
    # System Parameters
    run_mode: str = "BACKTEST"  # BACKTEST, PAPER, LIVE
    log_file: str = "binance_results.json"
    
    # ===== ADVANCED FEATURES CONFIGURATION =====
    
    # Feature Toggles
    enable_adaptive_thresholds: bool = False
    enable_multi_timeframe: bool = False
    enable_volume_profile: bool = False
    enable_ml_prediction: bool = False
    enable_portfolio_management: bool = False
    enable_advanced_exits: bool = False
    enable_regime_detection: bool = False
    
    # Adaptive Threshold Parameters
    adaptive_threshold_update_interval: int = 3600  # seconds (1 hour)
    adaptive_threshold_lookback_days: int = 30
    adaptive_threshold_min_adx: float = 15.0
    adaptive_threshold_max_adx: float = 35.0
    adaptive_threshold_min_rvol: float = 0.8
    adaptive_threshold_max_rvol: float = 2.0
    
    # Multi-Timeframe Parameters
    timeframe_5m: str = "5m"
    timeframe_4h: str = "4h"
    timeframe_weights: dict = field(default_factory=lambda: {
        "5m": 0.1,
        "15m": 0.2,
        "1h": 0.3,
        "4h": 0.4
    })
    min_timeframe_alignment: int = 3  # Minimum aligned timeframes for signal
    
    # Volume Profile Parameters
    volume_profile_lookback_days: int = 7
    volume_profile_update_interval: int = 14400  # seconds (4 hours)
    volume_profile_bin_size: float = 0.001  # 0.1% price increments
    volume_profile_value_area_pct: float = 0.70  # 70% of volume
    volume_profile_key_level_threshold: float = 0.005  # 0.5% proximity
    volume_profile_low_volume_size_reduction: float = 0.5  # 50% reduction
    
    # ML Predictor Parameters
    ml_model_path: str = "models/ml_predictor.pkl"
    ml_feature_count: int = 20
    ml_prediction_horizon_hours: int = 4
    ml_min_accuracy: float = 0.55  # 55% minimum accuracy
    ml_accuracy_window: int = 100  # Rolling window for accuracy tracking
    ml_high_confidence_threshold: float = 0.7
    ml_low_confidence_threshold: float = 0.3
    ml_retrain_interval_days: int = 7
    ml_training_lookback_days: int = 90
    
    # Portfolio Management Parameters
    portfolio_symbols: list = field(default_factory=lambda: ["BTCUSDT"])
    portfolio_max_symbols: int = 5
    portfolio_correlation_threshold: float = 0.7
    portfolio_correlation_max_exposure: float = 0.5  # 50% combined for correlated
    portfolio_max_single_allocation: float = 0.4  # 40% max per symbol
    portfolio_rebalance_interval: int = 21600  # seconds (6 hours)
    portfolio_correlation_lookback_days: int = 30
    portfolio_max_total_risk: float = 0.05  # 5% total portfolio risk
    
    # Advanced Exit Parameters
    exit_partial_1_atr_multiplier: float = 1.5
    exit_partial_1_percentage: float = 0.33  # 33%
    exit_partial_2_atr_multiplier: float = 3.0
    exit_partial_2_percentage: float = 0.33  # 33%
    exit_final_atr_multiplier: float = 5.0
    exit_breakeven_atr_multiplier: float = 2.0
    exit_tight_stop_atr_multiplier: float = 0.5
    exit_max_hold_time_hours: int = 24
    exit_regime_change_enabled: bool = True
    
    # Market Regime Parameters
    regime_update_interval: int = 900  # seconds (15 minutes)
    regime_stability_minutes: int = 15
    regime_trending_adx_threshold: float = 30.0
    regime_ranging_adx_threshold: float = 20.0
    regime_volatile_atr_percentile: float = 80.0
    regime_ranging_atr_percentile: float = 40.0
    regime_trending_stop_multiplier: float = 2.5
    regime_ranging_stop_multiplier: float = 1.0
    regime_volatile_size_reduction: float = 0.5  # 50% reduction
    regime_volatile_threshold_increase: float = 0.3  # 30% increase
    
    # Performance Parameters
    max_memory_mb: int = 500
    ml_prediction_timeout_ms: int = 100
    api_rate_limit_per_minute: int = 1200
    data_cleanup_interval_hours: int = 6
    async_volume_profile: bool = True
    cache_indicators: bool = True
    
    # Applied defaults tracking
    _applied_defaults: list = field(default_factory=list, init=False, repr=False)
    
    @classmethod
    def load_from_file(cls, config_path: str = "config/config.json") -> "Config":
        """Load configuration from JSON file and environment variables.
        
        Args:
            config_path: Path to the configuration JSON file
            
        Returns:
            Config instance with loaded and validated configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        config = cls()
        
        # Load from JSON file if it exists
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                config._load_from_dict(config_data)
        else:
            # Track that we're using all defaults
            config._applied_defaults.append("No config file found, using all defaults")
        
        # Override with environment variables (higher priority)
        config._load_from_env()
        
        # Validate configuration
        config.validate()
        
        return config
    
    def _load_from_dict(self, config_data: dict) -> None:
        """Load configuration from dictionary."""
        # API Configuration
        if "api_key" in config_data:
            self.api_key = config_data["api_key"]
        else:
            self._applied_defaults.append("api_key (will check environment variables)")
            
        if "api_secret" in config_data:
            self.api_secret = config_data["api_secret"]
        else:
            self._applied_defaults.append("api_secret (will check environment variables)")
        
        # Trading Parameters
        if "symbol" in config_data:
            self.symbol = config_data["symbol"]
        else:
            self._applied_defaults.append(f"symbol (default: {self.symbol})")
            
        if "timeframe_entry" in config_data:
            self.timeframe_entry = config_data["timeframe_entry"]
        else:
            self._applied_defaults.append(f"timeframe_entry (default: {self.timeframe_entry})")
            
        if "timeframe_filter" in config_data:
            self.timeframe_filter = config_data["timeframe_filter"]
        else:
            self._applied_defaults.append(f"timeframe_filter (default: {self.timeframe_filter})")
        
        # Risk Parameters
        if "risk_per_trade" in config_data:
            self.risk_per_trade = float(config_data["risk_per_trade"])
        else:
            self._applied_defaults.append(f"risk_per_trade (default: {self.risk_per_trade})")
            
        if "leverage" in config_data:
            self.leverage = int(config_data["leverage"])
        else:
            self._applied_defaults.append(f"leverage (default: {self.leverage})")
            
        if "stop_loss_atr_multiplier" in config_data:
            self.stop_loss_atr_multiplier = float(config_data["stop_loss_atr_multiplier"])
        else:
            self._applied_defaults.append(f"stop_loss_atr_multiplier (default: {self.stop_loss_atr_multiplier})")
            
        if "trailing_stop_atr_multiplier" in config_data:
            self.trailing_stop_atr_multiplier = float(config_data["trailing_stop_atr_multiplier"])
        else:
            self._applied_defaults.append(f"trailing_stop_atr_multiplier (default: {self.trailing_stop_atr_multiplier})")
        
        # Indicator Parameters
        if "atr_period" in config_data:
            self.atr_period = int(config_data["atr_period"])
        else:
            self._applied_defaults.append(f"atr_period (default: {self.atr_period})")
            
        if "adx_period" in config_data:
            self.adx_period = int(config_data["adx_period"])
        else:
            self._applied_defaults.append(f"adx_period (default: {self.adx_period})")
            
        if "adx_threshold" in config_data:
            self.adx_threshold = float(config_data["adx_threshold"])
        else:
            self._applied_defaults.append(f"adx_threshold (default: {self.adx_threshold})")
            
        if "rvol_period" in config_data:
            self.rvol_period = int(config_data["rvol_period"])
        else:
            self._applied_defaults.append(f"rvol_period (default: {self.rvol_period})")
            
        if "rvol_threshold" in config_data:
            self.rvol_threshold = float(config_data["rvol_threshold"])
        else:
            self._applied_defaults.append(f"rvol_threshold (default: {self.rvol_threshold})")
        
        # Backtest Parameters
        if "backtest_days" in config_data:
            self.backtest_days = int(config_data["backtest_days"])
        else:
            self._applied_defaults.append(f"backtest_days (default: {self.backtest_days})")
            
        if "trading_fee" in config_data:
            self.trading_fee = float(config_data["trading_fee"])
        else:
            self._applied_defaults.append(f"trading_fee (default: {self.trading_fee})")
            
        if "slippage" in config_data:
            self.slippage = float(config_data["slippage"])
        else:
            self._applied_defaults.append(f"slippage (default: {self.slippage})")
        
        # System Parameters
        if "run_mode" in config_data:
            self.run_mode = config_data["run_mode"]
        else:
            self._applied_defaults.append(f"run_mode (default: {self.run_mode})")
            
        if "log_file" in config_data:
            self.log_file = config_data["log_file"]
        else:
            self._applied_defaults.append(f"log_file (default: {self.log_file})")
        
        # Advanced Features - Feature Toggles
        self._load_bool_param(config_data, "enable_adaptive_thresholds")
        self._load_bool_param(config_data, "enable_multi_timeframe")
        self._load_bool_param(config_data, "enable_volume_profile")
        self._load_bool_param(config_data, "enable_ml_prediction")
        self._load_bool_param(config_data, "enable_portfolio_management")
        self._load_bool_param(config_data, "enable_advanced_exits")
        self._load_bool_param(config_data, "enable_regime_detection")
        
        # Adaptive Threshold Parameters
        self._load_int_param(config_data, "adaptive_threshold_update_interval")
        self._load_int_param(config_data, "adaptive_threshold_lookback_days")
        self._load_float_param(config_data, "adaptive_threshold_min_adx")
        self._load_float_param(config_data, "adaptive_threshold_max_adx")
        self._load_float_param(config_data, "adaptive_threshold_min_rvol")
        self._load_float_param(config_data, "adaptive_threshold_max_rvol")
        
        # Multi-Timeframe Parameters
        self._load_str_param(config_data, "timeframe_5m")
        self._load_str_param(config_data, "timeframe_4h")
        if "timeframe_weights" in config_data:
            self.timeframe_weights = config_data["timeframe_weights"]
        else:
            self._applied_defaults.append(f"timeframe_weights (default: {self.timeframe_weights})")
        self._load_int_param(config_data, "min_timeframe_alignment")
        
        # Volume Profile Parameters
        self._load_int_param(config_data, "volume_profile_lookback_days")
        self._load_int_param(config_data, "volume_profile_update_interval")
        self._load_float_param(config_data, "volume_profile_bin_size")
        self._load_float_param(config_data, "volume_profile_value_area_pct")
        self._load_float_param(config_data, "volume_profile_key_level_threshold")
        self._load_float_param(config_data, "volume_profile_low_volume_size_reduction")
        
        # ML Predictor Parameters
        self._load_str_param(config_data, "ml_model_path")
        self._load_int_param(config_data, "ml_feature_count")
        self._load_int_param(config_data, "ml_prediction_horizon_hours")
        self._load_float_param(config_data, "ml_min_accuracy")
        self._load_int_param(config_data, "ml_accuracy_window")
        self._load_float_param(config_data, "ml_high_confidence_threshold")
        self._load_float_param(config_data, "ml_low_confidence_threshold")
        self._load_int_param(config_data, "ml_retrain_interval_days")
        self._load_int_param(config_data, "ml_training_lookback_days")
        
        # Portfolio Management Parameters
        if "portfolio_symbols" in config_data:
            self.portfolio_symbols = config_data["portfolio_symbols"]
        else:
            self._applied_defaults.append(f"portfolio_symbols (default: {self.portfolio_symbols})")
        self._load_int_param(config_data, "portfolio_max_symbols")
        self._load_float_param(config_data, "portfolio_correlation_threshold")
        self._load_float_param(config_data, "portfolio_correlation_max_exposure")
        self._load_float_param(config_data, "portfolio_max_single_allocation")
        self._load_int_param(config_data, "portfolio_rebalance_interval")
        self._load_int_param(config_data, "portfolio_correlation_lookback_days")
        self._load_float_param(config_data, "portfolio_max_total_risk")
        
        # Advanced Exit Parameters
        self._load_float_param(config_data, "exit_partial_1_atr_multiplier")
        self._load_float_param(config_data, "exit_partial_1_percentage")
        self._load_float_param(config_data, "exit_partial_2_atr_multiplier")
        self._load_float_param(config_data, "exit_partial_2_percentage")
        self._load_float_param(config_data, "exit_final_atr_multiplier")
        self._load_float_param(config_data, "exit_breakeven_atr_multiplier")
        self._load_float_param(config_data, "exit_tight_stop_atr_multiplier")
        self._load_int_param(config_data, "exit_max_hold_time_hours")
        self._load_bool_param(config_data, "exit_regime_change_enabled")
        
        # Market Regime Parameters
        self._load_int_param(config_data, "regime_update_interval")
        self._load_int_param(config_data, "regime_stability_minutes")
        self._load_float_param(config_data, "regime_trending_adx_threshold")
        self._load_float_param(config_data, "regime_ranging_adx_threshold")
        self._load_float_param(config_data, "regime_volatile_atr_percentile")
        self._load_float_param(config_data, "regime_ranging_atr_percentile")
        self._load_float_param(config_data, "regime_trending_stop_multiplier")
        self._load_float_param(config_data, "regime_ranging_stop_multiplier")
        self._load_float_param(config_data, "regime_volatile_size_reduction")
        self._load_float_param(config_data, "regime_volatile_threshold_increase")
        
        # Performance Parameters
        self._load_int_param(config_data, "max_memory_mb")
        self._load_int_param(config_data, "ml_prediction_timeout_ms")
        self._load_int_param(config_data, "api_rate_limit_per_minute")
        self._load_int_param(config_data, "data_cleanup_interval_hours")
        self._load_bool_param(config_data, "async_volume_profile")
        self._load_bool_param(config_data, "cache_indicators")
    
    def _load_bool_param(self, config_data: dict, param_name: str) -> None:
        """Load a boolean parameter from config data."""
        if param_name in config_data:
            setattr(self, param_name, bool(config_data[param_name]))
        else:
            default_value = getattr(self, param_name)
            self._applied_defaults.append(f"{param_name} (default: {default_value})")
    
    def _load_int_param(self, config_data: dict, param_name: str) -> None:
        """Load an integer parameter from config data."""
        if param_name in config_data:
            setattr(self, param_name, int(config_data[param_name]))
        else:
            default_value = getattr(self, param_name)
            self._applied_defaults.append(f"{param_name} (default: {default_value})")
    
    def _load_float_param(self, config_data: dict, param_name: str) -> None:
        """Load a float parameter from config data."""
        if param_name in config_data:
            setattr(self, param_name, float(config_data[param_name]))
        else:
            default_value = getattr(self, param_name)
            self._applied_defaults.append(f"{param_name} (default: {default_value})")
    
    def _load_str_param(self, config_data: dict, param_name: str) -> None:
        """Load a string parameter from config data."""
        if param_name in config_data:
            setattr(self, param_name, str(config_data[param_name]))
        else:
            default_value = getattr(self, param_name)
            self._applied_defaults.append(f"{param_name} (default: {default_value})")
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables (overrides file config)."""
        if os.getenv("BINANCE_API_KEY"):
            self.api_key = os.getenv("BINANCE_API_KEY")
        
        if os.getenv("BINANCE_API_SECRET"):
            self.api_secret = os.getenv("BINANCE_API_SECRET")
        
        if os.getenv("TRADING_SYMBOL"):
            self.symbol = os.getenv("TRADING_SYMBOL")
        
        if os.getenv("RUN_MODE"):
            self.run_mode = os.getenv("RUN_MODE")
    
    def redact_api_key(self, key: str) -> str:
        """Redact API key for safe logging/display.
        
        Args:
            key: API key to redact
            
        Returns:
            Redacted key showing only first 4 and last 4 characters
        """
        if not key or len(key) < 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"
    
    def validate(self) -> None:
        """Validate all configuration parameters.
        
        Raises:
            ValueError: If any configuration parameter is invalid
        """
        errors = []
        
        # Validate run mode
        valid_modes = ["BACKTEST", "PAPER", "LIVE"]
        if self.run_mode not in valid_modes:
            errors.append(f"Invalid run_mode '{self.run_mode}'. Must be one of: {', '.join(valid_modes)}")
        
        # Validate API keys for PAPER and LIVE modes
        if self.run_mode in ["PAPER", "LIVE"]:
            if not self.api_key:
                errors.append("api_key is required for PAPER and LIVE modes")
            if not self.api_secret:
                errors.append("api_secret is required for PAPER and LIVE modes")
        
        # Validate risk parameters
        # WARNING: Values above 0.1 (10%) are extremely dangerous and can lead to account loss
        if self.risk_per_trade <= 0 or self.risk_per_trade > 1.0:
            errors.append(f"Invalid risk_per_trade {self.risk_per_trade}. Must be between 0 and 1.0 (0-100%)")
        
        if self.leverage < 1 or self.leverage > 125:
            errors.append(f"Invalid leverage {self.leverage}. Must be between 1 and 125")
        
        if self.stop_loss_atr_multiplier <= 0:
            errors.append(f"Invalid stop_loss_atr_multiplier {self.stop_loss_atr_multiplier}. Must be positive")
        
        if self.trailing_stop_atr_multiplier <= 0:
            errors.append(f"Invalid trailing_stop_atr_multiplier {self.trailing_stop_atr_multiplier}. Must be positive")
        
        # Validate indicator parameters
        if self.atr_period < 1:
            errors.append(f"Invalid atr_period {self.atr_period}. Must be at least 1")
        
        if self.adx_period < 1:
            errors.append(f"Invalid adx_period {self.adx_period}. Must be at least 1")
        
        if self.adx_threshold < 0 or self.adx_threshold > 100:
            errors.append(f"Invalid adx_threshold {self.adx_threshold}. Must be between 0 and 100")
        
        if self.rvol_period < 1:
            errors.append(f"Invalid rvol_period {self.rvol_period}. Must be at least 1")
        
        if self.rvol_threshold <= 0:
            errors.append(f"Invalid rvol_threshold {self.rvol_threshold}. Must be positive")
        
        # Validate backtest parameters
        if self.backtest_days < 1:
            errors.append(f"Invalid backtest_days {self.backtest_days}. Must be at least 1")
        
        if self.trading_fee < 0 or self.trading_fee > 0.01:
            errors.append(f"Invalid trading_fee {self.trading_fee}. Must be between 0 and 0.01 (0-1%)")
        
        if self.slippage < 0 or self.slippage > 0.01:
            errors.append(f"Invalid slippage {self.slippage}. Must be between 0 and 0.01 (0-1%)")
        
        # Validate timeframes
        valid_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"]
        if self.timeframe_entry not in valid_timeframes:
            errors.append(f"Invalid timeframe_entry '{self.timeframe_entry}'. Must be one of: {', '.join(valid_timeframes)}")
        
        if self.timeframe_filter not in valid_timeframes:
            errors.append(f"Invalid timeframe_filter '{self.timeframe_filter}'. Must be one of: {', '.join(valid_timeframes)}")
        
        # Validate advanced features parameters
        self._validate_adaptive_thresholds(errors)
        self._validate_multi_timeframe(errors, valid_timeframes)
        self._validate_volume_profile(errors)
        self._validate_ml_predictor(errors)
        self._validate_portfolio_management(errors)
        self._validate_advanced_exits(errors)
        self._validate_regime_detection(errors)
        self._validate_performance(errors)
        
        # If there are errors, raise ValueError with all error messages
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_message)
    
    def _validate_adaptive_thresholds(self, errors: list) -> None:
        """Validate adaptive threshold parameters."""
        if self.adaptive_threshold_update_interval < 60:
            errors.append(f"Invalid adaptive_threshold_update_interval {self.adaptive_threshold_update_interval}. Must be at least 60 seconds")
        
        if self.adaptive_threshold_lookback_days < 7 or self.adaptive_threshold_lookback_days > 90:
            errors.append(f"Invalid adaptive_threshold_lookback_days {self.adaptive_threshold_lookback_days}. Must be between 7 and 90")
        
        if self.adaptive_threshold_min_adx < 0 or self.adaptive_threshold_min_adx > 100:
            errors.append(f"Invalid adaptive_threshold_min_adx {self.adaptive_threshold_min_adx}. Must be between 0 and 100")
        
        if self.adaptive_threshold_max_adx < 0 or self.adaptive_threshold_max_adx > 100:
            errors.append(f"Invalid adaptive_threshold_max_adx {self.adaptive_threshold_max_adx}. Must be between 0 and 100")
        
        if self.adaptive_threshold_min_adx >= self.adaptive_threshold_max_adx:
            errors.append(f"adaptive_threshold_min_adx ({self.adaptive_threshold_min_adx}) must be less than adaptive_threshold_max_adx ({self.adaptive_threshold_max_adx})")
        
        if self.adaptive_threshold_min_rvol <= 0:
            errors.append(f"Invalid adaptive_threshold_min_rvol {self.adaptive_threshold_min_rvol}. Must be positive")
        
        if self.adaptive_threshold_max_rvol <= 0:
            errors.append(f"Invalid adaptive_threshold_max_rvol {self.adaptive_threshold_max_rvol}. Must be positive")
        
        if self.adaptive_threshold_min_rvol >= self.adaptive_threshold_max_rvol:
            errors.append(f"adaptive_threshold_min_rvol ({self.adaptive_threshold_min_rvol}) must be less than adaptive_threshold_max_rvol ({self.adaptive_threshold_max_rvol})")
    
    def _validate_multi_timeframe(self, errors: list, valid_timeframes: list) -> None:
        """Validate multi-timeframe parameters."""
        if self.timeframe_5m not in valid_timeframes:
            errors.append(f"Invalid timeframe_5m '{self.timeframe_5m}'. Must be one of: {', '.join(valid_timeframes)}")
        
        if self.timeframe_4h not in valid_timeframes:
            errors.append(f"Invalid timeframe_4h '{self.timeframe_4h}'. Must be one of: {', '.join(valid_timeframes)}")
        
        if self.min_timeframe_alignment < 1 or self.min_timeframe_alignment > 4:
            errors.append(f"Invalid min_timeframe_alignment {self.min_timeframe_alignment}. Must be between 1 and 4")
        
        # Validate timeframe weights
        if not isinstance(self.timeframe_weights, dict):
            errors.append("timeframe_weights must be a dictionary")
        else:
            required_keys = ["5m", "15m", "1h", "4h"]
            for key in required_keys:
                if key not in self.timeframe_weights:
                    errors.append(f"timeframe_weights missing required key: {key}")
                elif not isinstance(self.timeframe_weights[key], (int, float)):
                    errors.append(f"timeframe_weights[{key}] must be a number")
                elif self.timeframe_weights[key] < 0 or self.timeframe_weights[key] > 1:
                    errors.append(f"timeframe_weights[{key}] must be between 0 and 1")
            
            # Check if weights sum to approximately 1.0
            if all(key in self.timeframe_weights for key in required_keys):
                total_weight = sum(self.timeframe_weights[key] for key in required_keys)
                if abs(total_weight - 1.0) > 0.01:
                    errors.append(f"timeframe_weights must sum to 1.0 (current sum: {total_weight})")
    
    def _validate_volume_profile(self, errors: list) -> None:
        """Validate volume profile parameters."""
        if self.volume_profile_lookback_days < 1 or self.volume_profile_lookback_days > 30:
            errors.append(f"Invalid volume_profile_lookback_days {self.volume_profile_lookback_days}. Must be between 1 and 30")
        
        if self.volume_profile_update_interval < 3600:
            errors.append(f"Invalid volume_profile_update_interval {self.volume_profile_update_interval}. Must be at least 3600 seconds (1 hour)")
        
        if self.volume_profile_bin_size <= 0 or self.volume_profile_bin_size > 0.01:
            errors.append(f"Invalid volume_profile_bin_size {self.volume_profile_bin_size}. Must be between 0 and 0.01")
        
        if self.volume_profile_value_area_pct <= 0 or self.volume_profile_value_area_pct > 1.0:
            errors.append(f"Invalid volume_profile_value_area_pct {self.volume_profile_value_area_pct}. Must be between 0 and 1.0")
        
        if self.volume_profile_key_level_threshold <= 0 or self.volume_profile_key_level_threshold > 0.1:
            errors.append(f"Invalid volume_profile_key_level_threshold {self.volume_profile_key_level_threshold}. Must be between 0 and 0.1")
        
        if self.volume_profile_low_volume_size_reduction <= 0 or self.volume_profile_low_volume_size_reduction > 1.0:
            errors.append(f"Invalid volume_profile_low_volume_size_reduction {self.volume_profile_low_volume_size_reduction}. Must be between 0 and 1.0")
    
    def _validate_ml_predictor(self, errors: list) -> None:
        """Validate ML predictor parameters."""
        if self.ml_feature_count < 1:
            errors.append(f"Invalid ml_feature_count {self.ml_feature_count}. Must be at least 1")
        
        if self.ml_prediction_horizon_hours < 1 or self.ml_prediction_horizon_hours > 24:
            errors.append(f"Invalid ml_prediction_horizon_hours {self.ml_prediction_horizon_hours}. Must be between 1 and 24")
        
        if self.ml_min_accuracy <= 0 or self.ml_min_accuracy > 1.0:
            errors.append(f"Invalid ml_min_accuracy {self.ml_min_accuracy}. Must be between 0 and 1.0")
        
        if self.ml_accuracy_window < 10:
            errors.append(f"Invalid ml_accuracy_window {self.ml_accuracy_window}. Must be at least 10")
        
        if self.ml_high_confidence_threshold <= 0 or self.ml_high_confidence_threshold > 1.0:
            errors.append(f"Invalid ml_high_confidence_threshold {self.ml_high_confidence_threshold}. Must be between 0 and 1.0")
        
        if self.ml_low_confidence_threshold <= 0 or self.ml_low_confidence_threshold > 1.0:
            errors.append(f"Invalid ml_low_confidence_threshold {self.ml_low_confidence_threshold}. Must be between 0 and 1.0")
        
        if self.ml_low_confidence_threshold >= self.ml_high_confidence_threshold:
            errors.append(f"ml_low_confidence_threshold ({self.ml_low_confidence_threshold}) must be less than ml_high_confidence_threshold ({self.ml_high_confidence_threshold})")
        
        if self.ml_retrain_interval_days < 1:
            errors.append(f"Invalid ml_retrain_interval_days {self.ml_retrain_interval_days}. Must be at least 1")
        
        if self.ml_training_lookback_days < 30:
            errors.append(f"Invalid ml_training_lookback_days {self.ml_training_lookback_days}. Must be at least 30")
    
    def _validate_portfolio_management(self, errors: list) -> None:
        """Validate portfolio management parameters."""
        if not isinstance(self.portfolio_symbols, list):
            errors.append("portfolio_symbols must be a list")
        elif len(self.portfolio_symbols) == 0:
            errors.append("portfolio_symbols must contain at least one symbol")
        elif len(self.portfolio_symbols) > self.portfolio_max_symbols:
            errors.append(f"portfolio_symbols contains {len(self.portfolio_symbols)} symbols but portfolio_max_symbols is {self.portfolio_max_symbols}")
        
        if self.portfolio_max_symbols < 1 or self.portfolio_max_symbols > 10:
            errors.append(f"Invalid portfolio_max_symbols {self.portfolio_max_symbols}. Must be between 1 and 10")
        
        if self.portfolio_correlation_threshold <= 0 or self.portfolio_correlation_threshold > 1.0:
            errors.append(f"Invalid portfolio_correlation_threshold {self.portfolio_correlation_threshold}. Must be between 0 and 1.0")
        
        if self.portfolio_correlation_max_exposure <= 0 or self.portfolio_correlation_max_exposure > 1.0:
            errors.append(f"Invalid portfolio_correlation_max_exposure {self.portfolio_correlation_max_exposure}. Must be between 0 and 1.0")
        
        if self.portfolio_max_single_allocation <= 0 or self.portfolio_max_single_allocation > 1.0:
            errors.append(f"Invalid portfolio_max_single_allocation {self.portfolio_max_single_allocation}. Must be between 0 and 1.0")
        
        if self.portfolio_rebalance_interval < 3600:
            errors.append(f"Invalid portfolio_rebalance_interval {self.portfolio_rebalance_interval}. Must be at least 3600 seconds (1 hour)")
        
        if self.portfolio_correlation_lookback_days < 7 or self.portfolio_correlation_lookback_days > 90:
            errors.append(f"Invalid portfolio_correlation_lookback_days {self.portfolio_correlation_lookback_days}. Must be between 7 and 90")
        
        if self.portfolio_max_total_risk <= 0 or self.portfolio_max_total_risk > 1.0:
            errors.append(f"Invalid portfolio_max_total_risk {self.portfolio_max_total_risk}. Must be between 0 and 1.0 (0-100%)")
    
    def _validate_advanced_exits(self, errors: list) -> None:
        """Validate advanced exit parameters."""
        if self.exit_partial_1_atr_multiplier <= 0:
            errors.append(f"Invalid exit_partial_1_atr_multiplier {self.exit_partial_1_atr_multiplier}. Must be positive")
        
        if self.exit_partial_1_percentage <= 0 or self.exit_partial_1_percentage > 1.0:
            errors.append(f"Invalid exit_partial_1_percentage {self.exit_partial_1_percentage}. Must be between 0 and 1.0")
        
        if self.exit_partial_2_atr_multiplier <= 0:
            errors.append(f"Invalid exit_partial_2_atr_multiplier {self.exit_partial_2_atr_multiplier}. Must be positive")
        
        if self.exit_partial_2_percentage <= 0 or self.exit_partial_2_percentage > 1.0:
            errors.append(f"Invalid exit_partial_2_percentage {self.exit_partial_2_percentage}. Must be between 0 and 1.0")
        
        if self.exit_final_atr_multiplier <= 0:
            errors.append(f"Invalid exit_final_atr_multiplier {self.exit_final_atr_multiplier}. Must be positive")
        
        if self.exit_breakeven_atr_multiplier <= 0:
            errors.append(f"Invalid exit_breakeven_atr_multiplier {self.exit_breakeven_atr_multiplier}. Must be positive")
        
        if self.exit_tight_stop_atr_multiplier <= 0:
            errors.append(f"Invalid exit_tight_stop_atr_multiplier {self.exit_tight_stop_atr_multiplier}. Must be positive")
        
        if self.exit_max_hold_time_hours < 1:
            errors.append(f"Invalid exit_max_hold_time_hours {self.exit_max_hold_time_hours}. Must be at least 1")
        
        # Validate exit levels are in ascending order
        if self.exit_partial_1_atr_multiplier >= self.exit_partial_2_atr_multiplier:
            errors.append(f"exit_partial_1_atr_multiplier ({self.exit_partial_1_atr_multiplier}) must be less than exit_partial_2_atr_multiplier ({self.exit_partial_2_atr_multiplier})")
        
        if self.exit_partial_2_atr_multiplier >= self.exit_final_atr_multiplier:
            errors.append(f"exit_partial_2_atr_multiplier ({self.exit_partial_2_atr_multiplier}) must be less than exit_final_atr_multiplier ({self.exit_final_atr_multiplier})")
    
    def _validate_regime_detection(self, errors: list) -> None:
        """Validate market regime detection parameters."""
        if self.regime_update_interval < 60:
            errors.append(f"Invalid regime_update_interval {self.regime_update_interval}. Must be at least 60 seconds")
        
        if self.regime_stability_minutes < 1:
            errors.append(f"Invalid regime_stability_minutes {self.regime_stability_minutes}. Must be at least 1")
        
        if self.regime_trending_adx_threshold < 0 or self.regime_trending_adx_threshold > 100:
            errors.append(f"Invalid regime_trending_adx_threshold {self.regime_trending_adx_threshold}. Must be between 0 and 100")
        
        if self.regime_ranging_adx_threshold < 0 or self.regime_ranging_adx_threshold > 100:
            errors.append(f"Invalid regime_ranging_adx_threshold {self.regime_ranging_adx_threshold}. Must be between 0 and 100")
        
        if self.regime_ranging_adx_threshold >= self.regime_trending_adx_threshold:
            errors.append(f"regime_ranging_adx_threshold ({self.regime_ranging_adx_threshold}) must be less than regime_trending_adx_threshold ({self.regime_trending_adx_threshold})")
        
        if self.regime_volatile_atr_percentile < 0 or self.regime_volatile_atr_percentile > 100:
            errors.append(f"Invalid regime_volatile_atr_percentile {self.regime_volatile_atr_percentile}. Must be between 0 and 100")
        
        if self.regime_ranging_atr_percentile < 0 or self.regime_ranging_atr_percentile > 100:
            errors.append(f"Invalid regime_ranging_atr_percentile {self.regime_ranging_atr_percentile}. Must be between 0 and 100")
        
        if self.regime_trending_stop_multiplier <= 0:
            errors.append(f"Invalid regime_trending_stop_multiplier {self.regime_trending_stop_multiplier}. Must be positive")
        
        if self.regime_ranging_stop_multiplier <= 0:
            errors.append(f"Invalid regime_ranging_stop_multiplier {self.regime_ranging_stop_multiplier}. Must be positive")
        
        if self.regime_volatile_size_reduction <= 0 or self.regime_volatile_size_reduction > 1.0:
            errors.append(f"Invalid regime_volatile_size_reduction {self.regime_volatile_size_reduction}. Must be between 0 and 1.0")
        
        if self.regime_volatile_threshold_increase < 0 or self.regime_volatile_threshold_increase > 1.0:
            errors.append(f"Invalid regime_volatile_threshold_increase {self.regime_volatile_threshold_increase}. Must be between 0 and 1.0")
    
    def _validate_performance(self, errors: list) -> None:
        """Validate performance parameters."""
        if self.max_memory_mb < 100:
            errors.append(f"Invalid max_memory_mb {self.max_memory_mb}. Must be at least 100")
        
        if self.ml_prediction_timeout_ms < 10:
            errors.append(f"Invalid ml_prediction_timeout_ms {self.ml_prediction_timeout_ms}. Must be at least 10")
        
        if self.api_rate_limit_per_minute < 100:
            errors.append(f"Invalid api_rate_limit_per_minute {self.api_rate_limit_per_minute}. Must be at least 100")
        
        if self.data_cleanup_interval_hours < 1:
            errors.append(f"Invalid data_cleanup_interval_hours {self.data_cleanup_interval_hours}. Must be at least 1")
        
        # If there are errors, raise ValueError with all error messages
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_message)
    
    def get_applied_defaults(self) -> list:
        """Get list of configuration parameters that used default values.
        
        Returns:
            List of parameter names that used defaults
        """
        return self._applied_defaults.copy()
