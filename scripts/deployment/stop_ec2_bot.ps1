# Stop EC2 Bot Immediately
$EC2_IP = "13.233.2.23"
$KEY_FILE = "bb.pem"
$USER = "ubuntu"

Write-Host "`n========================================" -ForegroundColor Red
Write-Host "STOPPING EC2 BOT" -ForegroundColor Red
Write-Host "========================================`n" -ForegroundColor Red

Write-Host "[1/2] Killing all bot processes..." -ForegroundColor Yellow
ssh -i $KEY_FILE -o StrictHostKeyChecking=no ${USER}@${EC2_IP} "pkill -9 -f 'python.*main.py'"

Start-Sleep -Seconds 2

Write-Host "`n[2/2] Verifying bot is stopped..." -ForegroundColor Yellow
$result = ssh -i $KEY_FILE -o StrictHostKeyChecking=no ${USER}@${EC2_IP} "ps aux | grep python | grep main.py | grep -v grep"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n❌ Bot is still running!" -ForegroundColor Red
} else {
    Write-Host "`n✅ Bot stopped successfully!" -ForegroundColor Green
}

Write-Host "`n========================================" -ForegroundColor Red
Write-Host "EC2 BOT STOPPED" -ForegroundColor Red
Write-Host "========================================`n" -ForegroundColor Red
