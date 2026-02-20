# Complete EC2 Fix - Headless Mode + Permissions
$EC2_IP = "13.233.2.23"
$KEY_FILE = "bb.pem"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Complete EC2 Fix Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop the bot
Write-Host "[1] Stopping bot service..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl stop trading-bot'
Write-Host "Bot stopped." -ForegroundColor Green
Write-Host ""

# Step 2: Fix log permissions
Write-Host "[2] Fixing log file permissions..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo chown -R ubuntu:ubuntu /home/ubuntu/trading-bot/logs && chmod -R 755 /home/ubuntu/trading-bot/logs'
Write-Host "Permissions fixed." -ForegroundColor Green
Write-Host ""

# Step 3: Clear Python cache
Write-Host "[3] Clearing Python cache..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'find /home/ubuntu/trading-bot -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true'
ssh -i $KEY_FILE ubuntu@$EC2_IP 'find /home/ubuntu/trading-bot -type f -name "*.pyc" -delete 2>/dev/null || true'
Write-Host "Cache cleared." -ForegroundColor Green
Write-Host ""

# Step 4: Upload fixed trading_bot.py
Write-Host "[4] Uploading fixed trading_bot.py..." -ForegroundColor Yellow
scp -i $KEY_FILE src/trading_bot.py ubuntu@${EC2_IP}:/home/ubuntu/trading-bot/src/trading_bot.py
Write-Host "File uploaded." -ForegroundColor Green
Write-Host ""

# Step 5: Verify the fix is in place
Write-Host "[5] Verifying fix..." -ForegroundColor Yellow
$checkResult = ssh -i $KEY_FILE ubuntu@$EC2_IP 'grep -c "KEYBOARD_AVAILABLE" /home/ubuntu/trading-bot/src/trading_bot.py'
if ($checkResult -gt 0) {
    Write-Host "Fix verified in file" -ForegroundColor Green
} else {
    Write-Host "Fix not found in file!" -ForegroundColor Red
}
Write-Host ""

# Step 6: Restart the bot
Write-Host "[6] Restarting bot service..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl restart trading-bot'
Start-Sleep -Seconds 5
Write-Host ""

# Step 7: Check status
Write-Host "[7] Checking bot status..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl status trading-bot --no-pager -l'
Write-Host ""

# Step 8: Show recent logs
Write-Host "[8] Recent logs..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'tail -40 /home/ubuntu/trading-bot/logs/bot.log 2>/dev/null || tail -40 /home/ubuntu/trading-bot/logs/bot_error.log 2>/dev/null || echo "Waiting for logs..."'
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
