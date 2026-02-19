# Deploy Fixed Strategy to EC2
$EC2_IP = "13.233.2.23"
$KEY_FILE = "bb.pem"
$USER = "ubuntu"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "DEPLOYING FIXED STRATEGY TO EC2" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "[1/5] Stopping any running bot..." -ForegroundColor Yellow
ssh -i $KEY_FILE ${USER}@${EC2_IP} "pkill -9 -f main.py 2>/dev/null || true"
Start-Sleep -Seconds 2

Write-Host "`n[2/5] Backing up old config..." -ForegroundColor Yellow
ssh -i $KEY_FILE ${USER}@${EC2_IP} "cd ~/trading-bot && cp config/config.json config/config.json.backup.$(date +%Y%m%d_%H%M%S)"

Write-Host "`n[3/5] Uploading new config..." -ForegroundColor Yellow
scp -i $KEY_FILE config/config.json ${USER}@${EC2_IP}:~/trading-bot/config/config.json

Write-Host "`n[4/5] Verifying config..." -ForegroundColor Yellow
ssh -i $KEY_FILE ${USER}@${EC2_IP} "cd ~/trading-bot && python3 -c 'import json; json.load(open(\"config/config.json\"))' && echo 'Config valid'"

Write-Host "`n[5/5] Config deployed successfully!" -ForegroundColor Green
Write-Host "`n⚠️  Bot is STOPPED - Do NOT start until backtest is profitable" -ForegroundColor Yellow

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "DEPLOYMENT COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "`nNEW SETTINGS:" -ForegroundColor Cyan
Write-Host "  - ADX Threshold: 30.0 (was 22.0)" -ForegroundColor White
Write-Host "  - RVOL Threshold: 1.5 (was 1.0)" -ForegroundColor White
Write-Host "  - Timeframe Alignment: 4/4 (was 3/4)" -ForegroundColor White
Write-Host "  - Stop Loss: 5.0x ATR (was 3.5x)" -ForegroundColor White
Write-Host "  - Trailing Stop: 4.0x ATR (was 2.5x)" -ForegroundColor White
Write-Host "  - Take Profit: 8% (was 4%)" -ForegroundColor White
Write-Host "  - Risk Per Trade: 2% (was 12%)" -ForegroundColor White
Write-Host "  - Leverage: 10x (was 20x)" -ForegroundColor White
Write-Host "  - Symbols: BTC, ETH, SOL (was RIVER, XRP, ADA, TRX, DOT)" -ForegroundColor White

Write-Host "`nNEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. Run backtest locally: python run_portfolio_backtest.py" -ForegroundColor White
Write-Host "  2. Verify win rate > 50% and profit factor > 1.5" -ForegroundColor White
Write-Host "  3. Only then restart bot on EC2" -ForegroundColor White
