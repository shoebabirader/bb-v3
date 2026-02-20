"""
Comprehensive diagnostic for dashboard trade history display issue
"""

from src.streamlit_data_provider import StreamlitDataProvider
from pathlib import Path
import json

print("=" * 80)
print("DASHBOARD DISPLAY DIAGNOSTIC")
print("=" * 80)

# 1. Check log files
print("\n1. Checking log files...")
logs_path = Path("logs")
if logs_path.exists():
    print("   ✓ logs directory exists")
    
    # Check current trades.log
    current_log = logs_path / "trades.log"
    if current_log.exists():
        with open(current_log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            trade_lines = [l for l in lines if "TRADE_EXECUTED:" in l]
            print(f"   ✓ trades.log exists with {len(trade_lines)} trades")
    else:
        print("   ✗ trades.log does NOT exist")
    
    # Check rotated logs
    rotated_logs = list(logs_path.glob("trades.log.*"))
    if rotated_logs:
        print(f"   ✓ Found {len(rotated_logs)} rotated log files")
        total_rotated_trades = 0
        for log_file in rotated_logs:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                trade_lines = [l for l in lines if "TRADE_EXECUTED:" in l]
                total_rotated_trades += len(trade_lines)
        print(f"   ✓ Rotated logs contain {total_rotated_trades} trades")
else:
    print("   ✗ logs directory does NOT exist")

# 2. Check data provider
print("\n2. Testing data provider...")
provider = StreamlitDataProvider()
trades = provider.get_trade_history(limit=20)
print(f"   ✓ Data provider returned {len(trades)} trades")

if trades:
    # Calculate stats
    winning = sum(1 for t in trades if t.get('pnl', 0) > 0)
    losing = sum(1 for t in trades if t.get('pnl', 0) < 0)
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    
    print(f"   ✓ Winning: {winning}, Losing: {losing}")
    print(f"   ✓ Total PnL: ${total_pnl:.2f}")
    
    # Check trade structure
    sample_trade = trades[0]
    required_fields = ['symbol', 'side', 'pnl', 'pnl_percent', 'exit_reason']
    missing_fields = [f for f in required_fields if f not in sample_trade]
    
    if missing_fields:
        print(f"   ⚠ Warning: Sample trade missing fields: {missing_fields}")
    else:
        print(f"   ✓ All required fields present in trades")

# 3. Check binance_results.json
print("\n3. Checking binance_results.json...")
try:
    with open("binance_results.json", 'r') as f:
        results = json.load(f)
    print(f"   ✓ binance_results.json exists")
    print(f"   ✓ Bot status: {results.get('bot_status', 'unknown')}")
    print(f"   ✓ Run mode: {results.get('run_mode', 'unknown')}")
    print(f"   ✓ Balance: ${results.get('balance', 0):.2f}")
    print(f"   ✓ Open positions: {len(results.get('open_positions', []))}")
except FileNotFoundError:
    print("   ✗ binance_results.json does NOT exist")
except json.JSONDecodeError:
    print("   ✗ binance_results.json is malformed")

# 4. Check if dashboard is running
print("\n4. Checking if dashboard is running...")
import psutil
dashboard_running = False
try:
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and len(cmdline) > 0:
                cmdline_str = ' '.join(str(c) for c in cmdline)
                if 'streamlit' in cmdline_str.lower() and 'streamlit_app.py' in cmdline_str:
                    dashboard_running = True
                    print(f"   ✓ Dashboard is RUNNING (PID: {proc.pid})")
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
except Exception as e:
    print(f"   ⚠ Could not check process list: {e}")

if not dashboard_running:
    print("   ⚠ Dashboard does NOT appear to be running")

print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)

if trades:
    print("\n✓ GOOD NEWS: Trade data is available and can be read!")
    print(f"  - {len(trades)} trades are ready to display")
    print(f"  - Data provider is working correctly")
    print(f"  - Log files are being parsed successfully")
    
    print("\n📋 SOLUTION:")
    if dashboard_running:
        print("  The dashboard is running. The issue is likely browser cache.")
        print("  Try these steps:")
        print("    1. Go to the Trade History page in the dashboard")
        print("    2. Press Ctrl+F5 (Windows) or Cmd+Shift+R (Mac) to hard refresh")
        print("    3. If that doesn't work, restart the dashboard:")
        print("       - Stop the dashboard (Ctrl+C in the terminal)")
        print("       - Run: streamlit run streamlit_app.py")
    else:
        print("  The dashboard is NOT running. Start it with:")
        print("    streamlit run streamlit_app.py")
        print("  Then navigate to the Trade History page")
else:
    print("\n✗ PROBLEM: No trade data found!")
    print("  This could mean:")
    print("    - The bot hasn't executed any trades yet")
    print("    - The log files are empty or corrupted")
    print("    - The log parsing logic has an issue")

print("\n" + "=" * 80)
