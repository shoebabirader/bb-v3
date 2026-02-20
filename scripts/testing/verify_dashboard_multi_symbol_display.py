"""
Verification script for multi-symbol indicator display on dashboard.

This script verifies that:
1. All symbols show non-zero indicators in binance_results.json
2. The dashboard code correctly reads and displays the data
3. Signal indicators (LONG/SHORT/NONE) are present
"""

import json
import sys
from pathlib import Path


def verify_binance_results():
    """Verify binance_results.json has proper multi-symbol data."""
    print("=" * 60)
    print("VERIFICATION: Multi-Symbol Indicator Display")
    print("=" * 60)
    print()
    
    # Read binance_results.json
    results_path = Path("binance_results.json")
    if not results_path.exists():
        print("❌ FAIL: binance_results.json not found")
        return False
    
    try:
        with open(results_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ FAIL: Invalid JSON in binance_results.json: {e}")
        return False
    
    print("✅ binance_results.json found and readable")
    print()
    
    # Check for symbols_data array
    symbols_data = data.get('symbols_data', [])
    if not symbols_data:
        print("❌ FAIL: No symbols_data array found")
        return False
    
    print(f"✅ Found {len(symbols_data)} symbols in symbols_data")
    print()
    
    # Verify each symbol has required fields
    all_passed = True
    required_fields = ['symbol', 'current_price', 'adx', 'rvol', 'atr', 'signal']
    
    print("Checking each symbol for required indicators:")
    print("-" * 60)
    
    for idx, symbol_info in enumerate(symbols_data, 1):
        symbol = symbol_info.get('symbol', 'UNKNOWN')
        print(f"\n{idx}. {symbol}")
        
        # Check all required fields exist
        missing_fields = [field for field in required_fields if field not in symbol_info]
        if missing_fields:
            print(f"   ❌ Missing fields: {', '.join(missing_fields)}")
            all_passed = False
            continue
        
        # Check for non-zero indicators
        adx = symbol_info.get('adx', 0.0)
        rvol = symbol_info.get('rvol', 0.0)
        atr = symbol_info.get('atr', 0.0)
        signal = symbol_info.get('signal', 'NONE')
        price = symbol_info.get('current_price', 0.0)
        
        print(f"   Price: ${price:.4f}")
        print(f"   ADX: {adx:.2f}", end="")
        if adx > 0:
            print(" ✅")
        else:
            print(" ⚠️ (zero)")
            all_passed = False
        
        print(f"   RVOL: {rvol:.2f}", end="")
        if rvol > 0:
            print(" ✅")
        else:
            print(" ⚠️ (zero)")
            all_passed = False
        
        print(f"   ATR: {atr:.6f}", end="")
        if atr > 0:
            print(" ✅")
        else:
            print(" ⚠️ (zero)")
            all_passed = False
        
        print(f"   Signal: {signal}", end="")
        if signal in ['LONG', 'SHORT', 'NONE']:
            print(" ✅")
        else:
            print(f" ❌ (invalid: {signal})")
            all_passed = False
    
    print()
    print("-" * 60)
    
    return all_passed


def verify_dashboard_code():
    """Verify dashboard code correctly handles multi-symbol data."""
    print()
    print("Checking dashboard code implementation:")
    print("-" * 60)
    
    # Read streamlit_app.py
    app_path = Path("streamlit_app.py")
    if not app_path.exists():
        print("❌ FAIL: streamlit_app.py not found")
        return False
    
    with open(app_path, 'r', encoding='utf-8') as f:
        app_code = f.read()
    
    # Check for symbols_data handling
    checks = [
        ("symbols_data = results.get('symbols_data'", "Reading symbols_data from results"),
        ("for symbol_info in symbols_data:", "Iterating over symbols_data"),
        ("symbol_info.get('adx'", "Reading ADX from symbol_info"),
        ("symbol_info.get('rvol'", "Reading RVOL from symbol_info"),
        ("symbol_info.get('atr'", "Reading ATR from symbol_info"),
        ("symbol_info.get('signal'", "Reading signal from symbol_info"),
    ]
    
    all_passed = True
    for code_snippet, description in checks:
        if code_snippet in app_code:
            print(f"✅ {description}")
        else:
            print(f"❌ {description}")
            all_passed = False
    
    print("-" * 60)
    return all_passed


def verify_data_provider():
    """Verify StreamlitDataProvider correctly exposes data."""
    print()
    print("Checking StreamlitDataProvider implementation:")
    print("-" * 60)
    
    # Read streamlit_data_provider.py
    provider_path = Path("src/streamlit_data_provider.py")
    if not provider_path.exists():
        print("❌ FAIL: src/streamlit_data_provider.py not found")
        return False
    
    with open(provider_path, 'r', encoding='utf-8') as f:
        provider_code = f.read()
    
    # Check that it reads from results file
    checks = [
        ("self._read_cached_json(self.results_path", "Reading results file with caching"),
        ("_cache_ttl = 5", "Cache TTL set to 5 seconds"),
    ]
    
    all_passed = True
    for code_snippet, description in checks:
        if code_snippet in provider_code:
            print(f"✅ {description}")
        else:
            print(f"❌ {description}")
            all_passed = False
    
    print("-" * 60)
    return all_passed


def main():
    """Run all verification checks."""
    results_ok = verify_binance_results()
    dashboard_ok = verify_dashboard_code()
    provider_ok = verify_data_provider()
    
    print()
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    if results_ok:
        print("✅ binance_results.json: All symbols have non-zero indicators")
    else:
        print("❌ binance_results.json: Some symbols missing or have zero indicators")
    
    if dashboard_ok:
        print("✅ Dashboard code: Correctly reads and displays multi-symbol data")
    else:
        print("❌ Dashboard code: Missing multi-symbol handling")
    
    if provider_ok:
        print("✅ Data provider: Correctly configured with 5-second refresh")
    else:
        print("❌ Data provider: Configuration issues")
    
    print()
    
    if results_ok and dashboard_ok and provider_ok:
        print("🎉 ALL CHECKS PASSED!")
        print()
        print("Next steps:")
        print("1. Start the bot: python main.py")
        print("2. Wait 30 seconds for all symbols to be processed")
        print("3. Open dashboard: streamlit run streamlit_app.py")
        print("4. Navigate to 'Market Data' tab")
        print("5. Verify all symbols show non-zero indicators")
        print("6. Verify indicators update every 5 seconds")
        return 0
    else:
        print("⚠️ SOME CHECKS FAILED - Review output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
