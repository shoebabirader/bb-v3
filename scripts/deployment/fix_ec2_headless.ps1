# Fix EC2 Headless Mode Issue
# This script deploys the fix for pynput keyboard listener on headless EC2

$EC2_IP = "13.233.2.23"
$KEY_FILE = "bb.pem"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploying Headless Mode Fix to EC2" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop the bot
Write-Host "[1] Stopping bot service..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl stop trading-bot'
Write-Host "Bot stopped." -ForegroundColor Green
Write-Host ""

# Step 2: Upload fixed trading_bot.py
Write-Host "[2] Uploading fixed trading_bot.py..." -ForegroundColor Yellow
scp -i $KEY_FILE src/trading_bot.py ubuntu@${EC2_IP}:/home/ubuntu/trading-bot/src/trading_bot.py
Write-Host "File uploaded." -ForegroundColor Green
Write-Host ""

# Step 3: Restart the bot
Write-Host "[3] Restarting bot service..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl restart trading-bot'
Start-Sleep -Seconds 3
Write-Host ""

# Step 4: Check status
Write-Host "[4] Checking bot status..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl status trading-bot --no-pager -l'
Write-Host ""

# Step 5: Show recent logs
Write-Host "[5] Recent logs (last 30 lines)..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'tail -30 /home/ubuntu/trading-bot/logs/bot.log 2>/dev/null || tail -30 /home/ubuntu/trading-bot/logs/bot_error.log 2>/dev/null || echo "Waiting for logs..."'
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix Deployed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Monitor logs with:" -ForegroundColor Yellow
Write-Host "  ssh -i $KEY_FILE ubuntu@$EC2_IP 'tail -f /home/ubuntu/trading-bot/logs/bot.log'" -ForegroundColor White
Write-Host ""
