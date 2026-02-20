# Quick script to check EC2 bot status
$EC2_IP = "13.233.2.23"
$PEM_FILE = "bb.pem"
$EC2_USER = "ubuntu"

Write-Host "Checking bot status on EC2..." -ForegroundColor Cyan
Write-Host ""

Write-Host "[1] Systemd Service Status:" -ForegroundColor Yellow
ssh -i $PEM_FILE "${EC2_USER}@${EC2_IP}" "sudo systemctl status trading-bot --no-pager -l"

Write-Host ""
Write-Host "[2] Check if logs directory exists:" -ForegroundColor Yellow
ssh -i $PEM_FILE "${EC2_USER}@${EC2_IP}" "ls -la /home/ubuntu/trading-bot/logs/ 2>&1 || echo 'Logs directory does not exist'"

Write-Host ""
Write-Host "[3] Check bot directory structure:" -ForegroundColor Yellow
ssh -i $PEM_FILE "${EC2_USER}@${EC2_IP}" "ls -la /home/ubuntu/trading-bot/"

Write-Host ""
Write-Host "[4] Check if main.py exists:" -ForegroundColor Yellow
ssh -i $PEM_FILE "${EC2_USER}@${EC2_IP}" "ls -la /home/ubuntu/trading-bot/main.py"

Write-Host ""
Write-Host "[5] Check systemd service file:" -ForegroundColor Yellow
ssh -i $PEM_FILE "${EC2_USER}@${EC2_IP}" "cat /etc/systemd/system/trading-bot.service"

Write-Host ""
Write-Host "[6] Check journalctl logs (last 50 lines):" -ForegroundColor Yellow
ssh -i $PEM_FILE "${EC2_USER}@${EC2_IP}" "sudo journalctl -u trading-bot -n 50 --no-pager"
