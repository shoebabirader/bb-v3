"""Diagnose if bot is actually placing real orders or simulating."""

import sys
sys.path.append('src')

from config import Config
from order_executor import OrderExecutor
from binance.client import Client

print("\n" + "="*80)
print("LIVE vs PAPER TRADING DIAGNOSIS")
print("="*80 + "\n")

# Load config
config = Config.load_from_file("config/config.json")

print("Configuration:")
print(f"  run_mode: {config.run_mode}")
print(f"  symbol: {config.symbol}")
print(f"  API Key: {config.api_key[:10]}..." if config.api_key else "  API Key: NOT SET")
print(f"  API Secret: {config.api_secret[:10]}..." if config.api_secret else "  API Secret: NOT SET")

# Initialize client
if config.api_key and config.api_secret:
    client = Client(config.api_key, config.api_secret)
    print("\n✓ Binance client initialized")
    
    # Test API connection
    try:
        account = client.futures_account()
        balance = float(account['totalWalletBalance'])
        print(f"✓ API connection successful")
        print(f"  Wallet Balance: ${balance:.2f}")
        
        # Check if testnet
        if hasattr(client, 'API_URL'):
            print(f"  API URL: {client.API_URL}")
            if 'testnet' in client.API_URL.lower():
                print("  ⚠️  WARNING: Connected to TESTNET!")
            else:
                print("  ✓ Connected to MAINNET (real trading)")
    except Exception as e:
        print(f"✗ API connection failed: {e}")
else:
    print("\n✗ API keys not configured")

# Initialize OrderExecutor
order_executor = OrderExecutor(config, client if config.api_key else None)

print("\nOrderExecutor Status:")
print(f"  Has client: {order_executor.client is not None}")
print(f"  Run mode: {order_executor.config.run_mode}")

# Check the _run_live_trading method
print("\n" + "-"*80)
print("CHECKING BOT CODE")
print("-"*80 + "\n")

# Read the trading_bot.py file to check simulate_execution parameter
with open('src/trading_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
    # Find _run_live_trading method
    if '_run_live_trading' in content:
        print("✓ Found _run_live_trading method")
        
        # Check if it calls _run_event_loop with simulate_execution=False
        if '_run_event_loop(simulate_execution=False)' in content:
            print("✓ _run_live_trading calls _run_event_loop(simulate_execution=False)")
        else:
            print("✗ _run_live_trading does NOT call _run_event_loop with simulate_execution=False")
            print("  This is the BUG!")
    
    # Find _run_paper_trading method
    if '_run_paper_trading' in content:
        print("✓ Found _run_paper_trading method")
        
        # Check if it calls _run_event_loop with simulate_execution=True
        if '_run_event_loop(simulate_execution=True)' in content:
            print("✓ _run_paper_trading calls _run_event_loop(simulate_execution=True)")

print("\n" + "-"*80)
print("DIAGNOSIS")
print("-"*80 + "\n")

if config.run_mode == "LIVE":
    print("Config says: LIVE mode")
    print("Expected behavior: Real orders placed on Binance")
    print("\nIf orders are NOT appearing on Binance, possible causes:")
    print("  1. Bot is somehow running in PAPER mode despite config")
    print("  2. Order placement is failing silently")
    print("  3. API permissions don't allow order placement")
    print("  4. Orders are being placed but immediately cancelled")
elif config.run_mode == "PAPER":
    print("Config says: PAPER mode")
    print("Expected behavior: Simulated orders (no real trades)")
    print("\n⚠️  WARNING: You think you're in LIVE but config says PAPER!")
else:
    print(f"Config says: {config.run_mode} mode")

print("\n" + "="*80 + "\n")
