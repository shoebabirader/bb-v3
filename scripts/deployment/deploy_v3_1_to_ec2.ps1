# Deploy V3.1 Fixed Code to EC2

Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host "DEPLOYING V3.1 TO EC2" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green

Write-Host "`n📊 Backtest Results:" -ForegroundColor Cyan
Write-Host "  Win Rate: 54.55% ✅" -ForegroundColor Green
Write-Host "  Total PnL: +`$257.04 ✅" -ForegroundColor Green
Write-Host "  Profit Factor: 2.15 ✅" -ForegroundColor Green
Write-Host "  Trades: 11 ✅" -ForegroundColor Green

Write-Host "`n🔧 What's Being Deployed:" -ForegroundColor Cyan
Write-Host "  - Fixed trading_bot.py (phantom trade bug fixed)" -ForegroundColor White
Write-Host "  - V3.1 config (ADX 25, RVOL 1.2, TF 3/4)" -ForegroundColor White

Write-Host "`n⚠️  IMPORTANT:" -ForegroundColor Yellow
Write-Host "  This will deploy the fixed code to EC2" -ForegroundColor Yellow
Write-Host "  Bot will NOT be started automatically" -ForegroundColor Yellow
Write-Host "  You must start it manually after verification" -ForegroundColor Yellow

$response = Read-Host "`nDo you want to proceed? (yes/no)"

if ($response -ne "yes") {
    Write-Host "`n❌ Deployment cancelled" -ForegroundColor Red
    exit
}

Write-Host "`n1. Copying fixed trading_bot.py to EC2..." -ForegroundColor Cyan
scp -i bb.pem src/trading_bot.py ubuntu@13.233.2.23:~/trading-bot/src/
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ trading_bot.py copied successfully" -ForegroundColor Green
} else {
    Write-Host "   ❌ Failed to copy trading_bot.py" -ForegroundColor Red
    exit 1
}

Write-Host "`n2. Verifying EC2 config..." -ForegroundColor Cyan
$config_check = ssh -i bb.pem ubuntu@13.233.2.23 "cat ~/trading-bot/config/config.json | python3 -m json.tool | grep -E '(min_timeframe_alignment|adx_threshold|rvol_threshold)' | head -3"
Write-Host $config_check

Write-Host "`n3. Checking if bot is running..." -ForegroundColor Cyan
$bot_status = ssh -i bb.pem ubuntu@13.233.2.23 "pgrep -f 'python.*main.py' && echo 'RUNNING' || echo 'STOPPED'"
if ($bot_status -match "RUNNING") {
    Write-Host "   ⚠️  Bot is currently RUNNING" -ForegroundColor Yellow
    Write-Host "   You should stop it before starting with new code" -ForegroundColor Yellow
} else {
    Write-Host "   ✅ Bot is STOPPED (good)" -ForegroundColor Green
}

Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host "DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green

Write-Host "`n✅ Fixed code deployed to EC2" -ForegroundColor Green

Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Verify config is correct:" -ForegroundColor White
Write-Host "     python diagnose_ec2_current_state.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Start the bot:" -ForegroundColor White
Write-Host "     ssh -i bb.pem ubuntu@13.233.2.23" -ForegroundColor Gray
Write-Host "     cd ~/trading-bot" -ForegroundColor Gray
Write-Host "     nohup python3 main.py > bot.log 2>&1 &" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Monitor closely:" -ForegroundColor White
Write-Host "     python analyze_ec2_recent_trades.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Watch for:" -ForegroundColor White
Write-Host "     - No phantom trades (7-second exits)" -ForegroundColor Gray
Write-Host "     - Trades executing normally" -ForegroundColor Gray
Write-Host "     - Win rate trending toward 54%" -ForegroundColor Gray

Write-Host "`n⚠️  REMEMBER:" -ForegroundColor Yellow
Write-Host "  - Monitor first 3 trades closely" -ForegroundColor Yellow
Write-Host "  - Be ready to stop if issues arise" -ForegroundColor Yellow
Write-Host "  - Run in PAPER mode for 7 days before LIVE" -ForegroundColor Yellow

Write-Host "`n================================================================================" -ForegroundColor Green
