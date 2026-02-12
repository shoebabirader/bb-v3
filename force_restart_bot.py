"""Force kill the old bot process and provide restart instructions."""

import psutil
import sys

print("=" * 80)
print("FORCE RESTART BOT")
print("=" * 80)
print()

# Find and kill bot processes
print("Looking for bot processes...")
print()

killed_processes = []

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info['cmdline']
        if cmdline:
            cmdline_str = ' '.join(cmdline)
            if 'python' in cmdline_str.lower() and 'main.py' in cmdline_str:
                pid = proc.info['pid']
                print(f"Found bot process (PID: {pid})")
                print(f"  Command: {cmdline_str}")
                print(f"  Killing...")
                
                proc.kill()
                proc.wait(timeout=5)
                
                print(f"  ✓ Killed")
                killed_processes.append(pid)
                print()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
        print(f"  ⚠️  Error: {e}")
        pass

if killed_processes:
    print(f"✓ Killed {len(killed_processes)} bot process(es)")
else:
    print("No bot processes found running")

print()
print("=" * 80)
print("NOW RESTART THE BOT")
print("=" * 80)
print()
print("Run this command:")
print("  python main.py")
print()
print("The bot will:")
print("  1. Authenticate with Binance (should work now)")
print("  2. Detect the XAGUSDT SHORT signal")
print("  3. Execute the trade within 1-2 minutes")
print()
print("Watch the terminal for:")
print("  '[XAGUSDT] Position opened: SHORT @ $XX.XX'")
print()
