# Clean up EC2 disk space

Write-Host "`n================================================================================" -ForegroundColor Yellow
Write-Host "CLEANING UP EC2 DISK SPACE" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Yellow

Write-Host "`n📊 Current disk usage:" -ForegroundColor Cyan
ssh -i bb.pem ubuntu@13.233.2.23 "df -h /"

Write-Host "`n🧹 Step 1: Backing up and truncating bot.log..." -ForegroundColor Yellow
ssh -i bb.pem ubuntu@13.233.2.23 "cd ~/trading-bot && tail -1000 bot.log > bot.log.recent && > bot.log && cat bot.log.recent > bot.log && rm bot.log.recent"

Write-Host "`n🧹 Step 2: Cleaning pip cache..." -ForegroundColor Yellow
ssh -i bb.pem ubuntu@13.233.2.23 "rm -rf ~/.cache/pip/*"

Write-Host "`n🧹 Step 3: Cleaning apt cache..." -ForegroundColor Yellow
ssh -i bb.pem ubuntu@13.233.2.23 "sudo apt-get clean"

Write-Host "`n🧹 Step 4: Removing old logs..." -ForegroundColor Yellow
ssh -i bb.pem ubuntu@13.233.2.23 "cd ~/trading-bot/logs && find . -name '*.log.*' -mtime +7 -delete"

Write-Host "`n📊 New disk usage:" -ForegroundColor Cyan
ssh -i bb.pem ubuntu@13.233.2.23 "df -h /"

Write-Host "`n✅ Cleanup complete!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Yellow
