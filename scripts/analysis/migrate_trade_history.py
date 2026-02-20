"""Migrate recent trade history from old log to new log file."""

import json
from pathlib import Path
from datetime import datetime, timedelta

print("=" * 80)
print("MIGRATE TRADE HISTORY - Copy Recent Trades to New Log")
print("=" * 80)

# Configuration
logs_dir = Path("logs")
old_log = logs_dir / "trades.log"
new_log = logs_dir / "trades_paper.log"
hours_to_migrate = 24  # Migrate last 24 hours of trades

if not old_log.exists():
    print("❌ Old log file not found: logs/trades.log")
    exit(1)

if not new_log.exists():
    print("❌ New log file not found: logs/trades_paper.log")
    exit(1)

print(f"\n📁 Source: {old_log}")
print(f"📁 Target: {new_log}")
print(f"⏰ Migrating trades from last {hours_to_migrate} hours")

# Calculate cutoff time
cutoff_time = datetime.now() - timedelta(hours=hours_to_migrate)
cutoff_timestamp = cutoff_time.isoformat()

# Read all trades from old log
print("\n[1/3] Reading trades from old log...")
all_trades = []
with open(old_log, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if "TRADE_EXECUTED:" in line:
            try:
                # Extract JSON part
                json_start = line.find("TRADE_EXECUTED:") + len("TRADE_EXECUTED:")
                json_str = line[json_start:].strip()
                trade_data = json.loads(json_str)
                
                # Check if trade is within time window
                trade_timestamp = trade_data.get('timestamp', '')
                if trade_timestamp >= cutoff_timestamp:
                    all_trades.append(line.strip())
            except (json.JSONDecodeError, ValueError):
                continue

print(f"   ✅ Found {len(all_trades)} trades in last {hours_to_migrate} hours")

if not all_trades:
    print("\n⚠️  No recent trades to migrate")
    print("   This is normal if no positions closed in the last 24 hours")
    exit(0)

# Append trades to new log
print("\n[2/3] Appending trades to new log...")
with open(new_log, 'a', encoding='utf-8') as f:
    for trade_line in all_trades:
        f.write(trade_line + '\n')

print(f"   ✅ Migrated {len(all_trades)} trades")

# Verify
print("\n[3/3] Verifying migration...")
with open(new_log, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
    trade_count = content.count("TRADE_EXECUTED:")

print(f"   ✅ New log now contains {trade_count} trades")

print("\n" + "=" * 80)
print("✅ MIGRATION COMPLETE!")
print("=" * 80)
print("\n💡 What happens next:")
print("   1. Dashboard will now show recent trade history")
print("   2. Bot will continue logging to old file until restarted")
print("   3. To fix permanently, restart the bot: python main.py")
print("\n📊 Recent trades migrated:")

# Show summary of migrated trades
winning = 0
losing = 0
total_pnl = 0.0

for trade_line in all_trades:
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

print(f"   Winning: {winning} | Losing: {losing}")
print(f"   Total PnL: ${total_pnl:.2f}")
print("\n" + "=" * 80)
