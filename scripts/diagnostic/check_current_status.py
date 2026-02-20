#!/usr/bin/env python3
"""Check current bot status and recent activity."""

import json
import os
from datetime import datetime

print("=" * 80)
print("CURRENT BOT STATUS")
print("=" * 80)
print()

# Check config
with open('config/config.json', 'r') as f:
    config = json.load(f)

print(f"Mode: {config['run_mode']}")
print(f"Symbol: {config['symbol']}")
print(f"Risk per trade: {config['risk_per_trade']}%")
print(f"Leverage: {config['leverage']}x")
print()

# Check if bot is running
import subprocess
result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                      capture_output=True, text=True)
if 'python.exe' in result.stdout:
    count = result.stdout.count('python.exe')
    print(f"✓ Bot is RUNNING ({count} python process(es))")
else:
    print("✗ Bot is NOT running")
print()

# Check recent logs
print("Recent system log entries:")
print("-" * 80)
if os.path.exists('logs/system.log'):
    with open('logs/system.log', 'r') as f:
        lines = f.readlines()
        for line in lines[-5:]:
            print(line.strip())
print()

# Check for errors
print("Recent error log entries:")
print("-" * 80)
if os.path.exists('logs/errors.log'):
    with open('logs/errors.log', 'r') as f:
        lines = f.readlines()
        if len(lines) > 0:
            for line in lines[-10:]:
                print(line.strip())
        else:
            print("No errors logged")
else:
    print("No error log found")
print()

# Check startup debug log
print("Startup debug log (last 20 lines):")
print("-" * 80)
if os.path.exists('logs/startup_debug.log'):
    with open('logs/startup_debug.log', 'r') as f:
        lines = f.readlines()
        for line in lines[-20:]:
            print(line.strip())
else:
    print("No startup debug log found")
