# EC2 Headless Mode Fix

## Problem
The trading bot was failing to start on EC2 with the error:
```
ImportError: this platform is not supported: ('failed to acquire X connection: Bad display name ""', DisplayNameError(''))
```

## Root Cause
The bot was importing `pynput` library for keyboard input (ESC key for panic close), which requires an X server (graphical display). EC2 instances run headless (no display), causing the import to fail immediately.

## Solution
Made the keyboard listener optional:

1. **Conditional Import**: Wrapped `pynput` import in try/except block
2. **Graceful Degradation**: Bot runs without keyboard listener on headless servers
3. **Feature Detection**: Added `KEYBOARD_AVAILABLE` flag to detect display support
4. **Safe Initialization**: Keyboard listener only starts if display is available

## Changes Made

### src/trading_bot.py
- Changed `pynput` import to be optional with try/except
- Added `KEYBOARD_AVAILABLE` flag for feature detection
- Modified `_start_keyboard_listener()` to gracefully skip on headless systems
- Added informative logging for headless mode

## Deployment

### Quick Fix (Recommended)
```powershell
.\fix_ec2_headless.ps1
```

This script will:
1. Stop the bot service
2. Upload the fixed `trading_bot.py`
3. Restart the bot
4. Show status and logs

### Manual Deployment
```powershell
# Stop bot
ssh -i bb.pem ubuntu@13.233.2.23 'sudo systemctl stop trading-bot'

# Upload fix
scp -i bb.pem src/trading_bot.py ubuntu@13.233.2.23:/home/ubuntu/trading-bot/src/trading_bot.py

# Restart bot
ssh -i bb.pem ubuntu@13.233.2.23 'sudo systemctl restart trading-bot'

# Check status
ssh -i bb.pem ubuntu@13.233.2.23 'sudo systemctl status trading-bot'

# View logs
ssh -i bb.pem ubuntu@13.233.2.23 'tail -f /home/ubuntu/trading-bot/logs/bot.log'
```

## Verification

After deployment, verify the bot is running:

```powershell
# Check service status
ssh -i bb.pem ubuntu@13.233.2.23 'sudo systemctl status trading-bot'

# Should show: Active: active (running)
```

Check logs for confirmation:
```powershell
ssh -i bb.pem ubuntu@13.233.2.23 'tail -50 /home/ubuntu/trading-bot/logs/bot.log'
```

You should see:
```
Keyboard listener not available (headless mode - use API/signals for panic close)
TradingBot initialized in PAPER mode
```

## Alternative Panic Close Methods

Since keyboard input is not available on EC2, use these alternatives:

### 1. SSH Command
```bash
ssh -i bb.pem ubuntu@13.233.2.23 'sudo systemctl stop trading-bot'
```

### 2. API Endpoint (if implemented)
```bash
curl -X POST http://13.233.2.23:8000/api/panic-close
```

### 3. Signal Handler
```bash
ssh -i bb.pem ubuntu@13.233.2.23 'sudo pkill -SIGTERM -f "python.*main.py"'
```

## Notes

- The bot will function identically on EC2, just without keyboard input
- All trading logic, risk management, and execution remain unchanged
- This fix also allows the bot to run in Docker containers and other headless environments
- `pynput` is still available on Windows/Mac for local development with keyboard support

## Testing

Local testing (Windows with display):
```powershell
python main.py
# ESC key should still work for panic close
```

EC2 testing (headless):
```bash
python main.py
# Should start without keyboard listener, no errors
```
