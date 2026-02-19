# Position Shutdown Bug Fix

## Problem Identified

The bot was failing to close positions during shutdown, causing positions to be "orphaned" when the bot restarted. This is a critical bug that would leave real positions open on Binance in LIVE mode.

### Root Cause

In `src/trading_bot.py` line 1313, the shutdown handler was calling:
```python
trade = self.risk_manager.close_position(pos, pos_price, "SHUTDOWN")
```

However, `risk_manager.py` only accepts these valid exit reasons:
- STOP_LOSS
- TRAILING_STOP
- TAKE_PROFIT
- SIGNAL_EXIT
- PANIC
- TIME_BASED
- REGIME_CHANGE

The "SHUTDOWN" reason was invalid, causing a ValueError and preventing positions from closing.

### Evidence from Logs

```
2026-02-18 00:08:36,574 - src.trading_bot - ERROR - Error closing position RIVERUSDT: Invalid exit reason: SHUTDOWN. Must be one of: STOP_LOSS, TRAILING_STOP, TAKE_PROFIT, SIGNAL_EXIT, PANIC, TIME_BASED, REGIME_CHANGE
```

This happened multiple times:
- 00:08:36 UTC: Failed to close RIVERUSDT position
- 00:58:23 UTC: Failed to close RIVERUSDT position again

When you restarted the bot at 01:01:44 UTC, the positions were lost from memory but never properly closed.

## Solution

Changed line 1313 in `src/trading_bot.py` from:
```python
trade = self.risk_manager.close_position(pos, pos_price, "SHUTDOWN")
```

To:
```python
trade = self.risk_manager.close_position(pos, pos_price, "PANIC")
```

The "PANIC" exit reason is appropriate for emergency/shutdown scenarios and is already a valid reason in the risk manager.

## Impact

### Before Fix
- Positions could not be closed during bot shutdown
- Positions were "orphaned" when bot restarted
- In PAPER mode: harmless but confusing
- In LIVE mode: **CRITICAL** - would leave real positions open on Binance

### After Fix
- Positions are properly closed during shutdown
- Trade records are created with "PANIC" exit reason
- No orphaned positions after restart
- Safe for LIVE mode deployment

## Deployment to EC2

To deploy this fix to your EC2 instance:

### Option 1: Quick Deploy (Recommended)
```powershell
# From your local machine
scp -i bb.pem src/trading_bot.py ubuntu@13.233.2.23:/home/ubuntu/trading-bot/src/

# Restart the bot
ssh -i bb.pem ubuntu@13.233.2.23 'sudo systemctl restart trading-bot'

# Check status
ssh -i bb.pem ubuntu@13.233.2.23 'sudo systemctl status trading-bot'
```

### Option 2: Full Redeploy
```powershell
.\deploy_to_ec2.sh
```

### Verify Fix
After deployment, check the logs:
```powershell
ssh -i bb.pem ubuntu@13.233.2.23 'tail -f /home/ubuntu/trading-bot/logs/bot.log'
```

Then restart the bot (Ctrl+C or `sudo systemctl restart trading-bot`) and verify:
1. No "Invalid exit reason: SHUTDOWN" errors
2. Positions close successfully with "PANIC" reason
3. Trade records are created in the log

## Additional Recommendations

### 1. Position Persistence
Currently, positions are stored in memory only. Consider implementing position persistence:
- Save positions to a file/database
- Restore positions on bot restart
- Prevents "forgetting" positions across restarts

### 2. Remote Panic Close
Since ESC key doesn't work on headless EC2, consider adding:
- API endpoint for panic close
- Signal file monitoring (e.g., create `/tmp/panic_close` to trigger)
- WhatsApp/Telegram command integration

### 3. Position Reconciliation
Add a startup check that:
- Queries Binance for actual open positions
- Compares with bot's internal state
- Alerts if discrepancies found

## Testing

Before deploying to LIVE mode:
1. Test in PAPER mode on EC2
2. Open a position
3. Restart the bot (Ctrl+C or systemctl restart)
4. Verify position closes properly
5. Check logs for "PANIC" exit reason (not "SHUTDOWN" error)

## Status

- [x] Bug identified
- [x] Fix implemented
- [x] Deployed to EC2 (2026-02-18 01:11 UTC)
- [x] Bot restarted successfully
- [ ] Tested in PAPER mode (restart bot to verify)
- [ ] Ready for LIVE mode

## Deployment Log

```
2026-02-18 01:11 UTC - Deployed fix to EC2
- Uploaded src/trading_bot.py
- Restarted trading-bot service
- Bot status: active (running)
- PID: 50611
```

Previous errors in logs (before fix):
- 00:08:36 UTC: RIVERUSDT position failed to close
- 00:58:23 UTC: RIVERUSDT position failed to close again
- 01:09:50 UTC: TRXUSDT position failed to close

Next restart will test if the fix works properly.
