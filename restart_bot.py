"""Stop the current bot and provide instructions to restart."""

import psutil
import sys

def restart_bot():
    """Stop current bot process."""
    
    print("=" * 80)
    print("RESTARTING BOT")
    print("=" * 80)
    
    # Find and stop the bot
    bot_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline:
                cmdline_str = ' '.join(cmdline)
                
                if 'python' in cmdline_str.lower() and 'main.py' in cmdline_str:
                    bot_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if bot_processes:
        print(f"\nFound {len(bot_processes)} bot process(es) running")
        
        for proc in bot_processes:
            try:
                print(f"Stopping PID {proc.pid}...")
                proc.terminate()
                proc.wait(timeout=5)
                print(f"✓ Stopped PID {proc.pid}")
            except psutil.TimeoutExpired:
                print(f"Force killing PID {proc.pid}...")
                proc.kill()
                print(f"✓ Killed PID {proc.pid}")
            except Exception as e:
                print(f"✗ Error stopping PID {proc.pid}: {e}")
        
        print("\n" + "=" * 80)
        print("BOT STOPPED")
        print("=" * 80)
    else:
        print("\n✗ No bot process found running")
        print("\n" + "=" * 80)
        print("BOT NOT RUNNING")
        print("=" * 80)
    
    print("\n" + "=" * 80)
    print("CONFIGURATION UPDATED")
    print("=" * 80)
    print("\nSimplified configuration applied:")
    print("  ✓ Advanced features disabled (for stability)")
    print("  ✓ Portfolio management enabled")
    print("  ✓ Mode: LIVE")
    print("  ✓ Symbols: XAGUSDT, XAUUSDT, SOLUSDT, RIVERUSDT, ETHUSDT")
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("\n1. Start the bot:")
    print("   python main.py")
    print("\n2. Monitor the terminal output")
    print("   - Bot should start without crashes")
    print("   - Watch for signal detection")
    print("   - Watch for trade execution")
    print("\n3. Once stable and executing trades, you can gradually")
    print("   re-enable advanced features one at a time")

if __name__ == "__main__":
    try:
        restart_bot()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
