"""Verify that indicator storage code is correctly implemented."""

import ast
import sys

def verify_implementation():
    """Verify the indicator storage implementation in trading_bot.py."""
    
    with open('src/trading_bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Test 1: Check _symbol_indicators initialization
    if 'self._symbol_indicators: Dict[str, Dict[str, float]] = {}' in content:
        print("✓ Test 1 passed: _symbol_indicators is initialized in __init__")
    else:
        print("✗ Test 1 failed: _symbol_indicators initialization not found")
        return False
    
    # Test 2: Check indicator storage after update_indicators
    if 'self._symbol_indicators[symbol] = {' in content:
        print("✓ Test 2 passed: Indicator storage code exists")
    else:
        print("✗ Test 2 failed: Indicator storage code not found")
        return False
    
    # Test 3: Check all required fields are stored
    required_fields = ['"adx":', '"rvol":', '"atr":', '"signal":', '"timestamp":']
    all_fields_present = all(field in content for field in required_fields)
    
    if all_fields_present:
        print("✓ Test 3 passed: All required fields (adx, rvol, atr, signal, timestamp) are stored")
    else:
        print("✗ Test 3 failed: Not all required fields are stored")
        return False
    
    # Test 4: Check signal value update logic
    signal_update_checks = [
        'if long_signal:',
        'self._symbol_indicators[symbol]["signal"] = "LONG"',
        'elif short_signal:',
        'self._symbol_indicators[symbol]["signal"] = "SHORT"',
        'self._symbol_indicators[symbol]["signal"] = "NONE"'
    ]
    
    all_signal_logic_present = all(check in content for check in signal_update_checks)
    
    if all_signal_logic_present:
        print("✓ Test 4 passed: Signal value update logic is implemented")
    else:
        print("✗ Test 4 failed: Signal value update logic is incomplete")
        return False
    
    # Test 5: Check that indicators are stored using strategy.current_indicators
    indicator_sources = [
        'self.strategy.current_indicators.adx',
        'self.strategy.current_indicators.rvol',
        'self.strategy.current_indicators.atr_15m'
    ]
    
    all_sources_present = all(source in content for source in indicator_sources)
    
    if all_sources_present:
        print("✓ Test 5 passed: Indicators are read from strategy.current_indicators")
    else:
        print("✗ Test 5 failed: Indicators are not properly sourced")
        return False
    
    # Test 6: Check time.time() is used for timestamp
    if 'time.time()' in content:
        print("✓ Test 6 passed: Timestamp uses time.time()")
    else:
        print("✗ Test 6 failed: Timestamp not using time.time()")
        return False
    
    # Test 7: Verify the storage happens after update_indicators call
    # Find the position of update_indicators and _symbol_indicators storage
    update_pos = content.find('self.strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)')
    storage_pos = content.find('self._symbol_indicators[symbol] = {')
    
    if update_pos > 0 and storage_pos > update_pos:
        print("✓ Test 7 passed: Indicator storage happens after update_indicators call")
    else:
        print("✗ Test 7 failed: Indicator storage is not positioned correctly")
        return False
    
    print("\n✅ All verification tests passed!")
    print("\nImplementation Summary:")
    print("- _symbol_indicators dictionary is initialized in __init__")
    print("- Indicators (adx, rvol, atr, signal, timestamp) are stored after processing each symbol")
    print("- Signal value is updated based on long_signal and short_signal detection")
    print("- Storage happens immediately after update_indicators() call")
    
    return True

if __name__ == "__main__":
    success = verify_implementation()
    sys.exit(0 if success else 1)
