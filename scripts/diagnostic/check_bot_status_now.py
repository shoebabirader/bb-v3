"""Check current bot status - running locally or on EC2."""

import os
import time
from datetime import datetime

def check_local_bot():
    """Check if bot is running locally."""
    print("\n" + "="*80)
    print("CHECKING LOCAL BOT STATUS")
    print("="*80)
    
    # Check for recent log files
    log_files = [
        "logs/trades.log",
        "logs/system.log",
        "logs/trades_paper.log"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            # Get file modification time
            mod_time = os.path.getmtime(log_file)
            mod_datetime = datetime.fromtimestamp(mod_time)
            age_seconds = time.time() - mod_time
            
            print(f"\n📄 {log_file}")
            print(f"   Last modified: {mod_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Age: {age_seconds:.0f} seconds ago")
            
            if age_seconds < 60:
                print(f"   ✅ ACTIVE (modified within last minute)")
                
                # Show last 10 lines
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        print(f"\n   Last 10 lines:")
                        for line in lines[-10:]:
                            print(f"   {line.rstrip()}")
                except Exception as e:
                    print(f"   ⚠️ Could not read file: {e}")
            else:
                print(f"   ⏸️ INACTIVE (last modified {age_seconds/60:.1f} minutes ago)")
        else:
            print(f"\n📄 {log_file}")
            print(f"   ❌ File not found")
    
    # Check config
    print("\n📊 CURRENT CONFIGURATION:")
    try:
        import json
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        
        print(f"   Mode: {config.get('mode', 'N/A')}")
        print(f"   Run Mode: {config.get('run_mode', 'N/A')}")
        print(f"   Symbols: {', '.join(config.get('portfolio_symbols', [config.get('symbol', 'N/A')]))}")
        print(f"   ADX Threshold: {config.get('adx_threshold', 'N/A')}")
        print(f"   RVOL Threshold: {config.get('rvol_threshold', 'N/A')}")
        print(f"   Min TF Alignment: {config.get('min_timeframe_alignment', 'N/A')}/4")
        print(f"   Risk per Trade: {config.get('risk_per_trade', 'N/A')*100:.1f}%")
        print(f"   Leverage: {config.get('leverage', 'N/A')}x")
    except Exception as e:
        print(f"   ⚠️ Could not read config: {e}")

def main():
    """Main function."""
    print("\n" + "="*80)
    print("BOT STATUS CHECK")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    check_local_bot()
    
    print("\n" + "="*80)
    print("WHAT TO CHECK:")
    print("="*80)
    print("\n1. Is the bot process running?")
    print("   - Check Task Manager (Windows) or Activity Monitor (Mac)")
    print("   - Look for 'python.exe' or 'python' process running main.py")
    
    print("\n2. Are logs being updated?")
    print("   - Check if log files are being modified (see above)")
    print("   - If logs are old, bot may have crashed")
    
    print("\n3. Is the bot in the right mode?")
    print("   - PAPER mode: Safe for testing")
    print("   - LIVE mode: Real money at risk")
    print("   - BACKTEST mode: Historical testing only")
    
    print("\n4. Are there any errors in logs?")
    print("   - Check logs/system.log for errors")
    print("   - Check logs/trades.log for trade activity")
    
    print("\n5. Is the bot generating signals?")
    print("   - With V3.1 settings, should see signals if market conditions are right")
    print("   - ADX 25, RVOL 1.2, 3/4 timeframes")
    
    print("\n" + "="*80)
    print("COMMANDS TO CHECK BOT:")
    print("="*80)
    print("\nLocal bot:")
    print("  - View logs: type logs\\trades_paper.log")
    print("  - View system log: type logs\\system.log")
    print("  - Check processes: tasklist | findstr python")
    
    print("\nEC2 bot (if deployed):")
    print("  - Check status: ssh -i bb.pem ubuntu@13.233.2.23 \"ps aux | grep python\"")
    print("  - View logs: ssh -i bb.pem ubuntu@13.233.2.23 \"tail -50 ~/trading-bot/logs/trades.log\"")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
