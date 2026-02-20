"""Test script to verify dashboard reads correct trade log files."""

import json
import os
from pathlib import Path
from src.streamlit_data_provider import StreamlitDataProvider

def test_trade_log_reading():
    """Test that dashboard reads from correct mode-specific log file."""
    
    print("=" * 60)
    print("Testing Dashboard Trade Log Reading")
    print("=" * 60)
    
    # Read current config
    with open("config/config.json", 'r') as f:
        config = json.load(f)
    
    run_mode = config.get("run_mode", "PAPER")
    print(f"\nCurrent run_mode: {run_mode}")
    
    # Check which log files exist
    logs_dir = Path("logs")
    print(f"\nChecking log files in {logs_dir}:")
    
    log_files = {
        "trades.log": logs_dir / "trades.log",
        "trades_paper.log": logs_dir / "trades_paper.log",
        "trades_live.log": logs_dir / "trades_live.log",
        "trades_backtest.log": logs_dir / "trades_backtest.log"
    }
    
    for name, path in log_files.items():
        exists = "✅ EXISTS" if path.exists() else "❌ NOT FOUND"
        if path.exists():
            size = path.stat().st_size
            print(f"  {name}: {exists} ({size} bytes)")
        else:
            print(f"  {name}: {exists}")
    
    # Initialize data provider
    print(f"\nInitializing StreamlitDataProvider...")
    data_provider = StreamlitDataProvider()
    
    # Get trade history
    print(f"\nReading trade history...")
    trades = data_provider.get_trade_history(limit=10)
    
    print(f"\nFound {len(trades)} trades")
    
    if trades:
        print(f"\nMost recent trade:")
        latest_trade = trades[-1]
        print(f"  Symbol: {latest_trade.get('symbol', 'N/A')}")
        print(f"  Side: {latest_trade.get('side', 'N/A')}")
        print(f"  Entry: ${latest_trade.get('entry_price', 0):.4f}")
        print(f"  Exit: ${latest_trade.get('exit_price', 0):.4f}")
        print(f"  PnL: ${latest_trade.get('pnl', 0):.2f}")
        print(f"  Exit Reason: {latest_trade.get('exit_reason', 'N/A')}")
    
    # Verify it's reading from correct file
    expected_log_file = f"trades_{run_mode.lower()}.log"
    expected_path = logs_dir / expected_log_file
    
    print(f"\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    print(f"Expected log file: {expected_log_file}")
    print(f"File exists: {'✅ YES' if expected_path.exists() else '❌ NO'}")
    
    if expected_path.exists():
        # Count trades in the expected file
        trade_count = 0
        with open(expected_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "TRADE_EXECUTED:" in line:
                    trade_count += 1
        
        print(f"Trades in {expected_log_file}: {trade_count}")
        print(f"Trades returned by data provider: {len(trades)}")
        
        if trade_count == len(trades):
            print(f"\n✅ SUCCESS: Dashboard is reading from correct log file!")
        else:
            print(f"\n⚠️  WARNING: Trade count mismatch")
    else:
        print(f"\n⚠️  WARNING: Expected log file doesn't exist yet")
        print(f"This is normal if no trades have been executed in {run_mode} mode")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_trade_log_reading()
