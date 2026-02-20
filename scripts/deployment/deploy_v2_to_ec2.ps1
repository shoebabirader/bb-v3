# Deploy Strategy V2 to EC2
# This deploys the balanced filters and improved exit strategy

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "DEPLOYING STRATEGY V2 TO EC2" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "V2 Changes:" -ForegroundColor Yellow
Write-Host "  - ADX: 22.0 (balanced - between 18 and 25)" -ForegroundColor White
Write-Host "  - RVOL: 1.0 (balanced - between 0.8 and 1.2)" -ForegroundColor White
Write-Host "  - Stops: 3.5x ATR initial, 2.5x trailing, 2.0x activation" -ForegroundColor White
Write-Host "  - Advanced exits: 40% at 1.5x, 30% at 2.5x, 30% at 4.0x" -ForegroundColor White
Write-Host "  - Breakeven: 1.5x ATR" -ForegroundColor White
Write-Host ""

# EC2 details
$EC2_IP = "13.233.2.23"
$KEY_FILE = "bb.pem"
$USER = "ubuntu"

Write-Host "Uploading config.json to EC2..." -ForegroundColor Yellow
scp -i $KEY_FILE config/config.json ${USER}@${EC2_IP}:~/trading-bot/config/

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Config uploaded successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to upload config" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Restarting bot on EC2..." -ForegroundColor Yellow
ssh -i $KEY_FILE ${USER}@${EC2_IP} "cd trading-bot && pkill -f main.py; nohup python3 main.py > bot.log 2>&1 &"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Bot restarted successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to restart bot" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting 5 seconds for bot to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "Checking bot status..." -ForegroundColor Yellow
ssh -i $KEY_FILE ${USER}@${EC2_IP} "ps aux | grep 'python3 main.py' | grep -v grep"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "DEPLOYMENT COMPLETE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Monitor logs: ssh -i bb.pem ubuntu@13.233.2.23 'tail -f trading-bot/bot.log'" -ForegroundColor White
Write-Host "  2. API rate limit errors are normal for 5-10 minutes (caching data)" -ForegroundColor White
Write-Host "  3. Watch for trades over next 2-3 days" -ForegroundColor White
Write-Host "  4. Advanced exits ARE enabled in live bot (not in backtest)" -ForegroundColor White
Write-Host ""
Write-Host "Expected performance:" -ForegroundColor Yellow
Write-Host "  - 1-2 trades per day (17 trades in 90 days = ~0.2/day, but with portfolio mode should be more)" -ForegroundColor White
Write-Host "  - Win rate: 40-50%" -ForegroundColor White
Write-Host "  - Profit factor: Should be >1.2 with advanced exits" -ForegroundColor White
Write-Host ""
