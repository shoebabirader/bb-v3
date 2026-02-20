"""Analyze paper trading performance for last 8 hours."""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

print("=" * 80)
print("PAPER TRADING PERFORMANCE - LAST 8 HOURS")
print("=" * 80)

# Get current time and 8 hours ago
now = datetime.now()
cutoff_time = now - timedelta(hours=8)

print(f"\n⏰ Analysis Period:")
print(f"   From: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   To:   {now.strftime('%Y-%m-%d %H:%M:%S')}")

# Read trades from paper log
logs_dir = Path("logs")
trades_log = logs_dir / "trades_paper.log"

if not trades_log.exists():
    print("❌ No trades_paper.log file found")
    exit(1)

# Parse trades
trades = []
with open(trades_log, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if "TRADE_EXECUTED:" in line:
            try:
                # Extract timestamp from log line
                log_timestamp_str = line.split(' - ')[0]
                log_timestamp = datetime.strptime(log_timestamp_str, '%Y-%m-%d %H:%M:%S')
                
                # Only include trades from last 8 hours
                if log_timestamp < cutoff_time:
                    continue
                
                # Extract JSON part
                json_start = line.find("TRADE_EXECUTED:") + len("TRADE_EXECUTED:")
                json_str = line[json_start:].strip()
                trade_data = json.loads(json_str)
                
                trade_data['log_timestamp'] = log_timestamp
                trades.append(trade_data)
            except (json.JSONDecodeError, ValueError, Exception):
                continue

if not trades:
    print("\n⚠️  No trades found in last 8 hours")
    exit(0)

print(f"\n📊 Total Trades: {len(trades)}")

# Calculate metrics
winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]
breakeven_trades = [t for t in trades if t.get('pnl', 0) == 0]

total_pnl = sum(t.get('pnl', 0) for t in trades)
total_pnl_percent = sum(t.get('pnl_percent', 0) for t in trades)

# Win rate
win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0

