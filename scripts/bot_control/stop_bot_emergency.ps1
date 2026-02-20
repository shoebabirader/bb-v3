# Emergency stop of EC2 bot

Write-Host "`n================================================================================" -ForegroundColor Red
Write-Host "EMERGENCY: STOPPING EC2 BOT" -ForegroundColor Red
Write-Host "================================================================================" -ForegroundColor Red
Write-Host "Reason: Bot is losing money on every trade (-$12.14 total)" -ForegroundColor Yellow
Write-Host "Critical issue: ETHUSDT trade exited in 7 SECONDS with -$10.33 loss`n" -ForegroundColor Yellow

# Stop the bot
Write-Host "1. Stopping bot process..." -ForegroundColor Cyan
ssh -i bb.pem ubuntu@13.233.2.23 "pkill -f main.py"
Start-Sleep -Seconds 2

# Verify stopped
Write-Host "`n2. Verifying bot is stopped..." -ForegroundColor Cyan
$status = ssh -i bb.pem ubuntu@13.233.2.23 "pgrep -f main.py && echo 'STILL RUNNING' || echo 'STOPPED'"

if ($status -match "STOPPED") {
    Write-Host "✅ Bot successfully stopped" -ForegroundColor Green
} else {
    Write-Host "⚠️  Bot may still be running, trying force kill..." -ForegroundColor Yellow
    ssh -i bb.pem ubuntu@13.233.2.23 "pkill -9 -f main.py"
    Start-Sleep -Seconds 2
    $status2 = ssh -i bb.pem ubuntu@13.233.2.23 "pgrep -f main.py && echo 'STILL RUNNING' || echo 'STOPPED'"
    if ($status2 -match "STOPPED") {
        Write-Host "✅ Bot force killed successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Could not stop bot - manual intervention required" -ForegroundColor Red
    }
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "1. Investigate why ETHUSDT trade exited in 7 seconds" -ForegroundColor White
Write-Host "2. Fix the SIGNAL_EXIT bug" -ForegroundColor White
Write-Host "3. Implement V3.2 ultra-conservative settings" -ForegroundColor White
Write-Host "4. Run backtest and verify profitability" -ForegroundColor White
Write-Host "5. Test in paper mode locally before deploying to EC2" -ForegroundColor White
Write-Host "`nDO NOT RESTART BOT until backtest shows positive results!" -ForegroundColor Red
Write-Host "================================================================================" -ForegroundColor Cyan
