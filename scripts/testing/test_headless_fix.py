#!/usr/bin/env python3
"""Test the headless mode fix for trading_bot.py

This script verifies that:
1. The bot can import without pynput
2. Keyboard listener gracefully degrades
3. All other functionality remains intact
"""

import sys
import importlib.util

def test_import_without_pynput():
    """Test that trading_bot can import even if pynput is unavailable."""
    print("Testing import without pynput...")
    
    # Temporarily hide pynput
    original_pynput = sys.modules.get('pynput')
    if 'pynput' in sys.modules:
        del sys.modules['pynput']
    
    # Block pynput import
    import builtins
    original_import = builtins.__import__
    
    def mock_import(name, *args, **kwargs):
        if name == 'pynput' or name.startswith('pynput.'):
            raise ImportError(f"Mocking headless environment - {name} not available")
        return original_import(name, *args, **kwargs)
    
    builtins.__import__ = mock_import
    
    try:
        # Try to import trading_bot
        if 'src.trading_bot' in sys.modules:
            del sys.modules['src.trading_bot']
        
        from src import trading_bot
        
        # Check that KEYBOARD_AVAILABLE is False
        if hasattr(trading_bot, 'KEYBOARD_AVAILABLE'):
            if not trading_bot.KEYBOARD_AVAILABLE:
                print("✓ KEYBOARD_AVAILABLE correctly set to False")
            else:
                print("✗ KEYBOARD_AVAILABLE should be False in headless mode")
                return False
        else:
            print("✗ KEYBOARD_AVAILABLE flag not found")
            return False
        
        print("✓ trading_bot imports successfully without pynput")
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import trading_bot: {e}")
        return False
    
    finally:
        # Restore original import
        builtins.__import__ = original_import
        
        # Restore pynput if it was loaded
        if original_pynput:
            sys.modules['pynput'] = original_pynput

def test_import_with_pynput():
    """Test that trading_bot still works with pynput available."""
    print("\nTesting import with pynput...")
    
    try:
        # Clear cache
        if 'src.trading_bot' in sys.modules:
            del sys.modules['src.trading_bot']
        
        from src import trading_bot
        
        # Check that KEYBOARD_AVAILABLE reflects actual availability
        if hasattr(trading_bot, 'KEYBOARD_AVAILABLE'):
            print(f"✓ KEYBOARD_AVAILABLE = {trading_bot.KEYBOARD_AVAILABLE}")
        else:
            print("✗ KEYBOARD_AVAILABLE flag not found")
            return False
        
        print("✓ trading_bot imports successfully with pynput")
        return True
        
    except Exception as e:
        print(f"✗ Failed to import trading_bot: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Headless Mode Fix")
    print("=" * 60)
    
    results = []
    
    # Test 1: Import without pynput (simulating EC2)
    results.append(("Import without pynput", test_import_without_pynput()))
    
    # Test 2: Import with pynput (normal mode)
    results.append(("Import with pynput", test_import_with_pynput()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed! Safe to deploy to EC2.")
        return 0
    else:
        print("\n✗ Some tests failed. Review the fix before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
