# Check EC2 Bot Status and Recent Trades
# EC2 IP: 13.233.2.23 (Mumbai)

$EC2_IP = "13.233.2.23"
$KEY_FILE = "bb.pem"
$USER = "ubuntu"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CHECKING EC2 BOT STATUS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if bot is running
Write-Host "[1/5] Checking if bot process is running..." -ForegroundColor Yellow
ssh -i $KEY_FILE -o StrictHostKeyChecking=no ${USER}@${EC2_IP} "ps aux | grep python | grep main.py | grep -v grep"

Write-Host "`n[2/5] Checking recent log entries (last 50 lines)..." -ForegroundColor Yellow
ssh -i $KEY_FILE -o StrictHostKeyChecking=no ${USER}@${EC2_IP} "tail -50 ~/bb/logs/trades_paper.log 2>/dev/null || tail -50 ~/bb/logs/trades.log 2>/dev/null || echo 'No log file found'"

Write-Host "`n[3/5] Checking for recent trades..." -ForegroundColor Yellow
ssh -i $KEY_FILE -o StrictHostKeyChecking=no ${USER}@${EC2_IP} "grep -E 'Position opened|Position closed|TRADE' ~/bb/logs/trades_paper.log 2>/dev/null | tail -20 || grep -E 'Position opened|Position closed|TRADE' ~/bb/logs/trades.log 2>/dev/null | tail -20 || echo 'No trades found'"

Write-Host "`n[4/5] Checking system log for errors..." -ForegroundColor Yellow
ssh -i $KEY_FILE -o StrictHostKeyChecking=no ${USER}@${EC2_IP} "tail -30 ~/bb/logs/system.log 2>/dev/null | grep -E 'ERROR|CRITICAL|Exception' || echo 'No errors found'"

Write-Host "`n[5/5] Checking bot uptime..." -ForegroundColor Yellow
ssh -i $KEY_FILE -o StrictHostKeyChecking=no ${USER}@${EC2_IP} "ps -eo pid,etime,cmd | grep 'python.*main.py' | grep -v grep"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "EC2 BOT CHECK COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
