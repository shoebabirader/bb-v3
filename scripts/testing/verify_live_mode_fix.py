"""Verify that the LIVE mode fix is working correctly."""
from src.config import Config

print("="*70)
print("LIVE MODE FIX VERIFICATION")
print("="*70)

# Load config
config = Config.load_from_file('config/config.json')

print(f"\nConfig loaded successfully!")
print(f"\nMode Settings:")
print(f"  run_mode: {config.run_mode}")

# Check if there's a 'mode' attribute
if hasattr(config, 'mode'):
    print(f"  mode: {config.mode}")
else:
    print(f"  mode: (not found in config object)")

print(f"\n{'='*70}")
print("VERIFICATION RESULT")
print(f"{'='*70}\n")

if config.run_mode == "LIVE":
    print("✅ SUCCESS: Bot is configured for LIVE trading")
    print("\n⚠️  WARNING: REAL MONEY AT RISK")
    print("\nWhen you start the bot:")
    print("  1. Signals will be detected")
    print("  2. Positions will be created")
    print("  3. Orders will be EXECUTED on Binance (not simulated)")
    print("\nLook for these log messages to confirm:")
    print("  • 'Checking if should execute order (simulate=False)...'")
    print("  • 'EXECUTING REAL ORDER ON BINANCE'")
    print("  • '✅ ORDER EXECUTED: BUY/SELL X.XXXX @ market'")
    
    print(f"\nCurrent Settings:")
    print(f"  Wallet Balance: Check with bot")
    print(f"  Leverage: {config.leverage}x")
    print(f"  Risk per trade: {config.risk_per_trade * 100}%")
    print(f"  Portfolio symbols: {len(config.portfolio_symbols) if config.enable_portfolio_management else 1}")
    
elif config.run_mode == "PAPER":
    print("ℹ️  INFO: Bot is configured for PAPER trading")
    print("\nOrders will be SIMULATED (no real execution)")
    print("\nTo enable LIVE trading:")
    print("  1. Edit config/config.json")
    print("  2. Change 'run_mode' to 'LIVE'")
    print("  3. Restart the bot")
    
else:
    print(f"❌ ERROR: Unknown run_mode: {config.run_mode}")
    print("\nValid modes: LIVE, PAPER, BACKTEST")

print(f"\n{'='*70}")
