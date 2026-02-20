# Diagnose EC2 Bot Failure
# This script connects to EC2 and retrieves diagnostic information

$EC2_IP = "13.233.2.23"
$KEY_FILE = "bb.pem"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "EC2 Bot Diagnostic Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check 1: Service Status
Write-Host "[1] Checking service status..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl status trading-bot --no-pager -l'
Write-Host ""

# Check 2: Error Logs
Write-Host "[2] Checking error logs..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'tail -50 /home/ubuntu/trading-bot/logs/bot_error.log 2>/dev/null || echo "No error log found"'
Write-Host ""

# Check 3: Standard Output Logs
Write-Host "[3] Checking standard output logs..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'tail -50 /home/ubuntu/trading-bot/logs/bot.log 2>/dev/null || echo "No bot log found"'
Write-Host ""

# Check 4: Config File Exists
Write-Host "[4] Checking config file..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'ls -la /home/ubuntu/trading-bot/config/config.json 2>/dev/null || echo "Config file not found!"'
Write-Host ""

# Check 5: Python Environment
Write-Host "[5] Checking Python environment..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'source /home/ubuntu/trading-bot/venv/bin/activate && python --version && pip list | grep -E "(ccxt|pandas|numpy|ta-lib)"'
Write-Host ""

# Check 6: Disk Space
Write-Host "[6] Checking disk space..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'df -h /'
Write-Host ""

# Check 7: Memory
Write-Host "[7] Checking memory..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'free -h'
Write-Host ""

# Check 8: Try running bot manually
Write-Host "[8] Attempting manual bot start (will timeout after 10 seconds)..." -ForegroundColor Yellow
ssh -i $KEY_FILE ubuntu@$EC2_IP 'cd /home/ubuntu/trading-bot && timeout 10 venv/bin/python main.py 2>&1 || echo "Manual start test completed"'
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Diagnostic Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
