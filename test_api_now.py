"""Test if API permissions are actually fixed RIGHT NOW."""

from binance.client import Client
from src.config import Config

print("=" * 80)
print("API PERMISSION TEST - RIGHT NOW")
print("=" * 80)
print()

config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)

print("Testing API authentication...")
print()

try:
    # Test 1: Can we access account info?
    print("TEST 1: Futures Account Access")
    print("-" * 80)
    account = client.futures_account()
    balance = float(account['totalWalletBalance'])
    can_trade = account.get('canTrade', False)
    
    print(f"✓ Account access: SUCCESS")
    print(f"  Balance: ${balance:.2f}")
    print(f"  Can Trade: {can_trade}")
    
    if not can_trade:
        print()
        print("✗ FUTURES TRADING IS DISABLED!")
        print("  Go to Binance → API Management")
        print("  Enable 'Enable Futures' permission")
        exit(1)
    
    print()
    
    # Test 2: Can we get position info?
    print("TEST 2: Position Information Access")
    print("-" * 80)
    positions = client.futures_position_information(symbol="XAGUSDT")
    
    if positions:
        leverage = int(positions[0].get('leverage', 0))
        margin_type = positions[0].get('marginType', 'UNKNOWN')
        print(f"✓ Position info access: SUCCESS")
        print(f"  Leverage: {leverage}x")
        print(f"  Margin Type: {margin_type}")
    
    print()
    
    # Test 3: Can we get account trades?
    print("TEST 3: Trade History Access")
    print("-" * 80)
    trades = client.futures_account_trades(symbol="XAGUSDT", limit=1)
    print(f"✓ Trade history access: SUCCESS")
    print(f"  Recent trades: {len(trades)}")
    
    print()
    print("=" * 80)
    print("✅ ALL API TESTS PASSED!")
    print("=" * 80)
    print()
    print("API permissions are correctly configured.")
    print("The bot SHOULD be able to execute trades.")
    print()
    print("If bot still not executing, check:")
    print("  1. Bot terminal for other errors")
    print("  2. Restart bot: Ctrl+C then python main.py")
    print()
    
except Exception as e:
    error_msg = str(e)
    print()
    print("=" * 80)
    print("✗ API TEST FAILED!")
    print("=" * 80)
    print()
    print(f"Error: {error_msg}")
    print()
    
    if "Invalid API-key" in error_msg or "permissions" in error_msg:
        print("🚨 API PERMISSIONS NOT FIXED YET!")
        print()
        print("You need to:")
        print("  1. Go to Binance.com → Profile → API Management")
        print("  2. Find your API key (RbO503406VoV1tbTZtC5...)")
        print("  3. Click 'Edit restrictions'")
        print("  4. Enable 'Enable Futures' permission ✅")
        print("  5. Either:")
        print("     - Set IP access to 'Unrestricted', OR")
        print("     - Add your IP: 223.185.37.235")
        print("  6. Save changes")
        print("  7. Wait 1-2 minutes for changes to take effect")
        print("  8. Run this test again: python test_api_now.py")
        print()
    elif "IP" in error_msg:
        print("🚨 IP RESTRICTION ISSUE!")
        print()
        print("Your IP (223.185.37.235) is not whitelisted.")
        print()
        print("Fix:")
        print("  1. Go to Binance → API Management")
        print("  2. Edit restrictions")
        print("  3. Add IP: 223.185.37.235")
        print("  OR set to 'Unrestricted'")
        print()
    else:
        print("Unknown API error. Check:")
        print("  - API keys are correct")
        print("  - Binance account is verified")
        print("  - Futures trading is enabled on your account")
        print()
    
    exit(1)
