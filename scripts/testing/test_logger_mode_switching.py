"""Test that logger correctly switches between modes."""
import os
from src.config import Config
from src.logger import get_logger, _logger_instance
import src.logger
from src.models import Trade
from datetime import datetime

print("="*60)
print("TEST: Logger Mode Switching")
print("="*60)

# Reset logger instance
src.logger._logger_instance = None

# Test 1: Initialize in PAPER mode
print("\n1. Initialize logger in PAPER mode")
config_paper = Config()
config_paper.run_mode = "PAPER"
logger_paper = get_logger(config=config_paper)
print(f"   ✓ Logger created for PAPER mode")

# Log a paper trade
trade_paper = Trade(
    symbol="ETHUSDT",
    side="LONG",
    entry_price=3000.0,
    exit_price=3100.0,
    quantity=1.0,
    pnl=100.0,
    pnl_percent=3.33,
    entry_time=datetime.now().isoformat(),
    exit_time=datetime.now().isoformat(),
    exit_reason="TAKE_PROFIT"
)
logger_paper.log_trade(trade_paper)
print(f"   ✓ Paper trade logged")

# Test 2: Switch to BACKTEST mode
print("\n2. Switch to BACKTEST mode")
config_backtest = Config()
config_backtest.run_mode = "BACKTEST"
logger_backtest = get_logger(config=config_backtest)
print(f"   ✓ Logger switched to BACKTEST mode")

# Log a backtest trade
trade_backtest = Trade(
    symbol="BTCUSDT",
    side="SHORT",
    entry_price=50000.0,
    exit_price=49000.0,
    quantity=0.1,
    pnl=100.0,
    pnl_percent=2.0,
    entry_time=datetime.now().isoformat(),
    exit_time=datetime.now().isoformat(),
    exit_reason="STOP_LOSS"
)
logger_backtest.log_trade(trade_backtest)
print(f"   ✓ Backtest trade logged")

# Test 3: Verify files
print("\n3. Verify log files")

# Check paper log
paper_log = "logs/trades_paper.log"
if os.path.exists(paper_log):
    with open(paper_log, 'r', encoding='utf-8') as f:
        content = f.read()
        if "ETHUSDT" in content:
            print(f"   ✓ Paper trade found in {paper_log}")
        else:
            print(f"   ✗ Paper trade NOT found in {paper_log}")
        
        if "BTCUSDT" in content and "SHORT" in content:
            print(f"   ✗ ERROR: Backtest trade found in {paper_log} (should not be there!)")
        else:
            print(f"   ✓ Backtest trade NOT in {paper_log} (correct)")
else:
    print(f"   ✗ {paper_log} does not exist")

# Check backtest log
backtest_log = "logs/trades_backtest.log"
if os.path.exists(backtest_log):
    with open(backtest_log, 'r', encoding='utf-8') as f:
        content = f.read()
        if "BTCUSDT" in content and "SHORT" in content:
            print(f"   ✓ Backtest trade found in {backtest_log}")
        else:
            print(f"   ✗ Backtest trade NOT found in {backtest_log}")
        
        if "ETHUSDT" in content:
            print(f"   ✗ ERROR: Paper trade found in {backtest_log} (should not be there!)")
        else:
            print(f"   ✓ Paper trade NOT in {backtest_log} (correct)")
else:
    print(f"   ✗ {backtest_log} does not exist")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
