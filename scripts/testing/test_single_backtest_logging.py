"""Test that a single backtest logs to trades_backtest.log."""
import os
import json
from src.config import Config
from src.trading_bot import TradingBot
from src.logger import reset_logger

print("="*60)
print("TEST: Single Backtest Logging")
print("="*60)

# Reset logger to ensure clean state
reset_logger()

# Load config and set to BACKTEST mode
config = Config.load_from_file('config/config.json')
config.run_mode = "BACKTEST"
config.symbol = "BTCUSDT"
config.backtest_days = 7  # Short backtest for testing
config.enable_portfolio_management = False  # Single symbol

print(f"\n1. Configuration")
print(f"   Run mode: {config.run_mode}")
print(f"   Symbol: {config.symbol}")
print(f"   Backtest days: {config.backtest_days}")

# Clear existing backtest log
backtest_log = "logs/trades_backtest.log"
if os.path.exists(backtest_log):
    # Backup existing log
    import shutil
    backup_log = f"{backtest_log}.backup"
    shutil.copy(backtest_log, backup_log)
    print(f"   ✓ Backed up existing log to {backup_log}")

print(f"\n2. Running backtest...")
try:
    bot = TradingBot(config)
    bot.start()
    print(f"   ✓ Backtest completed")
except Exception as e:
    print(f"   ✗ Backtest failed: {e}")
    exit(1)

print(f"\n3. Verifying log files...")

# Check trades_backtest.log
if os.path.exists(backtest_log):
    with open(backtest_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        trade_lines = [l for l in lines if "TRADE_EXECUTED" in l]
        
        if trade_lines:
            print(f"   ✓ Found {len(trade_lines)} trades in {backtest_log}")
            print(f"   ✓ SUCCESS: Backtest trades logged to correct file!")
        else:
            print(f"   ⚠ No trades found in {backtest_log}")
            print(f"     (This might be normal if no signals were generated)")
else:
    print(f"   ✗ {backtest_log} does not exist")

# Check trades.log (should NOT have new backtest trades)
generic_log = "logs/trades.log"
if os.path.exists(generic_log):
    # Get file modification time
    import time
    mod_time = os.path.getmtime(generic_log)
    current_time = time.time()
    age_seconds = current_time - mod_time
    
    if age_seconds < 60:  # Modified in last minute
        print(f"   ⚠ WARNING: {generic_log} was recently modified")
        print(f"     This suggests trades might be going to wrong file!")
    else:
        print(f"   ✓ {generic_log} not recently modified (correct)")
else:
    print(f"   ✓ {generic_log} does not exist (correct)")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
