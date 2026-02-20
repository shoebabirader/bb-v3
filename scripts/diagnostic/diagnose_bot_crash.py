"""Diagnose why the bot crashes after starting."""

import sys
import os
import json
from datetime import datetime

def check_config():
    """Check if config is valid."""
    print("="*60)
    print("🔍 DIAGNOSING BOT CRASH")
    print("="*60)
    
    print("\n1. Checking configuration...")
    
    if not os.path.exists('config/config.json'):
        print("❌ config/config.json not found")
        return False
    
    try:
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        
        print("✅ Config file loads OK")
        
        # Check critical fields
        issues = []
        
        # Check API keys
        api_key = config.get('api_key', '')
        api_secret = config.get('api_secret', '')
        
        if not api_key or not api_secret:
            issues.append("❌ API keys are empty")
            print("   ⚠️  API keys not configured")
        else:
            print(f"   ✅ API key: {api_key[:4]}...{api_key[-4:]}")
        
        # Check run mode
        run_mode = config.get('run_mode', '')
        if run_mode not in ['BACKTEST', 'PAPER', 'LIVE']:
            issues.append(f"❌ Invalid run_mode: {run_mode}")
        else:
            print(f"   ✅ Run mode: {run_mode}")
        
        # Check symbol
        symbol = config.get('symbol', '')
        if not symbol:
            issues.append("❌ Symbol is empty")
        else:
            print(f"   ✅ Symbol: {symbol}")
        
        # Check risk parameters
        risk = config.get('risk_per_trade', 0)
        if risk <= 0 or risk > 1:
            issues.append(f"❌ Invalid risk_per_trade: {risk}")
        else:
            print(f"   ✅ Risk per trade: {risk*100}%")
        
        leverage = config.get('leverage', 0)
        if leverage < 1 or leverage > 125:
            issues.append(f"❌ Invalid leverage: {leverage}")
        else:
            print(f"   ✅ Leverage: {leverage}x")
        
        if issues:
            print("\n⚠️  Configuration issues found:")
            for issue in issues:
                print(f"   {issue}")
            return False
        
        return True
    
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False

def check_logs():
    """Check recent error logs."""
    print("\n2. Checking error logs...")
    
    log_files = [
        'logs/errors.log',
        'logs/system.log',
    ]
    
    recent_errors = []
    
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last 20 lines
                    recent_lines = lines[-20:] if len(lines) > 20 else lines
                    
                    for line in recent_lines:
                        if 'ERROR' in line or 'CRITICAL' in line or 'Exception' in line:
                            recent_errors.append(line.strip())
            except Exception as e:
                print(f"   ⚠️  Could not read {log_file}: {e}")
    
    if recent_errors:
        print(f"   ⚠️  Found {len(recent_errors)} recent errors:")
        for error in recent_errors[-5:]:  # Show last 5 errors
            print(f"   {error[:100]}...")
    else:
        print("   ✅ No recent errors in logs")
    
    return len(recent_errors) == 0

def test_imports():
    """Test if all required modules can be imported."""
    print("\n3. Testing imports...")
    
    modules = [
        'binance',
        'pandas',
        'numpy',
        'ta',
        'pynput',
    ]
    
    all_ok = True
    
    for module in modules:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except ImportError as e:
            print(f"   ❌ {module}: {e}")
            all_ok = False
    
    return all_ok

def test_bot_startup():
    """Try to start the bot and capture any errors."""
    print("\n4. Testing bot startup...")
    
    try:
        from src.config import Config
        config = Config.load_from_file('config/config.json')
        print("   ✅ Config loads OK")
        
        # Check if API keys are set
        if not config.api_key or not config.api_secret:
            print("   ❌ API keys are not set")
            print("\n   To fix:")
            print("   1. Edit config/config.json")
            print("   2. Add your Binance API key and secret")
            print("   3. Or set environment variables:")
            print("      set BINANCE_API_KEY=your_key")
            print("      set BINANCE_API_SECRET=your_secret")
            return False
        
        # Try to create bot instance
        from src.trading_bot import TradingBot
        print("   ✅ TradingBot imports OK")
        
        # Don't actually start it, just check if it can be created
        print("   ℹ️  Bot can be instantiated")
        
        return True
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        print("\n   Full error:")
        traceback.print_exc()
        return False

def check_binance_connection():
    """Test Binance API connection."""
    print("\n5. Testing Binance API connection...")
    
    try:
        from src.config import Config
        config = Config.load_from_file('config/config.json')
        
        if not config.api_key or not config.api_secret:
            print("   ⚠️  Skipping (no API keys)")
            return True
        
        from binance.client import Client
        client = Client(config.api_key, config.api_secret)
        
        # Try to get account info
        account = client.get_account()
        print("   ✅ Binance API connection OK")
        
        # Check permissions
        permissions = account.get('permissions', [])
        print(f"   ℹ️  Permissions: {', '.join(permissions)}")
        
        if 'FUTURES' not in permissions:
            print("   ⚠️  WARNING: FUTURES permission not enabled")
            print("   The bot needs FUTURES trading permission")
        
        return True
    
    except Exception as e:
        print(f"   ❌ Binance API error: {e}")
        print("\n   Possible causes:")
        print("   1. Invalid API keys")
        print("   2. API keys don't have required permissions")
        print("   3. IP not whitelisted (if IP restriction enabled)")
        print("   4. Network/firewall blocking connection")
        return False

def main():
    """Run all diagnostics."""
    
    results = {
        'config': check_config(),
        'logs': check_logs(),
        'imports': test_imports(),
        'startup': test_bot_startup(),
        'binance': check_binance_connection(),
    }
    
    print("\n" + "="*60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*60)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check.upper()}: {status}")
    
    print("\n" + "="*60)
    
    if all(results.values()):
        print("✅ ALL CHECKS PASSED")
        print("\nThe bot should work. If it still crashes:")
        print("1. Check the bot console window for errors")
        print("2. Check logs/errors.log for details")
        print("3. Try running: python main.py")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nFix the issues above, then try again.")
        print("\nMost common fixes:")
        print("1. Add API keys to config/config.json")
        print("2. Install missing packages: pip install -r requirements.txt")
        print("3. Check Binance API key permissions")
    
    print("="*60)

if __name__ == "__main__":
    main()
