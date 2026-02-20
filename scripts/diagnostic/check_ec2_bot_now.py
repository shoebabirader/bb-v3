"""Check EC2 bot status in real-time."""

import subprocess
import sys
from datetime import datetime

def run_ssh_command(command):
    """Run SSH command on EC2."""
    full_command = f'ssh -i bb.pem ubuntu@13.233.2.23 "{command}"'
    try:
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1

def main():
    """Check EC2 bot status."""
    print("\n" + "="*80)
    print("EC2 BOT STATUS CHECK")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"EC2 IP: 13.233.2.23 (Mumbai)")
    
    # Check if bot process is running
    print("\n1. Checking if bot is running...")
    print("-"*80)
    stdout, stderr, code = run_ssh_command("ps aux | grep 'python.*main.py' | grep -v grep")
    
    if code == 0 and stdout.strip():
        print("✅ BOT IS RUNNING")
        lines = stdout.strip().split('\n')
        for line in lines:
            parts = line.split()
            if len(parts) >= 11:
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                time_running = parts[9]
                print(f"   PID: {pid}")
                print(f"   CPU: {cpu}%")
                print(f"   Memory: {mem}%")
                print(f"   Running time: {time_running}")
    else:
        print("❌ BOT IS NOT RUNNING")
        if stderr:
            print(f"   Error: {stderr}")
    
    # Check recent trades
    print("\n2. Checking recent trades...")
    print("-"*80)
    stdout, stderr, code = run_ssh_command("tail -20 ~/trading-bot/logs/trades.log 2>/dev/null || echo 'No trades log found'")
    
    if stdout.strip():
        print(stdout.strip())
    else:
        print("   No recent trades found")
    
    # Check system log for errors
    print("\n3. Checking system log (last 20 lines)...")
    print("-"*80)
    stdout, stderr, code = run_ssh_command("tail -20 ~/trading-bot/logs/system.log 2>/dev/null || echo 'No system log found'")
    
    if stdout.strip():
        lines = stdout.strip().split('\n')
        for line in lines[-20:]:
            if 'ERROR' in line or 'CRITICAL' in line:
                print(f"   ❌ {line}")
            elif 'WARNING' in line:
                print(f"   ⚠️  {line}")
            else:
                print(f"   {line}")
    else:
        print("   No system log found")
    
    # Check bot uptime
    print("\n4. Checking bot uptime...")
    print("-"*80)
    stdout, stderr, code = run_ssh_command("ps -p $(pgrep -f 'python.*main.py' | head -1) -o etime= 2>/dev/null || echo 'Not running'")
    
    if stdout.strip() and stdout.strip() != 'Not running':
        print(f"   Uptime: {stdout.strip()}")
    else:
        print("   Bot is not running")
    
    # Check if bot is restarting
    print("\n5. Checking for restart pattern...")
    print("-"*80)
    stdout, stderr, code = run_ssh_command("grep 'Starting TradingBot' ~/trading-bot/logs/system.log 2>/dev/null | tail -10")
    
    if stdout.strip():
        lines = stdout.strip().split('\n')
        print(f"   Found {len(lines)} recent starts:")
        for line in lines[-5:]:
            print(f"   {line}")
        
        if len(lines) > 5:
            print(f"\n   ⚠️  WARNING: Bot has restarted {len(lines)} times recently!")
            print("   This suggests the bot is crashing and being auto-restarted")
    else:
        print("   No restart pattern detected")
    
    # Check config
    print("\n6. Checking bot configuration...")
    print("-"*80)
    stdout, stderr, code = run_ssh_command("cat ~/trading-bot/config/config.json | grep -E '(mode|adx_threshold|rvol_threshold|min_timeframe_alignment|portfolio_symbols)' | head -10")
    
    if stdout.strip():
        print(stdout.strip())
    else:
        print("   Could not read config")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    # Check if running
    stdout, stderr, code = run_ssh_command("pgrep -f 'python.*main.py' > /dev/null && echo 'RUNNING' || echo 'STOPPED'")
    status = stdout.strip()
    
    if status == "RUNNING":
        print("\n✅ Bot is RUNNING on EC2")
        print("\n📊 What to monitor:")
        print("   - Check if trades are being executed")
        print("   - Monitor for restart patterns")
        print("   - Watch for errors in system log")
        print("   - Verify V3.1 settings are active (ADX 25, RVOL 1.2, 3/4 TF)")
    else:
        print("\n❌ Bot is STOPPED on EC2")
        print("\n🔧 To start the bot:")
        print("   ssh -i bb.pem ubuntu@13.233.2.23")
        print("   cd ~/trading-bot")
        print("   nohup python3 main.py > bot.log 2>&1 &")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
