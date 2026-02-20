"""Analyze ALL paper trading trades comprehensively."""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

print("=" * 80)
print("COMPLETE PAPER TRADING PERFORMANCE ANALYSIS")
print("=" * 80)

# Read trades from paper log
logs_dir = Path("logs")
trades_log = logs_dir / "trades_paper.log"

if not trades_log.exists():
    print("❌ No trades_paper.log file found")
    exit(1)

# Parse ALL trades
trades = []
with open(trades_log, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if "TRADE_EXECUTED:" in line:
            try:
                # Extract timestamp from log line
                log_timestamp_str = line.split(' - ')[0]
                log_timestamp = datetime.strptime(log_timestamp_str, '%Y-%m-%d %H:%M:%S')
                
                # Extract JSON part
                json_start = line.find("TRADE_EXECUTED:") + len("TRADE_EXECUTED:")
                json_str = line[json_start:].strip()
                trade_data = json.loads(json_str)
                
                trade_data['log_timestamp'] = log_timestamp
                trades.append(trade_data)
            except (json.JSONDecodeError, ValueError, Exception):
                continue

if not trades:
    print("\n⚠️  No trades found")
    exit(0)

# Get date range
first_trade_time = trades[0]['log_timestamp']
last_trade_time = trades[-1]['log_timestamp']
duration_hours = (last_trade_time - first_trade_time).total_seconds() / 3600

print(f"\n⏰ Trading Period:")
print(f"   First Trade: {first_trade_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   Last Trade:  {last_trade_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   Duration:    {duration_hours:.1f} hours")

print(f"\n📊 Total Trades: {len(trades)}")

# Calculate metrics
winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
breakeven_trades = [t for t in trades if t.get('pnl', 0) == 0]

total_pnl = sum(t.get('pnl', 0) for t in trades)
total_pnl_percent = sum(t.get('pnl_percent', 0) for t in trades)

# Win rate (ACCURACY)
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

# Risk/Reward Ratio
avg_rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')

# Largest win/loss
largest_win = max((t.get('pnl', 0) for t in winning_trades), default=0)
largest_loss = min((t.get('pnl', 0) for t in losing_trades), default=0)
largest_win_percent = max((t.get('pnl_percent', 0) for t in winning_trades), default=0)
largest_loss_percent = min((t.get('pnl_percent', 0) for t in losing_trades), default=0)

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
print("🎯 KEY PERFORMANCE METRICS")
print("=" * 80)

print(f"\n📈 ACCURACY (Win Rate):")
print(f"   ✅ {win_rate:.1f}%")
print(f"   Winning Trades: {len(winning_trades)}")
print(f"   Losing Trades:  {len(losing_trades)}")
if breakeven_trades:
    print(f"   Breakeven:      {len(breakeven_trades)}")

print(f"\n💰 PROFITABILITY:")
print(f"   Total PnL:      ${total_pnl:.2f}")
print(f"   Total PnL %:    {total_pnl_percent:+.2f}%")
print(f"   Profit Factor:  {profit_factor:.2f}")
print(f"   Avg PnL/Trade:  ${total_pnl/len(trades):.2f}")

print(f"\n📊 RISK/REWARD:")
print(f"   Avg Win:        ${avg_win:.2f} ({avg_win_percent:+.2f}%)")
print(f"   Avg Loss:       ${avg_loss:.2f} ({avg_loss_percent:+.2f}%)")
print(f"   R:R Ratio:      {avg_rr_ratio:.2f}:1")

print(f"\n🎯 EXTREMES:")
print(f"   Largest Win:    ${largest_win:.2f} ({largest_win_percent:+.2f}%)")
print(f"   Largest Loss:   ${largest_loss:.2f} ({largest_loss_percent:+.2f}%)")

print("\n" + "=" * 80)
print("📊 PERFORMANCE BY SYMBOL")
print("=" * 80)

for symbol in sorted(trades_by_symbol.keys(), key=lambda x: len(trades_by_symbol[x]), reverse=True):
    symbol_trades = trades_by_symbol[symbol]
    symbol_wins = [t for t in symbol_trades if t.get('pnl', 0) > 0]
    symbol_losses = [t for t in symbol_trades if t.get('pnl', 0) < 0]
    symbol_pnl = sum(t.get('pnl', 0) for t in symbol_trades)
    symbol_win_rate = (len(symbol_wins) / len(symbol_trades) * 100) if symbol_trades else 0
    
    print(f"\n{symbol}:")
    print(f"   Trades: {len(symbol_trades)} ({len(symbol_trades)/len(trades)*100:.1f}%)")
    print(f"   Win Rate: {symbol_win_rate:.1f}% | W/L: {len(symbol_wins)}/{len(symbol_losses)}")
    print(f"   PnL: ${symbol_pnl:.2f}")

print("\n" + "=" * 80)
print("📊 PERFORMANCE BY DIRECTION")
print("=" * 80)

for side in sorted(trades_by_side.keys()):
    side_trades = trades_by_side[side]
    side_wins = [t for t in side_trades if t.get('pnl', 0) > 0]
    side_losses = [t for t in side_trades if t.get('pnl', 0) < 0]
    side_pnl = sum(t.get('pnl', 0) for t in side_trades)
    side_win_rate = (len(side_wins) / len(side_trades) * 100) if side_trades else 0
    
    print(f"\n{side}:")
    print(f"   Trades: {len(side_trades)} ({len(side_trades)/len(trades)*100:.1f}%)")
    print(f"   Win Rate: {side_win_rate:.1f}% | W/L: {len(side_wins)}/{len(side_losses)}")
    print(f"   PnL: ${side_pnl:.2f}")

print("\n" + "=" * 80)
print("📊 EXIT REASONS ANALYSIS")
print("=" * 80)

for exit_reason in sorted(trades_by_exit.keys(), key=lambda x: len(trades_by_exit[x]), reverse=True):
    exit_trades = trades_by_exit[exit_reason]
    exit_wins = [t for t in exit_trades if t.get('pnl', 0) > 0]
    exit_pnl = sum(t.get('pnl', 0) for t in exit_trades)
    exit_win_rate = (len(exit_wins) / len(exit_trades) * 100) if exit_trades else 0
    
    print(f"\n{exit_reason}:")
    print(f"   Count: {len(exit_trades)} ({len(exit_trades)/len(trades)*100:.1f}%)")
    print(f"   Win Rate: {exit_win_rate:.1f}%")
    print(f"   PnL: ${exit_pnl:.2f}")

print("\n" + "=" * 80)
print("🎯 FINAL ASSESSMENT")
print("=" * 80)

print(f"\n📊 Overall Statistics:")
print(f"   ✅ Win Rate (Accuracy):  {win_rate:.1f}%")
print(f"   ✅ Profit Factor:        {profit_factor:.2f}")
print(f"   ✅ Risk/Reward Ratio:    {avg_rr_ratio:.2f}:1")
print(f"   ✅ Total PnL:            ${total_pnl:.2f}")
print(f"   ✅ Total Trades:         {len(trades)}")
print(f"   ✅ Avg PnL per Trade:    ${total_pnl/len(trades):.2f}")

print(f"\n💡 Performance Rating:")
if win_rate >= 50 and profit_factor >= 1.5:
    print(f"   🎉 EXCELLENT PERFORMANCE!")
    print(f"   Your strategy is working very well.")
    print(f"   - Win rate above 50%")
    print(f"   - Strong profit factor (>1.5)")
    print(f"   - Positive total PnL")
elif win_rate >= 45 and profit_factor >= 1.2:
    print(f"   👍 GOOD PERFORMANCE")
    print(f"   Solid results with room for improvement.")
    print(f"   - Decent win rate (45-50%)")
    print(f"   - Good profit factor (1.2-1.5)")
elif win_rate >= 40 and profit_factor >= 1.0:
    print(f"   ⚠️  ACCEPTABLE PERFORMANCE")
    print(f"   Breaking even or slightly profitable.")
    print(f"   - Win rate needs improvement (<45%)")
    print(f"   - Profit factor barely positive")
else:
    print(f"   ⚠️  NEEDS IMPROVEMENT")
    print(f"   Strategy requires optimization.")
    print(f"   - Low win rate (<40%)")
    print(f"   - Poor profit factor (<1.0)")

print("\n" + "=" * 80)
