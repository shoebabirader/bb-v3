# Deploy Streamlit Dashboard to EC2

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "DEPLOYING STREAMLIT DASHBOARD TO EC2" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

Write-Host "`n📦 Step 1: Uploading Streamlit files..." -ForegroundColor Yellow

# Upload streamlit_app.py
Write-Host "  - Uploading streamlit_app.py..." -ForegroundColor Gray
scp -i bb.pem streamlit_app.py ubuntu@13.233.2.23:~/trading-bot/

# Upload all Streamlit source files
Write-Host "  - Uploading Streamlit source files..." -ForegroundColor Gray
scp -i bb.pem src/streamlit_*.py ubuntu@13.233.2.23:~/trading-bot/src/

# Upload requirements
Write-Host "  - Uploading requirements..." -ForegroundColor Gray
scp -i bb.pem requirements_complete.txt ubuntu@13.233.2.23:~/trading-bot/requirements_ui.txt

Write-Host "`n✅ Files uploaded" -ForegroundColor Green

Write-Host "`n📦 Step 2: Installing Streamlit dependencies..." -ForegroundColor Yellow
ssh -i bb.pem ubuntu@13.233.2.23 "cd ~/trading-bot && source venv/bin/activate && pip install streamlit streamlit-autorefresh plotly"

Write-Host "`n✅ Dependencies installed" -ForegroundColor Green

Write-Host "`n🚀 Step 3: Starting Streamlit dashboard..." -ForegroundColor Yellow
ssh -i bb.pem ubuntu@13.233.2.23 "cd ~/trading-bot && nohup venv/bin/streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &"

Start-Sleep -Seconds 5

Write-Host "`n📊 Step 4: Checking if Streamlit is running..." -ForegroundColor Yellow
$streamlit_pid = ssh -i bb.pem ubuntu@13.233.2.23 "pgrep -f streamlit"

if ($streamlit_pid) {
    Write-Host "✅ Streamlit is RUNNING! (PID: $streamlit_pid)" -ForegroundColor Green
} else {
    Write-Host "⚠️  Streamlit is not running" -ForegroundColor Yellow
    Write-Host "`nChecking logs..." -ForegroundColor Cyan
    ssh -i bb.pem ubuntu@13.233.2.23 "tail -20 ~/trading-bot/streamlit.log"
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "DEPLOYMENT COMPLETE" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

Write-Host "`n🌐 Dashboard URL:" -ForegroundColor Green
Write-Host "  http://13.233.2.23:8501" -ForegroundColor White

Write-Host "`n⚠️  IMPORTANT:" -ForegroundColor Yellow
Write-Host "  Make sure EC2 Security Group allows inbound traffic on port 8501" -ForegroundColor Yellow
Write-Host "  - Go to AWS Console → EC2 → Security Groups" -ForegroundColor Gray
Write-Host "  - Add inbound rule: Custom TCP, Port 8501, Source: Your IP or 0.0.0.0/0" -ForegroundColor Gray

Write-Host "`n📋 Useful Commands:" -ForegroundColor Cyan
Write-Host "  Check Streamlit status:" -ForegroundColor White
Write-Host "    ssh -i bb.pem ubuntu@13.233.2.23 `"pgrep -f streamlit`"" -ForegroundColor Gray
Write-Host "`n  View Streamlit logs:" -ForegroundColor White
Write-Host "    ssh -i bb.pem ubuntu@13.233.2.23 `"tail -50 ~/trading-bot/streamlit.log`"" -ForegroundColor Gray
Write-Host "`n  Restart Streamlit:" -ForegroundColor White
Write-Host "    ssh -i bb.pem ubuntu@13.233.2.23 `"pkill -f streamlit && cd ~/trading-bot && nohup venv/bin/streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &`"" -ForegroundColor Gray

Write-Host "`n================================================================================" -ForegroundColor Cyan
