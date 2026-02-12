#!/usr/bin/env python3
"""Check if the bot is healthy and processing data."""

import os
import time
from datetime import datetime

def check_log_activity():
    """Check if logs are being written (bot is active)."""
    log_files = ['logs/system.log', 'logs/errors.log', 'logs/trades.log']
    
    print("=" * 80)
    print("BOT HEALTH CHECK")
    print("=" * 80)
    print()
    
    for log_file in log_files:
        if os.path.exists(log_file):
            mtime = os.path.getmtime(log_file)
            last_modified = datetime.fromtimestamp(mtime)
            age_seconds = time.time() - mtime
            age_minutes = age_seconds / 60
            
            print(f"{log_file}:")
            print(f"  Last modified: {last_modified}")
            print(f"  Age: {age_minutes:.1f} minutes ago")
            
            if age_minutes < 5:
                print(f"  Status: ✓ ACTIVE (recently updated)")
            elif age_minutes < 15:
                print(f"  Status: ⚠ POSSIBLY STUCK (no updates for {age_minutes:.1f} min)")
            else:
                print(f"  Status: ✗ LIKELY CRASHED (no updates for {age_minutes:.1f} min)")
            print()
    
    # Check if python process exists
    import subprocess
    try:
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True)
        if 'python.exe' in result.stdout:
            print("✓ Python process is running")
            # Count how many
            count = result.stdout.count('python.exe')
            print(f"  Found {count} python.exe process(es)")
        else:
            print("✗ No python.exe process found - bot is NOT running")
    except Exception as e:
        print(f"Could not check process: {e}")
    
    print()
    print("=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)
    
    # Get most recent log timestamp
    most_recent = 0
    for log_file in log_files:
        if os.path.exists(log_file):
            mtime = os.path.getmtime(log_file)
            most_recent = max(most_recent, mtime)
    
    age_minutes = (time.time() - most_recent) / 60
    
    if age_minutes < 5:
        print("Bot appears to be running normally.")
    elif age_minutes < 15:
        print("Bot may be stuck. Consider restarting if no activity in next 5 minutes.")
    else:
        print("Bot appears to be crashed or stuck. RESTART RECOMMENDED.")
        print()
        print("To restart:")
        print("  1. Kill the process: taskkill /F /IM python.exe")
        print("  2. Start bot: python main.py")

if __name__ == "__main__":
    check_log_activity()
