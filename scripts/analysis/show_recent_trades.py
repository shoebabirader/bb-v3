"""Show recent completed trades from logs."""

import json
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("RECENT COMPLETED TRADES (from logs/trades.log)")
print("=" * 80)

logs_dir = Path("logs")
trades_log = logs_dir / "trades.log"

if not trades_log.exists():
    print("❌ No trades.log file found")
    exit(1)

# Parse all trades
trades = []
with open(trades_log, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if "TRADE_EXECUTED:" in line:
            try:
                # Extract JSON part
                json_start = line.find("TRADE_EXECUTED:") + len("TRADE_EXECUTED:")
                json_str = line[json_start:].strip()
                trade_data = json.loads(json_str)
                trades.append(trade_data)
            except (json.JSONDecodeError, ValueError):
                continue

if not trades:
    print("❌ No completed trades found")
    exit(0)

# Show last 10 trades
print(f"\n📊 Total trades in log: {len(trades)}")
print(f"\n🔄 Last 10 completed trades:\n")

for i, trade in enumerate(trades[-10:], 1):
    symbol = trade.get('symbol', 'N/A')
    side = trade.get('side', 'N/A')
    entry_price = trade.get('entry_price', 0)
    exit_price = trade.get('exit_price', 0)
    pnl = trade.get('pnl', 0)
    pnl_percent = trade.get('pnl_percent', 0)
    exit_reason = trade.get('exit_reason', 'N/A')
    timestamp = trade.get('timestamp', 'N/A')
    
    # Format PnL with color indicator
    pnl_indicator = "🟢" if pnl > 0 else "🔴"
    
    print(f"{i}. {pnl_indicator} {symbol} {side}")
    print(f"   Entry: ${entry_price:.4f} → Exit: ${exit_price:.4f}")
    print(f"   PnL: ${pnl:.4f} ({pnl_percent:+.2f}%)")
    print(f"   Exit Reason: {exit_reason}")
    print(f"   Time: {timestamp[:19]}")
    print()

# Summary
winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
losing_trades = sum(1 for t in trades if t.get('pnl', 0) <= 0)
total_pnl = sum(t.get('pnl', 0) for t in trades)

print("=" * 80)
print("SUMMARY:")
print(f"   Total Trades: {len(trades)}")
print(f"   Winning: {winning_trades} | Losing: {losing_trades}")
print(f"   Win Rate: {(winning_trades/len(trades)*100):.1f}%")
print(f"   Total PnL: ${total_pnl:.2f}")
print("=" * 80)

print("\n⚠️  NOTE: These trades are in the OLD log file (trades.log)")
print("   After restarting the bot, new trades will go to: logs/trades_paper.log")
print("   The dashboard will then show trade history correctly.")
