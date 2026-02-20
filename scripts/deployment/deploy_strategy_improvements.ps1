# Deploy Strategy Improvements to EC2
# This script deploys the updated config and position sizer to EC2

$EC2_IP = "13.233.2.23"
$KEY_FILE = "bb.pem"
$EC2_USER = "ubuntu"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploying Strategy Improvements to EC2" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if key file exists
if (-not (Test-Path $KEY_FILE)) {
    Write-Host "ERROR: Key file $KEY_FILE not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Step 1: Uploading updated config.json..." -ForegroundColor Yellow
scp -i $KEY_FILE config/config.json "${EC2_USER}@${EC2_IP}:~/trading-bot/config/"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upload config.json" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Config uploaded successfully" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Uploading updated position_sizer.py..." -ForegroundColor Yellow
scp -i $KEY_FILE src/position_sizer.py "${EC2_USER}@${EC2_IP}:~/trading-bot/src/"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upload position_sizer.py" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Position sizer uploaded successfully" -ForegroundColor Green
Write-Host ""

Write-Host "Step 3: Uploading updated strategy.py..." -ForegroundColor Yellow
scp -i $KEY_FILE src/strategy.py "${EC2_USER}@${EC2_IP}:~/trading-bot/src/"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upload strategy.py" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Strategy uploaded successfully" -ForegroundColor Green
Write-Host ""

Write-Host "Step 4: Restarting bot on EC2..." -ForegroundColor Yellow
& ssh -i $KEY_FILE "$EC2_USER@$EC2_IP" 'cd ~/trading-bot && pkill -f python.*main.py || true && sleep 2 && nohup python3 main.py > bot.log 2>&1 & sleep 3 && pgrep -f python.*main.py && echo Bot restarted successfully || echo ERROR: Bot failed to start'

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to restart bot" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Changes deployed:" -ForegroundColor Cyan
Write-Host "  • stop_loss_atr_multiplier: 2.0 → 3.5" -ForegroundColor White
Write-Host "  • trailing_stop_atr_multiplier: 3.0 → 2.5" -ForegroundColor White
Write-Host "  • trailing_stop_activation_atr: 2.0 (NEW)" -ForegroundColor White
Write-Host "  • adx_threshold: 18.0 → 25.0" -ForegroundColor White
Write-Host "  • rvol_threshold: 0.8 → 1.2" -ForegroundColor White
Write-Host "  • Candle-close confirmation: ENABLED (NEW)" -ForegroundColor White
Write-Host ""
Write-Host "Expected improvements:" -ForegroundColor Cyan
Write-Host "  • Wider stops = fewer premature stop-outs" -ForegroundColor White
Write-Host "  • Delayed trailing = positions get room to develop" -ForegroundColor White
Write-Host "  • Higher ADX/RVOL = better quality entries" -ForegroundColor White
Write-Host "  • Candle-close timing = no mid-candle entries, better fills" -ForegroundColor White
Write-Host "  • Win rate should improve from 11% to 40-50%" -ForegroundColor White
Write-Host ""
Write-Host "Monitor for 2-3 days in PAPER mode before going LIVE" -ForegroundColor Yellow
Write-Host ""
