"""Verify strategy improvements before deployment."""

import json
import sys

def verify_config():
    """Verify config.json has correct values."""
    print("=" * 60)
    print("VERIFYING CONFIG CHANGES")
    print("=" * 60)
    
    with open('config/config.json', 'r') as f:
        config = json.load(f)
    
    checks = {
        'stop_loss_atr_multiplier': (3.5, 'Initial stop widened to 3.5x ATR'),
        'trailing_stop_atr_multiplier': (2.5, 'Trailing stop tightened to 2.5x ATR'),
        'trailing_stop_activation_atr': (2.0, 'Trailing activation at 2.0x ATR profit'),
        'adx_threshold': (25.0, 'ADX threshold raised to 25.0'),
        'rvol_threshold': (1.2, 'RVOL threshold raised to 1.2')
    }
    
    all_passed = True
    for key, (expected, description) in checks.items():
        actual = config.get(key)
        if actual == expected:
            print(f"✓ {key}: {actual} - {description}")
        else:
            print(f"✗ {key}: Expected {expected}, got {actual}")
            all_passed = False
    
    return all_passed

def verify_position_sizer():
    """Verify position_sizer.py has trailing activation logic."""
    print("\n" + "=" * 60)
    print("VERIFYING POSITION SIZER CHANGES")
    print("=" * 60)
    
    with open('src/position_sizer.py', 'r') as f:
        content = f.read()
    
    checks = [
        ('trailing_stop_activation_atr', 'Activation threshold parameter'),
        ('profit_distance', 'Profit distance calculation'),
        ('if profit_distance <', 'Activation check logic')
    ]
    
    all_passed = True
    for search_str, description in checks:
        if search_str in content:
            print(f"✓ Found: {description}")
        else:
            print(f"✗ Missing: {description}")
            all_passed = False
    
    return all_passed

def verify_strategy():
    """Verify strategy.py has candle-close confirmation."""
    print("\n" + "=" * 60)
    print("VERIFYING STRATEGY CHANGES")
    print("=" * 60)
    
    with open('src/strategy.py', 'r') as f:
        content = f.read()
    
    checks = [
        ('_last_candle_close_time', 'Candle close time tracking'),
        ('_candle_just_closed', 'Candle close flag'),
        ('if not self._candle_just_closed:', 'Candle close check in signal generation')
    ]
    
    all_passed = True
    for search_str, description in checks:
        if search_str in content:
            print(f"✓ Found: {description}")
        else:
            print(f"✗ Missing: {description}")
            all_passed = False
    
    return all_passed

def main():
    """Run all verifications."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "STRATEGY IMPROVEMENTS VERIFICATION" + " " * 13 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    config_ok = verify_config()
    sizer_ok = verify_position_sizer()
    strategy_ok = verify_strategy()
    
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    if config_ok and sizer_ok and strategy_ok:
        print("✓ All checks passed!")
        print("\nReady to deploy with:")
        print("  .\\deploy_strategy_improvements.ps1")
        return 0
    else:
        print("✗ Some checks failed!")
        print("\nPlease fix the issues before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
