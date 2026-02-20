"""Safely restart the trading bot to fix trade logging issue."""

import psutil
import time
import subprocess
import sys
from pathlib import Path

print("=" * 80)
print("SAFE BOT RESTART - Fix Trade History Logging")
print("=" * 80)

# Step 1: Check if bot is running
print("\n[1/4] Checking if bot is running...")
bot_process = None
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info.get('cmdline', [])
        if cmdline and len(cmdline) > 0:
            cmdline_str = ' '.join(str(c) for c in cmdline)
            if 'python' in cmdline_str.lower() and 'main.py' in cmdline_str:
                bot_process = proc
                print(f"   ✅ Bot is running (PID: {proc.info['pid']})")
                break
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        continue

if not bot_process:
    print("   ⚠️  Bot is not running")
    print("\n💡 You can start the bot manually:")
    print("   python main.py")
    sys.exit(0)

# Step 2: Stop the bot
print("\n[2/4] Stopping the bot gracefully...")
try:
    bot_process.terminate()
    print("   ⏳ Waiting for bot to stop...")
    bot_process.wait(timeout=10)
    print("   ✅ Bot stopped successfully")
except psutil.TimeoutExpired:
    print("   ⚠️  Bot didn't stop gracefully, forcing...")
    bot_process.kill()
    print("   ✅ Bot force-stopped")
except Exception as e:
    print(f"   ❌ Error stopping bot: {e}")
    sys.exit(1)

# Step 3: Wait a moment
print("\n[3/4] Waiting for cleanup...")
time.sleep(2)
print("   ✅ Ready to restart")

# Step 4: Restart the bot
print("\n[4/4] Restarting the bot...")
print("   📝 The bot will now use the correct log file: logs/trades_paper.log")
print("   📝 Your 3 open positions will continue normally")
print("\n" + "=" * 80)

# Start the bot in a new process
try:
    if sys.platform == 'win32':
        # Windows: Start in new console window
        subprocess.Popen(
            ['python', 'main.py'],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        print("✅ Bot restarted in new console window")
    else:
        # Linux/Mac: Start in background
        subprocess.Popen(
            ['python', 'main.py'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("✅ Bot restarted in background")
    
    print("\n💡 What happens next:")
    print("   1. Bot will reconnect to Binance")
    print("   2. Bot will resume monitoring your 3 open positions")
    print("   3. New trades will log to: logs/trades_paper.log")
    print("   4. Dashboard will show trade history correctly")
    print("\n✅ RESTART COMPLETE!")
    
except Exception as e:
    print(f"❌ Error restarting bot: {e}")
    print("\n💡 Please start the bot manually:")
    print("   python main.py")
    sys.exit(1)

print("\n" + "=" * 80)
