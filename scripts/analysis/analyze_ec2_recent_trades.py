"""Analyze recent trades from EC2 bot."""

import subprocess
import json
import re
from datetime import datetime

def ssh_cmd(cmd, timeout=8):
    """Run SSH command."""
    try:
        result = subprocess.run(
            f'ssh -i bb.pem -o ConnectTimeout=5 ubuntu@13.233.2.23 "{cmd}"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except:
        return None

print("\n" + "="*80)
print("EC2 RECENT TRADES ANALYSIS")
print("="*80)

# Get all TRADE_EXECUTED entries
print("\nFetching trade data from EC2...")
trades_raw = ssh_cmd("grep 'TRADE_EXECUTED' ~/trading-bot/logs/trades.log 2>/dev/null | tail -10", timeout=10)

if not trades_raw:
    print("❌ Could not fetch trade data")
    exit(1)

print(f"\nFound {len(trades_raw.split(chr(10)))} recent trades\n")
print("="*80)

trades = []
for line in trades_raw.split('\n'):
    if 'TRADE_EXECUTED' in line:
        # Extract JSON part
        json_match = re.search(r'\{.*\}', line)
        if json_match:
            try:
                trade_data = json.loads(json_match.group())
                trades.append(trade_data)
            except:
                pass

# Analyze each trade
total_pnl = 0
wins = 0
losses = 0

for i, trade in enumerate(trades, 1):
    symbol = trade.get('symbol', 'UNKNOWN')
    side = trade.get('side', 'UNKNOWN')
    entry_price = trade.get('entry_price', 0)
    exit_price = trade.get('exit_price', 0)
    pnl = trade.get('pnl', 0)
    pnl_pct = trade.get('pnl_percent', 0)
    exit_reason = trade.get('exit_reason', 'UNKNOWN')
    
    # Calculate duration
    entry_time = trade.get('entry_time', 0)
    exit_time = trade.get('exit_time', 0)
    duration_ms = exit_time - entry_time
    duration_sec = duration_ms / 1000
    duration_min = duration_sec / 60
    
    total_pnl += pnl
    if pnl > 0:
        wins += 1
        result = "✅ WIN"
    else:
        losses += 1
        result = "❌ LOSS"
    
    print(f"\nTrade #{i}: {result}")
    print(f"  Symbol: {symbol}")
    print(f"  Side: {side}")
    print(f"  Entry: ${entry_price:.4f}")
    print(f"  Exit: ${exit_price:.4f}")
    print(f"  PnL: ${pnl:.2f} ({pnl_pct:.2f}%)")
    print(f"  Duration: {duration_min:.1f} minutes ({duration_sec:.0f} seconds)")
    print(f"  Exit Reason: {exit_reason}")
    
    # Analyze what went wrong
    if pnl < 0:
        if duration_sec < 60:
            print(f"  ⚠️  CRITICAL: Trade lasted only {duration_sec:.0f} seconds!")
            print(f"  ⚠️  This suggests immediate adverse price movement")
        elif exit_reason == "TRAILING_STOP":
            print(f"  ⚠️  Trailing stop hit - price moved against us")
        elif exit_reason == "STOP_LOSS":
            print(f"  ⚠️  Stop loss hit - entry was wrong")
        elif exit_reason == "PANIC":
            print(f"  ⚠️  Manual panic close - user intervention")
        elif exit_reason == "SIGNAL_EXIT":
            print(f"  ⚠️  Signal exit - conditions changed quickly")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nTotal Trades: {len(trades)}")
print(f"Wins: {wins} ({wins/len(trades)*100:.1f}%)")
print(f"Losses: {losses} ({losses/len(trades)*100:.1f}%)")
print(f"Total PnL: ${total_pnl:.2f}")
print(f"Average PnL per trade: ${total_pnl/len(trades):.2f}")

print("\n" + "="*80)
print("DIAGNOSIS")
print("="*80)

if losses > wins:
    print("\n❌ PROBLEM: More losses than wins")
    print("\nPossible causes:")
    print("  1. Entry signals are weak or premature")
    print("  2. Market conditions don't match strategy requirements")
    print("  3. Timeframe alignment too strict (currently 4, should be 3)")
    print("  4. ADX/RVOL thresholds not filtering enough")

# Check for quick exits
quick_exits = sum(1 for t in trades if (t.get('exit_time', 0) - t.get('entry_time', 0)) < 60000)
if quick_exits > 0:
    print(f"\n⚠️  {quick_exits} trades exited in less than 1 minute!")
    print("  This is a RED FLAG - entries are happening at wrong time")

print("\n" + "="*80)
print("RECOMMENDED ACTIONS")
print("="*80)
print("\n1. URGENT: Fix EC2 config")
print("   - Change min_timeframe_alignment from 4 to 3")
print("   - This will allow more trades with V3.1 settings")
print("\n2. Stop bot until backtest shows profitability")
print("   - Current strategy is still losing money")
print("   - Need to verify V3.1 works in backtest first")
print("\n3. Consider even stricter filters")
print("   - Maybe ADX 30+ instead of 25")
print("   - Maybe RVOL 1.5+ instead of 1.2")
print("   - Wait for stronger confirmation")

print("\n" + "="*80)
