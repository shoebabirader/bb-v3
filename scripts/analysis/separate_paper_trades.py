"""Separate paper trading trades from backtest trades."""

import json
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("SEPARATE PAPER TRADING TRADES FROM BACKTEST")
print("=" * 80)

logs_dir = Path("logs")
trades_log = logs_dir / "trades.log"
trades_paper_log = logs_dir / "trades_paper.log"

if not trades_log.exists():
    print("❌ No trades.log file found")
    exit(1)

print(f"\n📁 Source: {trades_log}")
print(f"📁 Target: {trades_paper_log}")

# Parse all trades
all_lines = []
paper_trades = []
backtest_trades = []

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
                
                # Check if paper trade or backtest
                # Paper trade: entry_time and log_time are close (within 2 hours)
                entry_time = int(trade_data.get('entry_time', 0))
                if entry_time > 0:
                    entry_dt = datetime.fromtimestamp(entry_time / 1000)
                    time_diff_hours = abs((log_timestamp - entry_dt).total_seconds() / 3600)
                    
                    if time_diff_hours < 2:  # Within 2 hours = paper trade
                        paper_trades.append(line.strip())
                    else:
                        backtest_trades.append(line.strip())
                else:
                    # No entry time, assume backtest
                    backtest_trades.append(line.strip())
                    
            except (json.JSONDecodeError, ValueError, Exception) as e:
                continue

print(f"\n📊 Analysis:")
print(f"   Total trades: {len(paper_trades) + len(backtest_trades)}")
print(f"   Paper trades: {len(paper_trades)}")
print(f"   Backtest trades: {len(backtest_trades)}")

if not paper_trades:
    print("\n⚠️  No paper trading trades found")
    print("   All trades appear to be from backtesting")
    exit(0)

# Clear the paper log and write only paper trades
print(f"\n[1/2] Clearing old data from {trades_paper_log.name}...")
with open(trades_paper_log, 'w', encoding='utf-8') as f:
    # Write initialization message
    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - trading_bot.trades - INFO - Trade logger initialized: trades_paper.log\n")

print(f"   ✅ Cleared")

print(f"\n[2/2] Writing {len(paper_trades)} paper trades...")
with open(trades_paper_log, 'a', encoding='utf-8') as f:
    for trade_line in paper_trades:
        f.write(trade_line + '\n')

print(f"   ✅ Written")

# Show summary of paper trades
print(f"\n📊 Paper Trading Summary:")
winning = 0
losing = 0
total_pnl = 0.0

for trade_line in paper_trades:
    try:
        json_start = trade_line.find("TRADE_EXECUTED:") + len("TRADE_EXECUTED:")
        json_str = trade_line[json_start:].strip()
        trade_data = json.loads(json_str)
        pnl = trade_data.get('pnl', 0)
        if pnl > 0:
            winning += 1
        else:
            losing += 1
        total_pnl += pnl
    except:
        continue

print(f"   Trades: {len(paper_trades)}")
print(f"   Winning: {winning} | Losing: {losing}")
if len(paper_trades) > 0:
    print(f"   Win Rate: {(winning/len(paper_trades)*100):.1f}%")
print(f"   Total PnL: ${total_pnl:.2f}")

# Show last 5 paper trades
print(f"\n📋 Last 5 Paper Trades:")
for i, trade_line in enumerate(paper_trades[-5:], 1):
    try:
        json_start = trade_line.find("TRADE_EXECUTED:") + len("TRADE_EXECUTED:")
        json_str = trade_line[json_start:].strip()
        trade_data = json.loads(json_str)
        
        symbol = trade_data.get('symbol', 'N/A')
        side = trade_data.get('side', 'N/A')
        pnl = trade_data.get('pnl', 0)
        pnl_percent = trade_data.get('pnl_percent', 0)
        
        pnl_indicator = "🟢" if pnl > 0 else "🔴"
        print(f"{i}. {pnl_indicator} {symbol} {side} - ${pnl:.4f} ({pnl_percent:+.2f}%)")
    except:
        continue

print("\n" + "=" * 80)
print("✅ SEPARATION COMPLETE!")
print("=" * 80)
print("\n💡 Result:")
print(f"   - {trades_paper_log.name} now contains ONLY paper trading trades")
print(f"   - Dashboard will show correct paper trading history")
print(f"   - Backtest trades were filtered out")
print("\n" + "=" * 80)
