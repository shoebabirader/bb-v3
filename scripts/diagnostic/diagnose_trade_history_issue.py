"""Diagnose trade history logging issue."""

import json
from pathlib import Path

print("=" * 60)
print("TRADE HISTORY LOGGING DIAGNOSTIC")
print("=" * 60)

# Check binance_results.json
results_file = Path("binance_results.json")
if results_file.exists():
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    print(f"\n📊 Bot Status from binance_results.json:")
    print(f"   Run Mode: {results.get('run_mode', 'N/A')}")
    print(f"   Total Trades: {results.get('total_trades', 0)}")
    print(f"   Winning Trades: {results.get('winning_trades', 0)}")
    print(f"   Losing Trades: {results.get('losing_trades', 0)}")
    print(f"   Open Positions: {len(results.get('open_positions', []))}")

# Check log files
logs_dir = Path("logs")
trade_log_files = {
    "trades.log": logs_dir / "trades.log",
    "trades_paper.log": logs_dir / "trades_paper.log",
    "trades_live.log": logs_dir / "trades_live.log",
    "trades_backtest.log": logs_dir / "trades_backtest.log"
}

print(f"\n📁 Trade Log Files:")
for name, path in trade_log_files.items():
    if path.exists():
        # Count TRADE_EXECUTED entries
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            trade_count = content.count("TRADE_EXECUTED:")
            init_count = content.count("Trade logger initialized:")
        
        print(f"   ✅ {name}")
        print(f"      - Trades logged: {trade_count}")
        print(f"      - Logger initializations: {init_count}")
        
        # Show last few lines
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                print(f"      - Last entry: {last_line[:80]}...")
    else:
        print(f"   ❌ {name} - NOT FOUND")

print(f"\n" + "=" * 60)
print("DIAGNOSIS:")
print("=" * 60)

# Analyze the issue
trades_log = logs_dir / "trades.log"
trades_paper_log = logs_dir / "trades_paper.log"

if trades_log.exists() and trades_paper_log.exists():
    with open(trades_log, 'r', encoding='utf-8', errors='ignore') as f:
        old_log_trades = f.read().count("TRADE_EXECUTED:")
    
    with open(trades_paper_log, 'r', encoding='utf-8', errors='ignore') as f:
        new_log_trades = f.read().count("TRADE_EXECUTED:")
    
    if old_log_trades > 0 and new_log_trades == 0:
        print("\n⚠️  ISSUE IDENTIFIED:")
        print("   - Trades are being logged to OLD file: trades.log")
        print("   - Trades are NOT being logged to NEW file: trades_paper.log")
        print("   - This means the bot is using the OLD logger instance")
        print("\n💡 SOLUTION:")
        print("   1. RESTART the bot to pick up the new logger configuration")
        print("   2. The bot will then log to: logs/trades_paper.log")
        print("   3. Dashboard will read from the correct file")
        print("\n📝 STEPS:")
        print("   1. Stop the current bot (Ctrl+C or close terminal)")
        print("   2. Start the bot again: python main.py")
        print("   3. New trades will log to trades_paper.log")
        print("   4. Dashboard will show trade history correctly")
    elif new_log_trades > 0:
        print("\n✅ WORKING CORRECTLY:")
        print("   - Trades are being logged to: trades_paper.log")
        print("   - Dashboard should show trade history")
    else:
        print("\n⚠️  NO TRADES LOGGED:")
        print("   - No completed trades found in any log file")
        print("   - This is normal if no positions have closed yet")

print("\n" + "=" * 60)
