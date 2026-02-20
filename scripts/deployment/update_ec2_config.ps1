# Update EC2 Config with New API Keys
# Use this if you need to update API keys or other config on EC2

$EC2_IP = "13.233.2.23"
$KEY_FILE = "bb.pem"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Update EC2 Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Current EC2 IP: $EC2_IP" -ForegroundColor Yellow
Write-Host ""
Write-Host "To fix API authentication, you need to:" -ForegroundColor Yellow
Write-Host "1. Go to Binance API Management" -ForegroundColor White
Write-Host "2. Edit your API key settings" -ForegroundColor White
Write-Host "3. Add $EC2_IP to the IP whitelist" -ForegroundColor White
Write-Host ""
Write-Host "OR" -ForegroundColor Yellow
Write-Host ""
Write-Host "Upload a new config.json with unrestricted API keys" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Do you want to upload a new config.json? (y/n)"

if ($choice -eq 'y' -or $choice -eq 'Y') {
    Write-Host ""
    Write-Host "Stopping bot..." -ForegroundColor Yellow
    ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl stop trading-bot'
    
    Write-Host "Uploading config.json..." -ForegroundColor Yellow
    scp -i $KEY_FILE config/config.json ubuntu@${EC2_IP}:/home/ubuntu/trading-bot/config/config.json
    
    Write-Host "Restarting bot..." -ForegroundColor Yellow
    ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl restart trading-bot'
    Start-Sleep -Seconds 5
    
    Write-Host ""
    Write-Host "Bot Status:" -ForegroundColor Yellow
    ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl status trading-bot --no-pager'
    
    Write-Host ""
    Write-Host "Recent Logs:" -ForegroundColor Yellow
    ssh -i $KEY_FILE ubuntu@$EC2_IP 'tail -30 /home/ubuntu/trading-bot/logs/bot.log'
} else {
    Write-Host ""
    Write-Host "No changes made. Remember to whitelist $EC2_IP in Binance!" -ForegroundColor Yellow
}
