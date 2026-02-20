"""
Test script to diagnose trade history display issue
"""

from src.streamlit_data_provider import StreamlitDataProvider
import json

print("=" * 80)
print("TRADE HISTORY DIAGNOSTIC TEST")
print("=" * 80)

# Initialize data provider
provider = StreamlitDataProvider()

# Test 1: Check if trades.log exists
print("\n1. Checking if trades.log exists...")
import os
if os.path.exists("logs/trades.log"):
    print("✓ logs/trades.log exists")
    
    # Count lines
    with open("logs/trades.log", 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        print(f"  - Total lines: {len(lines)}")
        
        # Count TRADE_EXECUTED lines
        trade_lines = [l for l in lines if "TRADE_EXECUTED:" in l]
        print(f"  - Lines with TRADE_EXECUTED: {len(trade_lines)}")
else:
    print("✗ logs/trades.log does NOT exist")

# Test 2: Call get_trade_history
print("\n2. Calling get_trade_history()...")
trades = provider.get_trade_history(limit=20)
print(f"✓ Returned {len(trades)} trades")

# Test 3: Display trade details
if trades:
    print("\n3. Trade details:")
    for i, trade in enumerate(trades, 1):
        print(f"\n  Trade {i}:")
        print(f"    Symbol: {trade.get('symbol', 'N/A')}")
        print(f"    Side: {trade.get('side', 'N/A')}")
        print(f"    PnL: ${trade.get('pnl', 0):.2f}")
        print(f"    PnL %: {trade.get('pnl_percent', 0):.2f}%")
        print(f"    Exit Reason: {trade.get('exit_reason', 'N/A')}")
        print(f"    Timestamp: {trade.get('timestamp', 'N/A')}")
else:
    print("\n3. No trades found!")
    print("\n   Debugging _parse_trade_logs()...")
    
    # Manual test of parsing
    import pathlib
    logs_path = pathlib.Path("logs")
    
    if logs_path.exists():
        print(f"   ✓ logs directory exists")
        
        # Check for trade log files
        current_log = logs_path / "trades.log"
        if current_log.exists():
            print(f"   ✓ trades.log exists")
            
            # Try to parse manually
            with open(current_log, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if "TRADE_EXECUTED:" in line:
                        print(f"\n   Found TRADE_EXECUTED on line {line_num}")
                        print(f"   Line content: {line[:100]}...")
                        
                        # Try to extract JSON
                        try:
                            json_start = line.find("TRADE_EXECUTED:") + len("TRADE_EXECUTED:")
                            json_str = line[json_start:].strip()
                            trade_data = json.loads(json_str)
                            print(f"   ✓ Successfully parsed JSON")
                            print(f"   Symbol: {trade_data.get('symbol')}")
                        except Exception as e:
                            print(f"   ✗ Failed to parse JSON: {e}")
        else:
            print(f"   ✗ trades.log does NOT exist")
    else:
        print(f"   ✗ logs directory does NOT exist")

print("\n" + "=" * 80)
print("DIAGNOSTIC TEST COMPLETE")
print("=" * 80)
