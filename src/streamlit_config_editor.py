"""
Streamlit Config Editor

Manages configuration editing with validation.
Provides safe loading and saving of bot configuration.
"""

import json
from typing import Dict, Tuple


class ConfigEditor:
    """Manages configuration editing with validation."""
    
    def __init__(self, config_path: str = "config/config.json"):
        """
        Initialize the config editor.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
    
    def load_config(self) -> Dict:
        """
        Load current configuration.
        
        Returns:
            Dictionary containing configuration data
        """
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
        except Exception:
            return {}
    
    def save_config(self, config: Dict) -> Tuple[bool, str]:
        """
        Save configuration after validation.
        
        Args:
            config: Configuration dictionary to save
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate config
        is_valid, error_msg = self.validate_config(config)
        if not is_valid:
            return False, error_msg
        
        # Save to file
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True, "Configuration saved successfully"
        except Exception as e:
            return False, f"Error saving config: {str(e)}"
    
    def validate_config(self, config: Dict) -> Tuple[bool, str]:
        """
        Validate configuration parameters.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        errors = []
        
        # Validate risk_per_trade
        risk_per_trade = config.get("risk_per_trade", 0)
        if not isinstance(risk_per_trade, (int, float)):
            errors.append("risk_per_trade must be a number")
        elif risk_per_trade <= 0 or risk_per_trade > 1.0:
            errors.append("risk_per_trade must be between 0 and 1.0")
        
        # Validate leverage
        leverage = config.get("leverage", 0)
        if not isinstance(leverage, (int, float)):
            errors.append("leverage must be a number")
        elif leverage < 1 or leverage > 125:
            errors.append("leverage must be between 1 and 125")
        
        # Validate ADX threshold
        adx_threshold = config.get("adx_threshold", 0)
        if not isinstance(adx_threshold, (int, float)):
            errors.append("adx_threshold must be a number")
        elif adx_threshold < 0 or adx_threshold > 100:
            errors.append("adx_threshold must be between 0 and 100")
        
        # Validate RVOL threshold
        rvol_threshold = config.get("rvol_threshold", 0)
        if not isinstance(rvol_threshold, (int, float)):
            errors.append("rvol_threshold must be a number")
        elif rvol_threshold < 0:
            errors.append("rvol_threshold must be positive")
        
        # Validate stop loss percentage
        stop_loss_pct = config.get("stop_loss_pct", 0)
        if not isinstance(stop_loss_pct, (int, float)):
            errors.append("stop_loss_pct must be a number")
        elif stop_loss_pct <= 0 or stop_loss_pct > 1.0:
            errors.append("stop_loss_pct must be between 0 and 1.0")
        
        # Validate take profit percentage
        take_profit_pct = config.get("take_profit_pct", 0)
        if not isinstance(take_profit_pct, (int, float)):
            errors.append("take_profit_pct must be a number")
        elif take_profit_pct <= 0:
            errors.append("take_profit_pct must be positive")
        
        # Validate symbol
        symbol = config.get("symbol", "")
        if not isinstance(symbol, str):
            errors.append("symbol must be a string")
        elif not symbol:
            errors.append("symbol cannot be empty")
        
        # Validate timeframe
        timeframe = config.get("timeframe", "")
        if not isinstance(timeframe, str):
            errors.append("timeframe must be a string")
        elif timeframe not in ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]:
            errors.append("timeframe must be one of: 1m, 5m, 15m, 30m, 1h, 4h, 1d")
        
        if errors:
            return False, "; ".join(errors)
        return True, ""