# Average metrics
avg_win = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
avg_win_percent = sum(t.get('pnl_percent', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
avg_loss_percent = sum(t.get('pnl_percent', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0

# Profit factor
total_wins = sum(t.get('pnl', 0) for t in winning_trades)
total_losses = abs(sum(t.get('pnl', 0) for t in losing_trades))
profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf')

# Largest win/loss
largest_win = max((t.get('pnl', 0) for t in winning_trades), default=0)
largest_loss = min((t.get('pnl', 0) for t in losing_trades), default=0)

# By symbol
trades_by_symbol = defaultdict(list)
for trade in trades:
    symbol = trade.get('symbol', 'UNKNOWN')
    trades_by_symbol[symbol].append(trade)

# By side
trades_by_side = defaultdict(list)
for trade in trades:
    side = trade.get('side', 'UNKNOWN')
    trades_by_side[side].append(trade)

# By exit reason
trades_by_exit = defaultdict(list)
for trade in trades:
    exit_reason = trade.get('exit_reason', 'UNKNOWN')
    trades_by_exit[exit_reason].append(trade)

print("\n" + "=" * 80)
print("OVERALL PERFORMANCE")
print("=" * 80)

print(f"\n📈 Win/Loss Breakdown:")
print(f"   Winning Trades: {len(winning_trades)} ({len(winning_trades)/len(trades)*100:.1f}%)")
print(f"   Losing Trades:  {len(losing_trades)} ({len(losing_trades)/len(trades)*100:.1f}%)")
if breakeven_trades:
    print(f"   Breakeven:      {len(breakeven_trades)} ({len(breakeven_trades)/len(trades)*100:.1f}%)")

print(f"\n💰 Profit & Loss:")
print(f"   Total PnL:      ${total_pnl:.2f}")
print(f"   Total PnL %:    {total_pnl_percent:+.2f}%")
print(f"   Win Rate:       {win_rate:.1f}%")
print(f"   Profit Factor:  {profit_factor:.2f}")

print(f"\n📊 Average Trade:")
print(f"   Avg Win:        ${avg_win:.2f} ({avg_win_percent:+.2f}%)")
print(f"   Avg Loss:       ${avg_loss:.2f} ({avg_loss_percent:+.2f}%)")
print(f"   Avg Trade:      ${total_pnl/len(trades):.2f}")

print(f"\n🎯 Best/Worst:")
print(f"   Largest Win:    ${largest_win:.2f}")
print(f"   Largest Loss:   ${largest_loss:.2f}")

print("\n" + "=" * 80)
print("PERFORMANCE BY SYMBOL")
print("=" * 80)

for symbol in sorted(trades_by_symbol.keys()):
    symbol_trades = trades_by_symbol[symbol]
    symbol_wins = [t for t in symbol_trades if t.get('pnl', 0) > 0]
    symbol_losses = [t for t in symbol_trades if t.get('pnl', 0) <= 0]
    symbol_pnl = sum(t.get('pnl', 0) for t in symbol_trades)
    symbol_win_rate = (len(symbol_wins) / len(symbol_trades) * 100) if symbol_trades else 0
    
    print(f"\n{symbol}:")
    print(f"   Trades: {len(symbol_trades)} | Win Rate: {symbol_win_rate:.1f}%")
    print(f"   W/L: {len(symbol_wins)}/{len(symbol_losses)} | PnL: ${symbol_pnl:.2f}")

print("\n" + "=" * 80)
print("PERFORMANCE BY DIRECTION")
print("=" * 80)

for side in sorted(trades_by_side.keys()):
    side_trades = trades_by_side[side]
    side_wins = [t for t in side_trades if t.get('pnl', 0) > 0]
    side_losses = [t for t in side_trades if t.get('pnl', 0) <= 0]
    side_pnl = sum(t.get('pnl', 0) for t in side_trades)
    side_win_rate = (len(side_wins) / len(side_trades) * 100) if side_trades else 0
    
    print(f"\n{side}:")
    print(f"   Trades: {len(side_trades)} | Win Rate: {side_win_rate:.1f}%")
    print(f"   W/L: {len(side_wins)}/{len(side_losses)} | PnL: ${side_pnl:.2f}")

print("\n" + "=" * 80)
print("EXIT REASONS")
print("=" * 80)

for exit_reason in sorted(trades_by_exit.keys(), key=lambda x: len(trades_by_exit[x]), reverse=True):
    exit_trades = trades_by_exit[exit_reason]
    exit_wins = [t for t in exit_trades if t.get('pnl', 0) > 0]
    exit_pnl = sum(t.get('pnl', 0) for t in exit_trades)
    exit_win_rate = (len(exit_wins) / len(exit_trades) * 100) if exit_trades else 0
    
    print(f"\n{exit_reason}:")
    print(f"   Count: {len(exit_trades)} ({len(exit_trades)/len(trades)*100:.1f}%)")
    print(f"   Win Rate: {exit_win_rate:.1f}% | PnL: ${exit_pnl:.2f}")

print("\n" + "=" * 80)
print("RECENT TRADES (Last 10)")
print("=" * 80)

for i, trade in enumerate(trades[-10:], 1):
    symbol = trade.get('symbol', 'N/A')
    side = trade.get('side', 'N/A')
    pnl = trade.get('pnl', 0)
    pnl_percent = trade.get('pnl_percent', 0)
    exit_reason = trade.get('exit_reason', 'N/A')
    log_time = trade['log_timestamp']
    
    pnl_indicator = "🟢" if pnl > 0 else "🔴"
    print(f"\n{i}. {pnl_indicator} {symbol} {side}")
    print(f"   PnL: ${pnl:.4f} ({pnl_percent:+.2f}%)")
    print(f"   Exit: {exit_reason}")
    print(f"   Time: {log_time.strftime('%H:%M:%S')}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"\n✅ Win Rate: {win_rate:.1f}%")
print(f"✅ Profit Factor: {profit_factor:.2f}")
print(f"✅ Total PnL: ${total_pnl:.2f}")
print(f"✅ Total Trades: {len(trades)}")

if win_rate >= 50 and profit_factor >= 1.5:
    print(f"\n🎉 EXCELLENT PERFORMANCE!")
elif win_rate >= 45 and profit_factor >= 1.2:
    print(f"\n👍 GOOD PERFORMANCE")
elif win_rate >= 40 and profit_factor >= 1.0:
    print(f"\n⚠️  ACCEPTABLE PERFORMANCE")
else:
    print(f"\n⚠️  NEEDS IMPROVEMENT")

print("\n" + "=" * 80)
