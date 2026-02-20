"""Analyze if trades in log are from paper trading or backtesting."""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

print("=" * 80)
print("TRADE LOG SOURCE ANALYSIS")
print("=" * 80)

# Read config to see current mode
config_file = Path("config/config.json")
with open(config_file, 'r') as f:
    config = json.load(f)

current_mode = config.get('run_mode', 'UNKNOWN')
print(f"\n📋 Current Config:")
print(f"   Run Mode: {current_mode}")

# Analyze trades.log
logs_dir = Path("logs")
trades_log = logs_dir / "trades.log"

if not trades_log.exists():
    print("❌ No trades.log file found")
    exit(1)

print(f"\n📊 Analyzing: {trades_log}")

# Parse all trades
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
    print("❌ No trades found")
    exit(0)

print(f"\n✅ Found {len(trades)} total trades")

# Analyze trade patterns
print("\n" + "=" * 80)
print("TRADE PATTERN ANALYSIS")
print("=" * 80)

# Group trades by date
trades_by_date = defaultdict(list)
for trade in trades:
    date = trade['log_timestamp'].date()
    trades_by_date[date].append(trade)

print(f"\n📅 Trades by Date:")
for date in sorted(trades_by_date.keys()):
    count = len(trades_by_date[date])
    print(f"   {date}: {count} trades")

# Check for backtest patterns
print(f"\n🔍 Backtest Pattern Detection:")

# Pattern 1: Many trades in very short time (typical of backtest)
rapid_trades = 0
for i in range(1, len(trades)):
    time_diff = (trades[i]['log_timestamp'] - trades[i-1]['log_timestamp']).total_seconds()
    if time_diff < 1:  # Less than 1 second between trades
        rapid_trades += 1

print(f"   Rapid trades (<1s apart): {rapid_trades}")
if rapid_trades > 50:
    print(f"   ⚠️  HIGH - Likely contains backtest data")
elif rapid_trades > 10:
    print(f"   ⚠️  MEDIUM - May contain backtest data")
else:
    print(f"   ✅ LOW - Likely paper trading only")

# Pattern 2: Check entry_time vs log_time difference
# Backtest: entry_time is historical, log_time is recent
# Paper: entry_time and log_time are close
time_differences = []
for trade in trades[-20:]:  # Check last 20 trades
    try:
        entry_time = int(trade.get('entry_time', 0))
        if entry_time > 0:
            entry_dt = datetime.fromtimestamp(entry_time / 1000)
            log_dt = trade['log_timestamp']
            diff_hours = abs((log_dt - entry_dt).total_seconds() / 3600)
            time_differences.append(diff_hours)
    except:
        continue

if time_differences:
    avg_diff = sum(time_differences) / len(time_differences)
    max_diff = max(time_differences)
    
    print(f"\n⏰ Entry Time vs Log Time (last 20 trades):")
    print(f"   Average difference: {avg_diff:.1f} hours")
    print(f"   Maximum difference: {max_diff:.1f} hours")
    
    if avg_diff > 24:
        print(f"   ⚠️  BACKTEST - Entry times are historical")
    elif avg_diff > 1:
        print(f"   ⚠️  MIXED - May contain both backtest and paper trades")
    else:
        print(f"   ✅ PAPER TRADING - Entry times are recent")

# Show recent trades
print(f"\n📋 Last 5 Trades:")
for i, trade in enumerate(trades[-5:], 1):
    symbol = trade.get('symbol', 'N/A')
    side = trade.get('side', 'N/A')
    pnl = trade.get('pnl', 0)
    log_time = trade['log_timestamp']
    
    try:
        entry_time = int(trade.get('entry_time', 0))
        entry_dt = datetime.fromtimestamp(entry_time / 1000)
        time_diff = (log_time - entry_dt).total_seconds() / 3600
        
        pnl_indicator = "🟢" if pnl > 0 else "🔴"
        print(f"\n{i}. {pnl_indicator} {symbol} {side}")
        print(f"   Entry: {entry_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Logged: {log_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Time diff: {time_diff:.1f} hours")
        print(f"   PnL: ${pnl:.4f}")
    except:
        print(f"\n{i}. {symbol} {side} - PnL: ${pnl:.4f}")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)

# Final determination
if rapid_trades > 50 or (time_differences and sum(time_differences) / len(time_differences) > 24):
    print("\n⚠️  MIXED LOGS DETECTED")
    print("   The trades.log file contains BOTH:")
    print("   - Historical backtest trades")
    print("   - Recent paper trading trades")
    print("\n💡 RECOMMENDATION:")
    print("   1. Clear old backtest data from logs")
    print("   2. Keep only recent paper trading data")
    print("   3. Or separate them into different files")
else:
    print("\n✅ PAPER TRADING LOGS")
    print("   The trades appear to be from paper trading only")

print("\n" + "=" * 80)
