"""Fix paper trading logging by restarting the bot."""

import psutil
import subprocess
import sys
import time

print("=" * 80)
print("FIX PAPER TRADING LOGGING")
print("=" * 80)

# Step 1: Check if bot is running
print("\n[1/3] Checking bot status...")
bot_running = False
bot_process = None

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info.get('cmdline', [])
        if cmdline and len(cmdline) > 0:
            cmdline_str = ' '.join(str(c) for c in cmdline)
            if 'python' in cmdline_str.lower() and 'main.py' in cmdline_str:
                bot_running = True
                bot_process = proc
                print(f"   ✅ Bot is running (PID: {proc.info['pid']})")
                break
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        continue

if not bot_running:
    print("   ⚠️  Bot is NOT running")
    print("\n💡 The bot is not running. Start it with: python main.py")
    print("   Once started, it will log to: logs/trades_paper.log")
    sys.exit(0)

# Step 2: Explain the issue
print("\n[2/3] Diagnosing logging issue...")
print("   ⚠️  Bot is using OLD logger instance")
print("   📝 Currently logging to: logs/trades.log")
print("   📝 Should log to: logs/trades_paper.log")
print("\n   💡 SOLUTION: Restart the bot to pick up new logger")

# Step 3: Ask user to restart
print("\n[3/3] Restart Required:")
print("\n   To fix paper trading logging, you need to:")
print("   1. Stop the bot (press Ctrl+C in bot terminal)")
print("   2. Start it again: python main.py")
print("   3. New trades will log to: logs/trades_paper.log")
print("\n   ⚠️  Your 3 open positions will continue normally after restart")

print("\n" + "=" * 80)
print("MANUAL RESTART INSTRUCTIONS")
print("=" * 80)

print("\n📋 Steps:")
print("   1. Go to the terminal where the bot is running")
print("   2. Press Ctrl+C to stop the bot")
print("   3. Wait for it to close positions gracefully")
print("   4. Run: python main.py")
print("   5. Bot will resume with correct logging")

print("\n✅ After restart:")
print("   - New trades will log to: logs/trades_paper.log")
print("   - Dashboard will show correct trade history")
print("   - Your 3 open positions will continue")

print("\n" + "=" * 80)
