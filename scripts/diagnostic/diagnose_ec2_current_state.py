"""Quick diagnosis of EC2 bot current state."""

import subprocess
import json
from datetime import datetime

def ssh_cmd(cmd, timeout=5):
    """Run SSH command with short timeout."""
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
print("EC2 BOT QUICK DIAGNOSIS")
print("="*80)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}\n")

# 1. Check if running
print("1. Bot Status:")
status = ssh_cmd("pgrep -f 'python.*main.py' && echo 'RUNNING' || echo 'STOPPED'")
print(f"   {status if status else 'Connection failed'}")

# 2. Check config - critical settings
print("\n2. Current Config (V3.1 settings):")
config_check = ssh_cmd("cat ~/trading-bot/config/config.json | python3 -m json.tool | grep -E '(mode|adx_threshold|rvol_threshold|min_timeframe_alignment|portfolio_symbols|take_profit_pct)' | head -15", timeout=8)
if config_check:
    print(config_check)
else:
    print("   Could not read config")

# 3. Check last 5 trade log entries
print("\n3. Recent Trade Activity:")
trades = ssh_cmd("tail -5 ~/trading-bot/logs/trades.log 2>/dev/null", timeout=8)
if trades:
    print(trades)
else:
    print("   No trades log or connection timeout")

# 4. Check for errors
print("\n4. Recent Errors:")
errors = ssh_cmd("grep -i error ~/trading-bot/logs/system.log 2>/dev/null | tail -3", timeout=8)
if errors:
    print(errors)
else:
    print("   No recent errors")

# 5. Check restart pattern
print("\n5. Bot Restart Check:")
restarts = ssh_cmd("grep 'Starting TradingBot' ~/trading-bot/logs/system.log 2>/dev/null | tail -5", timeout=8)
if restarts:
    lines = restarts.split('\n')
    print(f"   Found {len(lines)} recent starts (last 5):")
    for line in lines:
        print(f"   {line}")
else:
    print("   No restart data")

print("\n" + "="*80)
print("KEY FINDINGS:")
print("="*80)

# Analyze config
if config_check:
    if '"mode": "PAPER"' in config_check:
        print("✅ Mode: PAPER (safe)")
    if '"adx_threshold": 25' in config_check:
        print("✅ ADX threshold: 25.0 (V3.1)")
    if '"rvol_threshold": 1.2' in config_check:
        print("✅ RVOL threshold: 1.2 (V3.1)")
    if '"min_timeframe_alignment": 4' in config_check:
        print("⚠️  Min TF alignment: 4 (should be 3 for V3.1!)")
    elif '"min_timeframe_alignment": 3' in config_check:
        print("✅ Min TF alignment: 3 (V3.1)")
    if '"take_profit_pct": 0.08' in config_check:
        print("✅ Take profit: 8% (V3.1)")

print("\n" + "="*80)
