# Start EC2 Bot with V3.1 Fixed Code

Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host "STARTING EC2 BOT WITH V3.1" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green

Write-Host "`n✅ Fixed code deployed" -ForegroundColor Green
Write-Host "✅ Config verified (ADX 25, RVOL 1.2, TF 3/4)" -ForegroundColor Green
Write-Host "✅ Backtest successful (54.55% win rate)" -ForegroundColor Green

Write-Host "`n🚀 Starting bot on EC2..." -ForegroundColor Cyan
ssh -i bb.pem ubuntu@13.233.2.23 "sudo systemctl start trading-bot"

Start-Sleep -Seconds 3

Write-Host "`n📊 Checking bot status..." -ForegroundColor Cyan
$status = ssh -i bb.pem ubuntu@13.233.2.23 "sudo systemctl is-active trading-bot"

if ($status -match "active") {
    Write-Host "✅ Bot is RUNNING!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Bot status: $status" -ForegroundColor Yellow
    Write-Host "Checking detailed status..." -ForegroundColor Cyan
    ssh -i bb.pem ubuntu@13.233.2.23 "sudo systemctl status trading-bot"
}

Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host "BOT STARTED" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green

Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Monitor for first 3 trades" -ForegroundColor White
Write-Host "  2. Check for phantom trades (should be NONE)" -ForegroundColor White
Write-Host "  3. Verify win rate trends toward 54%" -ForegroundColor White
Write-Host "  4. Watch for 7 days before considering LIVE" -ForegroundColor White

Write-Host "`n📞 Monitoring Commands:" -ForegroundColor Cyan
Write-Host "  python analyze_ec2_recent_trades.py" -ForegroundColor Gray
Write-Host "  python diagnose_ec2_current_state.py" -ForegroundColor Gray

Write-Host "`n⚠️  IMPORTANT:" -ForegroundColor Yellow
Write-Host "  - Bot is in PAPER mode (safe)" -ForegroundColor Yellow
Write-Host "  - Monitor daily" -ForegroundColor Yellow
Write-Host "  - Be ready to stop if issues" -ForegroundColor Yellow

Write-Host "`n================================================================================" -ForegroundColor Green
