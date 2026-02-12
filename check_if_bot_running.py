"""Check if the trading bot is currently running and processing XAGUSDT."""

import psutil
import sys

def check_bot_running():
    """Check if main.py or start_paper_trading.py is running."""
    
    print("=" * 80)
    print("CHECKING IF BOT IS RUNNING")
    print("=" * 80)
    
    bot_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline:
                cmdline_str = ' '.join(cmdline)
                
                # Check if it's running main.py or start_paper_trading.py
                if 'python' in cmdline_str.lower() and ('main.py' in cmdline_str or 'start_paper_trading.py' in cmdline_str):
                    bot_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline_str
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if bot_processes:
        print(f"\n✓ FOUND {len(bot_processes)} BOT PROCESS(ES) RUNNING:\n")
        for proc in bot_processes:
            print(f"  PID: {proc['pid']}")
            print(f"  Name: {proc['name']}")
            print(f"  Command: {proc['cmdline']}")
            print()
        
        print("=" * 80)
        print("BOT IS RUNNING")
        print("=" * 80)
        print("\nThe bot should be processing signals automatically.")
        print("If XAGUSDT SHORT signal exists but trade not executing, check:")
        print("1. Bot terminal output for errors")
        print("2. Check logs/trades.log for any error messages")
        print("3. Verify the bot is in LIVE mode (not PAPER)")
        print("4. Check if there's already an open position for XAGUSDT")
        
    else:
        print("\n✗ NO BOT PROCESS FOUND")
        print("\n" + "=" * 80)
        print("BOT IS NOT RUNNING!")
        print("=" * 80)
        print("\nThe bot needs to be started to execute trades.")
        print("\nTo start the bot:")
        print("  python main.py")
        print("\nOr for paper trading:")
        print("  python start_paper_trading.py")

if __name__ == "__main__":
    try:
        check_bot_running()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
