"""Diagnose why live trading isn't working on Binance."""

import sys
sys.path.append('src')

from config import Config
from binance.client import Client
from binance.exceptions import BinanceAPIException
import json

print("\n" + "="*80)
print("LIVE TRADING DIAGNOSTIC")
print("="*80 + "\n")

# Load config
config = Config.load_from_file("config/config.json")

print("STEP 1: Check Configuration")
print("-" * 80)
print(f"Current run_mode: {config.run_mode}")
if config.run_mode == "PAPER":
    print("  [WARNING] Bot is in PAPER mode - trades are SIMULATED")
    print("  [ACTION] Change 'run_mode' to 'LIVE' in config.json")
elif config.run_mode == "LIVE":
    print("  [OK] Bot is configured for LIVE trading")
else:
    print(f"  [ERROR] Invalid run_mode: {config.run_mode}")

print(f"\nTrading symbol: {config.symbol}")
print(f"Leverage: {config.leverage}x")
print(f"Risk per trade: {config.risk_per_trade * 100}%")

# Initialize client
print("\n" + "="*80)
print("STEP 2: Test API Connection")
print("-" * 80)

try:
    client = Client(config.api_key, config.api_secret)
    
    # Test 1: Read account
    print("\nTest 1: Read Account Balance")
    try:
        account = client.futures_account()
        balance = float(account['totalWalletBalance'])
        print(f"  [OK] Balance: ${balance:.2f}")
    except BinanceAPIException as e:
        print(f"  [X] FAILED: {e.message} (Code: {e.code})")
        if e.code == -2015:
            print("  [ACTION] Enable 'Enable Reading' permission on Binance")
    
    # Test 2: Read positions
    print("\nTest 2: Read Open Positions")
    try:
        positions = client.futures_position_information(symbol=config.symbol)
        for pos in positions:
            amt = float(pos['positionAmt'])
            if amt != 0:
                print(f"  [OK] Open position: {amt} {config.symbol}")
                print(f"       Entry: ${float(pos['entryPrice']):.4f}")
                print(f"       PnL: ${float(pos['unRealizedProfit']):.2f}")
            else:
                print(f"  [OK] No open position for {config.symbol}")
    except BinanceAPIException as e:
        print(f"  [X] FAILED: {e.message} (Code: {e.code})")
    
    # Test 3: Check order placement permission
    print("\nTest 3: Order Placement Permission")
    try:
        # Try to place a tiny test order (will fail due to size, but tests permission)
        client.futures_create_order(
            symbol=config.symbol,
            side='BUY',
            type='MARKET',
            quantity=0.00001
        )
        print(f"  [OK] Has order placement permission")
    except BinanceAPIException as e:
        if e.code == -2015:
            print(f"  [X] NO PERMISSION TO PLACE ORDERS")
            print(f"  [ACTION] Enable 'Enable Futures' permission on Binance")
        elif e.code in [-1111, -1013, -4164]:
            print(f"  [OK] Has order placement permission")
            print(f"       (Test order rejected for: {e.message})")
        else:
            print(f"  [?] Unknown error: {e.message} (Code: {e.code})")
    
    # Test 4: Check leverage setting
    print("\nTest 4: Leverage Configuration")
    try:
        client.futures_change_leverage(symbol=config.symbol, leverage=config.leverage)
        print(f"  [OK] Leverage set to {config.leverage}x for {config.symbol}")
    except BinanceAPIException as e:
        if e.code == -4028:
            print(f"  [OK] Leverage already set to {config.leverage}x")
        else:
            print(f"  [WARNING] {e.message} (Code: {e.code})")
    
    # Test 5: Check margin type
    print("\nTest 5: Margin Type Configuration")
    try:
        client.futures_change_margin_type(symbol=config.symbol, marginType='ISOLATED')
        print(f"  [OK] Margin type set to ISOLATED for {config.symbol}")
    except BinanceAPIException as e:
        if e.code == -4046:
            print(f"  [OK] Margin type already set to ISOLATED")
        else:
            print(f"  [WARNING] {e.message} (Code: {e.code})")

except Exception as e:
    print(f"\n[ERROR] Failed to connect to Binance: {e}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80 + "\n")

if config.run_mode == "PAPER":
    print("[MAIN ISSUE] Bot is in PAPER mode")
    print()
    print("Your bot is configured for PAPER trading, which means:")
    print("  - Trades are SIMULATED (not real)")
    print("  - No orders are sent to Binance")
    print("  - Your balance doesn't change")
    print("  - This is for testing only")
    print()
    print("TO FIX:")
    print("  1. Open config/config.json")
    print("  2. Change: \"run_mode\": \"PAPER\"")
    print("  3. To:     \"run_mode\": \"LIVE\"")
    print("  4. Save the file")
    print("  5. Restart the bot")
    print()
    print("[WARNING] Make sure API permissions are correct BEFORE switching to LIVE!")
else:
    print("[OK] Bot is configured for LIVE trading")
    print()
    print("If trades still don't execute, check:")
    print("  1. API permissions (Enable Reading + Enable Futures)")
    print("  2. Bot logs for error messages")
    print("  3. Signal conditions are being met")

print("\n" + "="*80 + "\n")
