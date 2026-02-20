# Diagnose what went wrong with deployment
$EC2_IP = "13.233.2.23"
$PEM_FILE = "bb.pem"
$EC2_USER = "ubuntu"

Write-Host "Diagnosing EC2 deployment issue..." -ForegroundColor Cyan
Write-Host ""

Write-Host "[1] Check home directory:" -ForegroundColor Yellow
ssh -i $PEM_FILE "${EC2_USER}@${EC2_IP}" "ls -la /home/ubuntu/"

Write-Host ""
Write-Host "[2] Check if zip file is still there:" -ForegroundColor Yellow
ssh -i $PEM_FILE "${EC2_USER}@${EC2_IP}" "ls -la /home/ubuntu/*.zip 2>&1 || echo 'No zip files found'"

Write-Host ""
Write-Host "[3] Check disk space:" -ForegroundColor Yellow
ssh -i $PEM_FILE "${EC2_USER}@${EC2_IP}" "df -h"

Write-Host ""
Write-Host "[4] Check if unzip is installed:" -ForegroundColor Yellow
ssh -i $PEM_FILE "${EC2_USER}@${EC2_IP}" "which unzip && unzip -v | head -5"
