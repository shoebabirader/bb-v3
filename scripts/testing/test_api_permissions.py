"""Test if API key has sufficient permissions for live trading."""

import sys
sys.path.append('src')

from config import Config
from binance.client import Client
from binance.exceptions import BinanceAPIException

print("\n" + "="*80)
print("BINANCE API PERMISSIONS TEST")
print("="*80 + "\n")

# Load config
config = Config.load_from_file("config/config.json")

print(f"Testing API Key: {config.api_key[:15]}...\n")

# Initialize client
client = Client(config.api_key, config.api_secret)

# Test 1: Can read account info
print("Test 1: Read Account Information")
try:
    account = client.futures_account()
    balance = float(account['totalWalletBalance'])
    print(f"  ✓ SUCCESS: Can read account")
    print(f"    Balance: ${balance:.2f}")
except BinanceAPIException as e:
    print(f"  ✗ FAILED: {e.message}")
    print(f"    Error code: {e.code}")
except Exception as e:
    print(f"  ✗ FAILED: {e}")

# Test 2: Can read positions
print("\nTest 2: Read Open Positions")
try:
    positions = client.futures_position_information()
    open_positions = [p for p in positions if float(p['positionAmt']) != 0]
    print(f"  ✓ SUCCESS: Can read positions")
    print(f"    Open positions: {len(open_positions)}")
except BinanceAPIException as e:
    print(f"  ✗ FAILED: {e.message}")
    print(f"    Error code: {e.code}")
except Exception as e:
    print(f"  ✗ FAILED: {e}")

# Test 3: Can place test order (this will fail if no permissions)
print("\nTest 3: Order Placement Permission")
print("  (Testing with a tiny test order that will be rejected for other reasons)")
try:
    # Try to place a test order with invalid quantity to test permissions
    # This will fail due to quantity, but we'll see if it's a permission error
    client.futures_create_order(
        symbol=config.symbol,
        side='BUY',
        type='MARKET',
        quantity=0.00001  # Intentionally too small
    )
    print(f"  ✓ SUCCESS: Has order placement permission")
except BinanceAPIException as e:
    if e.code == -2015:
        print(f"  ✗ FAILED: NO PERMISSION TO PLACE ORDERS")
        print(f"    Error: {e.message}")
        print(f"\n  🔧 FIX REQUIRED:")
        print(f"    1. Go to Binance.com → API Management")
        print(f"    2. Edit your API key")
        print(f"    3. Enable 'Enable Futures' permission")
        print(f"    4. Save and wait 1-2 minutes")
    elif e.code == -1111 or e.code == -1013:
        # Precision or quantity errors mean we HAVE permission but order is invalid
        print(f"  ✓ SUCCESS: Has order placement permission")
        print(f"    (Order rejected for: {e.message})")
    else:
        print(f"  ? UNKNOWN: {e.message}")
        print(f"    Error code: {e.code}")
except Exception as e:
    print(f"  ? UNKNOWN ERROR: {e}")

# Test 4: Check API restrictions
print("\nTest 4: API Key Restrictions")
try:
    api_info = client.get_account_api_trading_status()
    print(f"  API Trading Status:")
    print(f"    {api_info}")
except Exception as e:
    print(f"  Could not retrieve API restrictions: {e}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80 + "\n")

print("For LIVE trading to work, you need:")
print("  ✓ Read account permission (Test 1)")
print("  ✓ Read positions permission (Test 2)")
print("  ✓ Place orders permission (Test 3) ← MOST IMPORTANT")
print("\nIf Test 3 shows 'NO PERMISSION', you MUST enable 'Enable Futures'")
print("permission on your Binance API key.")
print("\n⚠️  Once permissions are fixed, bot will place REAL orders!")
print("\n" + "="*80 + "\n")
