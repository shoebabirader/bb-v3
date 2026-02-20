# Automated AWS EC2 Deployment Script for Trading Bot
# Usage: .\deploy_to_aws.ps1

$EC2_IP = "13.233.2.23"
$PEM_FILE = "bb.pem"
$EC2_USER = "ubuntu"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Trading Bot AWS EC2 Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if PEM file exists
if (-not (Test-Path $PEM_FILE)) {
    Write-Host "[ERROR] PEM file not found: $PEM_FILE" -ForegroundColor Red
    Write-Host "Please ensure bb.pem is in the current directory" -ForegroundColor Yellow
    exit 1
}

# Fix PEM file permissions (SSH requires strict permissions)
Write-Host "[0/6] Fixing PEM file permissions..." -ForegroundColor Green
try {
    # Remove inheritance
    icacls $PEM_FILE /inheritance:r | Out-Null
    # Grant read permission only to current user
    icacls $PEM_FILE /grant:r "$($env:USERNAME):(R)" | Out-Null
    Write-Host "  PEM permissions set correctly" -ForegroundColor Gray
} catch {
    Write-Host "[WARNING] Could not set PEM permissions automatically" -ForegroundColor Yellow
    Write-Host "  If SSH fails, run these commands manually:" -ForegroundColor Yellow
    Write-Host "    icacls $PEM_FILE /inheritance:r" -ForegroundColor Gray
    Write-Host "    icacls $PEM_FILE /grant:r `"`$(`$env:USERNAME):(R)`"" -ForegroundColor Gray
}

Write-Host "[1/6] Creating deployment package..." -ForegroundColor Green

# Create temporary directory for deployment
$tempDir = "temp_deploy"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Copy essential files only (exclude logs, cache, etc.)
$filesToCopy = @(
    "src",
    "config",
    "main.py",
    "requirements.txt",
    "deploy_to_ec2.sh",
    "streamlit_app.py",
    "start_dashboard.py"
)

foreach ($item in $filesToCopy) {
    if (Test-Path $item) {
        Copy-Item -Path $item -Destination $tempDir -Recurse -Force
        Write-Host "  Copied: $item" -ForegroundColor Gray
    }
}

# Create zip file
Write-Host "[2/6] Compressing files..." -ForegroundColor Green
$zipFile = "trading-bot-deploy.zip"
if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
}

Compress-Archive -Path "$tempDir\*" -DestinationPath $zipFile -Force
Write-Host "  Created: $zipFile" -ForegroundColor Gray

# Clean up temp directory
Remove-Item -Recurse -Force $tempDir

Write-Host "[3/6] Uploading to EC2..." -ForegroundColor Green
Write-Host "  Target: $EC2_USER@$EC2_IP" -ForegroundColor Gray

# Upload zip file
& scp -i $PEM_FILE -o StrictHostKeyChecking=no $zipFile "${EC2_USER}@${EC2_IP}:/home/ubuntu/"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to upload files to EC2" -ForegroundColor Red
    exit 1
}

Write-Host "  Upload complete!" -ForegroundColor Gray

Write-Host "[4/6] Extracting files on EC2..." -ForegroundColor Green

# SSH and extract (install unzip first if needed)
$extractCmd = @"
cd /home/ubuntu && \
sudo apt-get update -qq && \
sudo apt-get install -y -qq unzip && \
rm -rf trading-bot && \
unzip -q trading-bot-deploy.zip -d trading-bot && \
rm trading-bot-deploy.zip && \
echo 'Files extracted successfully'
"@

& ssh -i $PEM_FILE -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" $extractCmd

Write-Host "[5/6] Running deployment script on EC2..." -ForegroundColor Green

# Run deployment script
$deployCmd = @"
cd /home/ubuntu/trading-bot && \
chmod +x deploy_to_ec2.sh && \
./deploy_to_ec2.sh
"@

& ssh -i $PEM_FILE -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" $deployCmd

Write-Host "[6/6] Starting trading bot service..." -ForegroundColor Green

# Start the bot
$startCmd = @"
sudo systemctl daemon-reload && \
sudo systemctl enable trading-bot && \
sudo systemctl start trading-bot && \
sleep 2 && \
sudo systemctl status trading-bot --no-pager
"@

& ssh -i $PEM_FILE -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" $startCmd

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Bot Status:" -ForegroundColor Yellow
Write-Host "  SSH: ssh -i $PEM_FILE $EC2_USER@$EC2_IP" -ForegroundColor Gray
Write-Host "  Logs: ssh -i $PEM_FILE $EC2_USER@$EC2_IP 'tail -f /home/ubuntu/trading-bot/logs/bot.log'" -ForegroundColor Gray
Write-Host "  Stop: ssh -i $PEM_FILE $EC2_USER@$EC2_IP 'sudo systemctl stop trading-bot'" -ForegroundColor Gray
Write-Host "  Restart: ssh -i $PEM_FILE $EC2_USER@$EC2_IP 'sudo systemctl restart trading-bot'" -ForegroundColor Gray
Write-Host ""

# Clean up local zip
Remove-Item $zipFile -Force

Write-Host "Press any key to view live logs (Ctrl+C to exit)..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Show live logs
& ssh -i $PEM_FILE "${EC2_USER}@${EC2_IP}" "tail -f /home/ubuntu/trading-bot/logs/bot.log"
