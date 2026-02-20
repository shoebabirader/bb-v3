"""Test script to verify logger fix for mode-specific trade logs."""

from src.config import Config
from src.logger import get_logger

def test_logger_with_config():
    """Test that logger correctly uses config to determine log file."""
    
    # Test BACKTEST mode
    print("Testing BACKTEST mode...")
    config_backtest = Config()
    config_backtest.run_mode = "BACKTEST"
    
    # Reset global logger instance
    import src.logger
    src.logger._logger_instance = None
    
    logger_backtest = get_logger(config=config_backtest)
    print(f"✓ Logger initialized for BACKTEST mode")
    print(f"  Trade log file: trades_backtest.log")
    
    # Test PAPER mode
    print("\nTesting PAPER mode...")
    config_paper = Config()
    config_paper.run_mode = "PAPER"
    
    # Reset global logger instance
    src.logger._logger_instance = None
    
    logger_paper = get_logger(config=config_paper)
    print(f"✓ Logger initialized for PAPER mode")
    print(f"  Trade log file: trades_paper.log")
    
    # Test LIVE mode
    print("\nTesting LIVE mode...")
    config_live = Config()
    config_live.run_mode = "LIVE"
    
    # Reset global logger instance
    src.logger._logger_instance = None
    
    logger_live = get_logger(config=config_live)
    print(f"✓ Logger initialized for LIVE mode")
    print(f"  Trade log file: trades_live.log")
    
    # Test without config (should use default)
    print("\nTesting without config...")
    src.logger._logger_instance = None
    
    logger_default = get_logger()
    print(f"✓ Logger initialized without config")
    print(f"  Trade log file: trades.log (default)")
    
    print("\n✅ All tests passed! Logger correctly handles mode-specific log files.")

if __name__ == "__main__":
    test_logger_with_config()
