"""Test script to verify backtest logging fix."""
import os
from src.config import Config
from src.logger import get_logger
from src.models import Trade
from datetime import datetime

# Test 1: Create logger for BACKTEST mode
print("="*60)
print("TEST 1: Logger initialization for BACKTEST mode")
print("="*60)

config = Config()
config.run_mode = "BACKTEST"
config.symbol = "BTCUSDT"

logger = get_logger(config=config)
print(f"✓ Logger initialized for {config.run_mode} mode")

# Check if the correct log file would be created
expected_file = "logs/trades_backtest.log"
print(f"✓ Expected trade log file: {expected_file}")

# Test 2: Log a test trade
print("\n" + "="*60)
print("TEST 2: Logging a test trade")
print("="*60)

test_trade = Trade(
    symbol="BTCUSDT",
    side="LONG",
    entry_price=50000.0,
    exit_price=51000.0,
    quantity=0.1,
    pnl=100.0,
    pnl_percent=2.0,
    entry_time=datetime.now().isoformat(),
    exit_time=datetime.now().isoformat(),
    exit_reason="TAKE_PROFIT"
)

logger.log_trade(test_trade)
print(f"✓ Test trade logged")

# Test 3: Verify file exists and contains the trade
print("\n" + "="*60)
print("TEST 3: Verify log file")
print("="*60)

if os.path.exists(expected_file):
    print(f"✓ Log file exists: {expected_file}")
    
    # Read last line
    with open(expected_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        if lines:
            last_line = lines[-1]
            if "TRADE_EXECUTED" in last_line and "BTCUSDT" in last_line:
                print(f"✓ Trade logged correctly to {expected_file}")
                print(f"  Last line: {last_line[:100]}...")
            else:
                print(f"✗ Trade not found in log file")
                print(f"  Last line: {last_line}")
        else:
            print(f"✗ Log file is empty")
else:
    print(f"✗ Log file does not exist: {expected_file}")

# Test 4: Check that trades.log is NOT being used
print("\n" + "="*60)
print("TEST 4: Verify trades.log is NOT being used")
print("="*60)

generic_log = "logs/trades.log"
if os.path.exists(generic_log):
    # Check if our test trade is in the generic log
    with open(generic_log, 'r', encoding='utf-8') as f:
        content = f.read()
        if "BTCUSDT" in content and "TAKE_PROFIT" in content:
            # Check timestamp to see if it's recent
            lines = content.split('\n')
            for line in reversed(lines):
                if "BTCUSDT" in line and "TAKE_PROFIT" in line:
                    print(f"⚠ WARNING: Test trade also found in {generic_log}")
                    print(f"  This suggests logging to wrong file!")
                    print(f"  Line: {line[:100]}...")
                    break
        else:
            print(f"✓ Test trade NOT in {generic_log} (correct)")
else:
    print(f"✓ Generic trades.log does not exist (correct)")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
