"""Verify bot is ready for LIVE trading."""

import json
import sys
import os

print("\n" + "="*80)
print("LIVE TRADING READINESS CHECK")
print("="*80 + "\n")

# Check 1: Config file
print("CHECK 1: Configuration File")
print("-" * 80)

try:
    with open('config/config.json', 'r') as f:
        config = json.load(f)
    
    run_mode = config.get('run_mode', 'UNKNOWN')
    trailing_stop = config.get('trailing_stop_atr_multiplier', 0)
    stop_loss = config.get('stop_loss_atr_multiplier', 0)
    
    if run_mode == "LIVE":
        print("[OK] run_mode = LIVE")
    else:
        print(f"[X] run_mode = {run_mode} (should be LIVE)")
    
    if trailing_stop >= stop_loss:
        print(f"[OK] Trailing stop ({trailing_stop}) >= Stop loss ({stop_loss})")
    else:
        print(f"[X] Trailing stop ({trailing_stop}) < Stop loss ({stop_loss})")
        print("    This will stop you out too early!")
    
    print(f"\nSymbol: {config.get('symbol', 'UNKNOWN')}")
    print(f"Leverage: {config.get('leverage', 0)}x")
    print(f"Risk per trade: {config.get('risk_per_trade', 0) * 100}%")
    
except Exception as e:
    print(f"[X] Error reading config: {e}")

# Check 2: Bot logs
print("\n" + "="*80)
print("CHECK 2: Recent Bot Logs")
print("-" * 80)

try:
    if os.path.exists('logs/bot.log'):
        with open('logs/bot.log', 'r') as f:
            lines = f.readlines()
        
        # Check last 100 lines for mode initialization
        recent_lines = lines[-100:] if len(lines) > 100 else lines
        
        found_paper = False
        found_live = False
        
        for line in recent_lines:
            if 'TradingBot initialized in PAPER mode' in line:
                found_paper = True
            if 'TradingBot initialized in LIVE mode' in line:
                found_live = True
        
        if found_live:
            print("[OK] Bot was last started in LIVE mode")
        elif found_paper:
            print("[X] Bot was last started in PAPER mode")
            print("    YOU MUST RESTART THE BOT!")
        else:
            print("[?] Could not determine bot mode from logs")
            print("    Bot may not have been started yet")
    else:
        print("[?] No bot.log file found")
        print("    Bot has not been started yet")

except Exception as e:
    print(f"[X] Error reading logs: {e}")

# Check 3: API permissions
print("\n" + "="*80)
print("CHECK 3: API Permissions")
print("-" * 80)

try:
    sys.path.append('src')
    from config import Config
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    
    config_obj = Config.load_from_file("config/config.json")
    client = Client(config_obj.api_key, config_obj.api_secret)
    
    # Test account access
    try:
        account = client.futures_account()
        balance = float(account['totalWalletBalance'])
        print(f"[OK] Can read account (Balance: ${balance:.2f})")
    except BinanceAPIException as e:
        print(f"[X] Cannot read account: {e.message}")
    
    # Test order permission (will fail on quantity, but tests permission)
    try:
        client.futures_create_order(
            symbol=config_obj.symbol,
            side='BUY',
            type='MARKET',
            quantity=0.00001
        )
        print("[OK] Has order placement permission")
    except BinanceAPIException as e:
        if e.code == -2015:
            print("[X] NO PERMISSION to place orders")
            print("    Enable 'Enable Futures' on Binance")
        elif e.code in [-1111, -1013, -1102, -4164]:
            print("[OK] Has order placement permission")
        else:
            print(f"[?] Unknown error: {e.message}")

except Exception as e:
    print(f"[X] Error testing API: {e}")

# Final summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80 + "\n")

all_good = True

if run_mode != "LIVE":
    print("[X] Config is not set to LIVE mode")
    all_good = False

if trailing_stop < stop_loss:
    print("[X] Trailing stop is too tight")
    all_good = False

if found_paper and not found_live:
    print("[X] Bot is running in PAPER mode")
    print("    YOU MUST RESTART: python main.py")
    all_good = False

if all_good:
    print("[OK] Everything looks good!")
    print()
    print("If bot is not running, start it with:")
    print("  python main.py")
    print()
    print("You should see:")
    print("  LIVE TRADING MODE ACTIVATED")
    print("  [WARNING] REAL MONEY AT RISK [WARNING]")
else:
    print("\n[ACTION REQUIRED]")
    print("1. Fix any issues above")
    print("2. Restart the bot: python main.py")
    print("3. Run this script again to verify")

print("\n" + "="*80 + "\n")
