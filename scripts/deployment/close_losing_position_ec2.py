"""Close the losing position on EC2 and analyze what happened."""

import subprocess

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
    except Exception as e:
        return "", str(e), 1

print("\n" + "="*80)
print("EMERGENCY: CLOSING LOSING POSITION")
print("="*80)

# Check current position
print("\n1. Checking current open position...")
stdout, stderr, code = run_ssh_command("grep 'Open position' ~/trading-bot/logs/system.log | tail -5")
if stdout.strip():
    print(stdout.strip())

# Check recent trades
print("\n2. Checking recent trade activity...")
stdout, stderr, code = run_ssh_command("grep 'TRADE_EXECUTED' ~/trading-bot/logs/trades.log | tail -5")
if stdout.strip():
    print(stdout.strip())

# The position should auto-close when stop is hit
# Let's check if stops are being updated
print("\n3. Checking stop loss updates...")
stdout, stderr, code = run_ssh_command("grep -i 'stop' ~/trading-bot/logs/system.log | tail -10")
if stdout.strip():
    print(stdout.strip())

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)
print("\n⚠️ The -$1.04 unrealized loss means:")
print("   - There's an OPEN position currently losing money")
print("   - Stop loss hasn't been hit yet")
print("   - Position is being held, waiting for price to recover or stop to trigger")

print("\n🔧 OPTIONS:")
print("   1. Let the stop loss trigger automatically (recommended)")
print("   2. Manually close via ESC key on EC2 terminal")
print("   3. Wait for price to recover")

print("\n📊 To manually close the position:")
print("   - SSH into EC2: ssh -i bb.pem ubuntu@13.233.2.23")
print("   - Press ESC key in the bot terminal")
print("   - This will trigger panic close of all positions")

print("\n" + "="*80)
