"""Quick test that backtest logs to trades_backtest.log."""
import os
import time
from src.config import Config
from src.logger import reset_logger, get_logger
from src.models import Trade
from datetime import datetime

print("="*60)
print("QUICK TEST: Backtest Logging")
print("="*60)

# Reset logger
reset_logger()

# Create BACKTEST config
config = Config()
config.run_mode = "BACKTEST"
config.symbol = "BTCUSDT"

print(f"\n1. Initialize logger for BACKTEST mode")
logger = get_logger(config=config)
print(f"   ✓ Logger initialized")

# Log a test trade
print(f"\n2. Log a test trade")
test_trade = Trade(
    symbol="BTCUSDT",
    side="LONG",
    entry_price=70000.0,
    exit_price=71000.0,
    quantity=0.1,
    pnl=100.0,
    pnl_percent=1.43,
    entry_time=datetime.now().isoformat(),
    exit_time=datetime.now().isoformat(),
    exit_reason="TAKE_PROFIT"
)

logger.log_trade(test_trade)
print(f"   ✓ Trade logged")

# Wait a moment for file write
time.sleep(0.5)

# Check files
print(f"\n3. Verify log files")

backtest_log = "logs/trades_backtest.log"
if os.path.exists(backtest_log):
    with open(backtest_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # Find our test trade
        found = False
        for line in reversed(lines):
            if "70000.0" in line and "71000.0" in line:
                found = True
                print(f"   ✓ Test trade found in {backtest_log}")
                break
        
        if not found:
            print(f"   ✗ Test trade NOT found in {backtest_log}")
else:
    print(f"   ✗ {backtest_log} does not exist")

# Check trades.log
generic_log = "logs/trades.log"
if os.path.exists(generic_log):
    with open(generic_log, 'r', encoding='utf-8') as f:
        content = f.read()
        if "70000.0" in content and "71000.0" in content:
            print(f"   ✗ ERROR: Test trade also in {generic_log}")
        else:
            print(f"   ✓ Test trade NOT in {generic_log} (correct)")
else:
    print(f"   ✓ {generic_log} does not exist (correct)")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
