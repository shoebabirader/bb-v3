#!/bin/bash
# Automated deployment script for AWS EC2 Ubuntu
# Run this script on your EC2 instance after connecting via SSH

set -e  # Exit on error

echo "=========================================="
echo "Trading Bot EC2 Deployment Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Please do not run as root. Run as ubuntu user."
    exit 1
fi

# Step 1: Update system
print_status "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Step 2: Install Python 3.11
print_status "Installing Python 3.11..."
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip git build-essential wget

# Step 3: Install TA-Lib
print_status "Installing TA-Lib..."
cd /tmp
if [ ! -f "ta-lib-0.4.0-src.tar.gz" ]; then
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
fi
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
sudo ldconfig
cd ~

# Step 4: Setup bot directory
print_status "Setting up bot directory..."
BOT_DIR="$HOME/trading-bot"

if [ ! -d "$BOT_DIR" ]; then
    print_warning "Bot directory not found. Please upload your bot code to $BOT_DIR"
    print_warning "You can use: scp -r your-bot-folder ubuntu@YOUR_IP:~/trading-bot"
    exit 1
fi

cd "$BOT_DIR"

# Step 5: Create virtual environment
print_status "Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Step 6: Install Python dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
if [ -f "requirements_complete.txt" ]; then
    pip install -r requirements_complete.txt
elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    print_error "No requirements file found!"
    exit 1
fi

# Step 7: Create logs directory
print_status "Creating logs directory..."
mkdir -p logs

# Step 8: Create systemd service
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/trading-bot.service > /dev/null <<EOF
[Unit]
Description=Binance Futures Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin"
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:$BOT_DIR/logs/bot.log
StandardError=append:$BOT_DIR/logs/bot_error.log

[Install]
WantedBy=multi-user.target
EOF

# Step 9: Enable and start service
print_status "Enabling trading bot service..."
sudo systemctl daemon-reload
sudo systemctl enable trading-bot

# Step 10: Setup firewall
print_status "Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw --force enable

# Step 11: Add swap space (for t3.micro)
print_status "Adding swap space..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    print_status "Swap space added (2GB)"
else
    print_status "Swap space already exists"
fi

# Step 12: Create helper scripts
print_status "Creating helper scripts..."

# Start bot script
cat > "$BOT_DIR/start_bot.sh" <<'EOF'
#!/bin/bash
sudo systemctl start trading-bot
echo "Bot started. Check status with: sudo systemctl status trading-bot"
EOF
chmod +x "$BOT_DIR/start_bot.sh"

# Stop bot script
cat > "$BOT_DIR/stop_bot.sh" <<'EOF'
#!/bin/bash
sudo systemctl stop trading-bot
echo "Bot stopped."
EOF
chmod +x "$BOT_DIR/stop_bot.sh"

# Restart bot script
cat > "$BOT_DIR/restart_bot.sh" <<'EOF'
#!/bin/bash
sudo systemctl restart trading-bot
echo "Bot restarted. Check status with: sudo systemctl status trading-bot"
EOF
chmod +x "$BOT_DIR/restart_bot.sh"

# View logs script
cat > "$BOT_DIR/view_logs.sh" <<'EOF'
#!/bin/bash
tail -f logs/bot.log
EOF
chmod +x "$BOT_DIR/view_logs.sh"

# Check status script
cat > "$BOT_DIR/check_status.sh" <<'EOF'
#!/bin/bash
echo "=== Bot Service Status ==="
sudo systemctl status trading-bot --no-pager
echo ""
echo "=== Recent Logs (last 20 lines) ==="
tail -20 logs/bot.log
echo ""
echo "=== System Resources ==="
free -h
df -h /
EOF
chmod +x "$BOT_DIR/check_status.sh"

print_status "Helper scripts created in $BOT_DIR"

# Final instructions
echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit config: nano $BOT_DIR/config/config.json"
echo "2. Verify API keys and settings"
echo "3. Start bot: ./start_bot.sh"
echo "4. Check status: ./check_status.sh"
echo "5. View logs: ./view_logs.sh"
echo ""
echo "Useful commands:"
echo "  Start:   sudo systemctl start trading-bot"
echo "  Stop:    sudo systemctl stop trading-bot"
echo "  Restart: sudo systemctl restart trading-bot"
echo "  Status:  sudo systemctl status trading-bot"
echo "  Logs:    tail -f logs/bot.log"
echo ""
print_warning "IMPORTANT: Test with PAPER mode first before going LIVE!"
echo ""
