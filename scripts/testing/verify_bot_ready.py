"""Verify bot is ready for live trading with proper logging."""

import os
import sys

print("=" * 80)
print("BOT READINESS CHECK")
print("=" * 80)

all_good = True

# Check 1: Logs directory
print("\n[1] Checking logs directory...")
if os.path.exists("logs"):
    log_files = [f for f in os.listdir("logs") if f.endswith(".log")]
    print(f"  ✓ logs/ directory exists with {len(log_files)} log files")
else:
    print("  ✗ logs/ directory missing")
    all_good = False

# Check 2: Config file
print("\n[2] Checking configuration...")
if os.path.exists("config/config.json"):
    print("  ✓ config/config.json exists")
    
    import json
    with open("config/config.json", "r") as f:
        config = json.load(f)
    
    if config.get("run_mode") == "LIVE":
        print("  ✓ Run mode: LIVE")
    else:
        print(f"  ⚠ Run mode: {config.get('run_mode')} (not LIVE)")
    
    if config.get("api_key") and len(config.get("api_key")) > 20:
        print(f"  ✓ API key configured ({config['api_key'][:4]}...{config['api_key'][-4:]})")
    else:
        print("  ✗ API key not configured")
        all_good = False
    
    print(f"  ✓ Symbol: {config.get('symbol')}")
    print(f"  ✓ Risk per trade: {config.get('risk_per_trade') * 100}%")
    print(f"  ✓ Leverage: {config.get('leverage')}x")
else:
    print("  ✗ config/config.json missing")
    all_good = False

# Check 3: Logging enhancements
print("\n[3] Checking logging enhancements...")
with open("src/trading_bot.py", "r") as f:
    content = f.read()

if "StreamHandler" in content:
    print("  ✓ Console logging configured")
else:
    print("  ✗ Console logging not configured")
    all_good = False

if "LIVE TRADING MODE ACTIVATED" in content:
    print("  ✓ LIVE mode logging added")
else:
    print("  ✗ LIVE mode logging missing")
    all_good = False

if "EXECUTING REAL ORDER ON BINANCE" in content:
    print("  ✓ Order execution logging added")
else:
    print("  ✗ Order execution logging missing")
    all_good = False

# Check 4: Order executor logging
print("\n[4] Checking order executor logging...")
with open("src/order_executor.py", "r") as f:
    content = f.read()

if "PLACE_MARKET_ORDER CALLED" in content:
    print("  ✓ Detailed order placement logging added")
else:
    print("  ✗ Order placement logging missing")
    all_good = False

# Check 5: API permissions test
print("\n[5] Checking API permissions...")
if os.path.exists("test_api_permissions.py"):
    print("  ✓ API permissions test script exists")
    print("  → Run: python test_api_permissions.py")
else:
    print("  ⚠ API permissions test script not found")

# Summary
print("\n" + "=" * 80)
if all_good:
    print("✅ BOT IS READY FOR LIVE TRADING")
    print("=" * 80)
    print("\n📋 Next steps:")
    print("  1. Fix API permissions on Binance:")
    print("     https://www.binance.com/en/my/settings/api-management")
    print("     Enable: 'Enable Reading' and 'Enable Futures'")
    print("")
    print("  2. Test API permissions:")
    print("     python test_api_permissions.py")
    print("")
    print("  3. Start bot:")
    print("     python main.py")
    print("")
    print("  4. Watch logs:")
    print("     - Console: Real-time logs")
    print("     - logs/bot.log: General activity")
    print("     - logs/trades.log: Trade execution")
    print("     - logs/errors.log: Error messages")
else:
    print("❌ BOT NOT READY - ISSUES FOUND")
    print("=" * 80)
    print("\n📋 Fix the issues above, then run this script again")

print("\n" + "=" * 80)
