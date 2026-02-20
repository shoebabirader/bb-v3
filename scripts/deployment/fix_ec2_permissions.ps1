# Fix EC2 Log Permissions Issue
$EC2_IP = "13.233.2.23"
$KEY_FILE = "bb.pem"

Write-Host "Fixing EC2 log permissions..." -ForegroundColor Cyan

# Stop bot
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl stop trading-bot'

# Remove old log files that might have wrong permissions
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo rm -f /home/ubuntu/trading-bot/logs/bot.log /home/ubuntu/trading-bot/logs/bot_error.log'

# Recreate logs directory with correct permissions
ssh -i $KEY_FILE ubuntu@$EC2_IP 'mkdir -p /home/ubuntu/trading-bot/logs && chmod 755 /home/ubuntu/trading-bot/logs'

# Create empty log files with correct permissions
ssh -i $KEY_FILE ubuntu@$EC2_IP 'touch /home/ubuntu/trading-bot/logs/bot.log /home/ubuntu/trading-bot/logs/bot_error.log && chmod 644 /home/ubuntu/trading-bot/logs/*.log'

# Ensure ubuntu user owns everything
ssh -i $KEY_FILE ubuntu@$EC2_IP 'chown -R ubuntu:ubuntu /home/ubuntu/trading-bot'

Write-Host "Permissions fixed. Restarting bot..." -ForegroundColor Green

# Restart bot
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl restart trading-bot'
Start-Sleep -Seconds 5

# Check status
Write-Host "`nBot Status:" -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl status trading-bot --no-pager'

Write-Host "`nRecent Logs:" -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'tail -30 /home/ubuntu/trading-bot/logs/bot.log 2>/dev/null || echo "No logs yet"'
