"""Comprehensive test for all trading modes logging to correct files."""
import os
import time
from src.config import Config
from src.logger import reset_logger, get_logger
from src.models import Trade
from datetime import datetime

print("="*70)
print("COMPREHENSIVE TEST: All Trading Modes Logging")
print("="*70)

def log_test_trade(logger, mode, symbol, price_entry, price_exit):
    """Helper to log a test trade."""
    trade = Trade(
        symbol=symbol,
        side="LONG",
        entry_price=price_entry,
        exit_price=price_exit,
        quantity=0.1,
        pnl=price_exit - price_entry,
        pnl_percent=((price_exit - price_entry) / price_entry) * 100,
        entry_time=datetime.now().isoformat(),
        exit_time=datetime.now().isoformat(),
        exit_reason="TAKE_PROFIT"
    )
    logger.log_trade(trade)
    return trade

def verify_trade_in_file(filepath, symbol, price_entry, price_exit):
    """Check if a trade is in the specified file."""
    if not os.path.exists(filepath):
        return False, "File does not exist"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        if symbol in content and str(price_entry) in content and str(price_exit) in content:
            return True, "Trade found"
        else:
            return False, "Trade not found"

# Test data for each mode
test_data = {
    "BACKTEST": {
        "symbol": "BTCUSDT",
        "entry": 70000.0,
        "exit": 71000.0,
        "log_file": "logs/trades_backtest.log"
    },
    "PAPER": {
        "symbol": "ETHUSDT",
        "entry": 3000.0,
        "exit": 3100.0,
        "log_file": "logs/trades_paper.log"
    },
    "LIVE": {
        "symbol": "BNBUSDT",
        "entry": 500.0,
        "exit": 510.0,
        "log_file": "logs/trades_live.log"
    }
}

results = {}

# Test each mode
for mode in ["BACKTEST", "PAPER", "LIVE"]:
    print(f"\n{'='*70}")
    print(f"Testing {mode} Mode")
    print(f"{'='*70}")
    
    # Reset logger for clean state
    reset_logger()
    
    # Create config for this mode
    config = Config()
    config.run_mode = mode
    config.symbol = test_data[mode]["symbol"]
    
    print(f"\n1. Initialize logger for {mode} mode")
    logger = get_logger(config=config)
    print(f"   ✓ Logger initialized")
    print(f"   Expected log file: {test_data[mode]['log_file']}")
    
    # Log test trade
    print(f"\n2. Log test trade")
    trade = log_test_trade(
        logger, 
        mode, 
        test_data[mode]["symbol"],
        test_data[mode]["entry"],
        test_data[mode]["exit"]
    )
    print(f"   ✓ Trade logged: {trade.symbol} {trade.side} @ {trade.entry_price}")
    
    # Wait for file write
    time.sleep(0.5)
    
    # Verify correct file
    print(f"\n3. Verify trade in correct log file")
    expected_file = test_data[mode]["log_file"]
    found, msg = verify_trade_in_file(
        expected_file,
        test_data[mode]["symbol"],
        test_data[mode]["entry"],
        test_data[mode]["exit"]
    )
    
    if found:
        print(f"   ✓ Trade found in {expected_file}")
        results[mode] = {"correct_file": True, "wrong_files": []}
    else:
        print(f"   ✗ Trade NOT found in {expected_file}: {msg}")
        results[mode] = {"correct_file": False, "wrong_files": []}
    
    # Check that trade is NOT in other mode's files
    print(f"\n4. Verify trade NOT in other log files")
    for other_mode, other_data in test_data.items():
        if other_mode != mode:
            other_file = other_data["log_file"]
            found, msg = verify_trade_in_file(
                other_file,
                test_data[mode]["symbol"],
                test_data[mode]["entry"],
                test_data[mode]["exit"]
            )
            
            if found:
                print(f"   ✗ ERROR: Trade found in {other_file} (should not be there!)")
                results[mode]["wrong_files"].append(other_file)
            else:
                print(f"   ✓ Trade NOT in {other_file} (correct)")

# Summary
print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")

all_passed = True
for mode, result in results.items():
    status = "✓ PASS" if result["correct_file"] and not result["wrong_files"] else "✗ FAIL"
    print(f"\n{mode} Mode: {status}")
    
    if not result["correct_file"]:
        print(f"  - Trade NOT in correct file: {test_data[mode]['log_file']}")
        all_passed = False
    
    if result["wrong_files"]:
        print(f"  - Trade found in wrong files: {', '.join(result['wrong_files'])}")
        all_passed = False

print(f"\n{'='*70}")
if all_passed:
    print("✓ ALL TESTS PASSED - All modes log to correct files!")
else:
    print("✗ SOME TESTS FAILED - Check results above")
print(f"{'='*70}")
