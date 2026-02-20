"""Test script to verify indicator storage implementation."""

import sys
import time
from unittest.mock import Mock, MagicMock

# Mock the imports before importing trading_bot
sys.modules['binance.client'] = MagicMock()
sys.modules['pynput'] = MagicMock()
sys.modules['pynput.keyboard'] = MagicMock()

from src.trading_bot import TradingBot
from src.config import Config

def test_indicator_storage():
    """Test that _symbol_indicators dictionary is properly initialized and used."""
    
    # Create a mock config
    config = Mock(spec=Config)
    config.api_key = "test_key"
    config.api_secret = "test_secret"
    config.testnet = True
    config.mode = "paper"
    config.symbols = ["BTCUSDT", "ETHUSDT"]
    config.enable_multi_timeframe = False
    config.enable_portfolio_management = False
    
    # Create bot instance
    bot = TradingBot(config)
    
    # Test 1: Verify _symbol_indicators is initialized
    assert hasattr(bot, '_symbol_indicators'), "Bot should have _symbol_indicators attribute"
    assert isinstance(bot._symbol_indicators, dict), "_symbol_indicators should be a dictionary"
    assert len(bot._symbol_indicators) == 0, "_symbol_indicators should be empty initially"
    print("✓ Test 1 passed: _symbol_indicators is initialized correctly")
    
    # Test 2: Verify we can store indicator data
    test_symbol = "BTCUSDT"
    test_data = {
        "adx": 45.5,
        "rvol": 1.2,
        "atr": 0.0099,
        "signal": "LONG",
        "timestamp": time.time()
    }
    
    bot._symbol_indicators[test_symbol] = test_data
    assert test_symbol in bot._symbol_indicators, "Symbol should be in _symbol_indicators"
    assert bot._symbol_indicators[test_symbol]["adx"] == 45.5, "ADX value should match"
    assert bot._symbol_indicators[test_symbol]["signal"] == "LONG", "Signal should match"
    print("✓ Test 2 passed: Can store indicator data")
    
    # Test 3: Verify we can update signal value
    bot._symbol_indicators[test_symbol]["signal"] = "SHORT"
    assert bot._symbol_indicators[test_symbol]["signal"] == "SHORT", "Signal should be updated"
    print("✓ Test 3 passed: Can update signal value")
    
    # Test 4: Verify multiple symbols can be stored
    test_symbol2 = "ETHUSDT"
    test_data2 = {
        "adx": 32.1,
        "rvol": 0.8,
        "atr": 0.0045,
        "signal": "NONE",
        "timestamp": time.time()
    }
    
    bot._symbol_indicators[test_symbol2] = test_data2
    assert len(bot._symbol_indicators) == 2, "Should have 2 symbols stored"
    assert test_symbol2 in bot._symbol_indicators, "Second symbol should be stored"
    print("✓ Test 4 passed: Multiple symbols can be stored")
    
    print("\n✅ All tests passed! Indicator storage implementation is working correctly.")

if __name__ == "__main__":
    test_indicator_storage()
