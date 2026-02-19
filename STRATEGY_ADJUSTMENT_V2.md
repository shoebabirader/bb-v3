# Strategy Adjustment V2 - February 18, 2026

## Problem Analysis

### V1 Results (ADX 25.0, RVOL 1.2):
- Total Trades: 13 in 90 days (TOO FEW)
- Win Rate: 46.15% (GOOD - improved from 11%)
- Total PnL: -$755.76 (STILL LOSING)
- Profit Factor: 0.47 (BAD - need >1.5)
- Average Win: +$111.24
- Average Loss: Larger than wins (causing net loss)

### Root Cause:
1. **Filters too strict** - Missing too many opportunities (only 13 trades)
2. **Exit strategy suboptimal** - Not capturing enough profit when winning
3. **Average losses > average wins** - Need better profit capture

## V2 Adjustments

### 1. Entry Filters - Find Middle Ground

**Changed:**
```json
{
  "adx_threshold": 22.0,  // Was 25.0 → Slightly looser (was 18.0 originally)
  "rvol_threshold": 1.0   // Was 1.2 → Slightly looser (was 0.8 originally)
}
```

**Rationale:**
- ADX 22.0 is between old (18.0) and V1 (25.0) - still requires decent trend
- RVOL 1.0 is between old (0.8) and V1 (1.2) - requires above-average volume
- Should generate 25-35 trades in 90 days (sweet spot)

**Keep unchanged:**
```json
{
  "stop_loss_atr_multiplier": 3.5,           // WORKING WELL
  "trailing_stop_atr_multiplier": 2.5,       // WORKING WELL
  "trailing_stop_activation_atr": 2.0        // WORKING WELL
}
```

### 2. Exit Strategy Improvements

**Changed:**
```json
{
  "exit_partial_1_atr_multiplier": 1.5,      // Take 40% profit at 1.5x ATR
  "exit_partial_1_percentage": 0.4,          // Was 0.33 → Take more profit early
  
  "exit_partial_2_atr_multiplier": 2.5,      // Take 30% profit at 2.5x ATR (was 3.0)
  "exit_partial_2_percentage": 0.3,          // Was 0.33 → Slightly less
  
  "exit_final_atr_multiplier": 4.0,          // Let final 30% run to 4x ATR (was 5.0)
  
  "exit_breakeven_atr_multiplier": 1.5,      // Move to breakeven at 1.5x ATR (was 2.0)
  "exit_tight_stop_atr_multiplier": 1.0,     // Tighter stop after partial exits (was 0.5)
  
  "exit_max_hold_time_hours": 48             // Allow longer holds (was 24)
}
```

**Rationale:**
- **Take profit earlier and more aggressively** - Lock in 40% at 1.5x ATR
- **Reduce risk faster** - Move to breakeven sooner (1.5x ATR instead of 2.0x)
- **More realistic final target** - 4x ATR instead of 5x ATR
- **Allow positions to develop** - 48 hours instead of 24 hours
- **Better risk management** - After taking partials, use 1.0x ATR trailing (not 0.5x which was too tight)

### 3. How Advanced Exits Work

When `enable_advanced_exits: true`, the bot uses a tiered exit strategy:

**Stage 1: Entry → 1.5x ATR profit**
- Initial stop at 3.5x ATR
- No trailing yet (activation at 2.0x ATR)

**Stage 2: 1.5x ATR profit reached**
- Take 40% profit (exit_partial_1)
- Move stop to breakeven
- Continue with 60% position

**Stage 3: 2.5x ATR profit reached**
- Take 30% more profit (exit_partial_2)
- Move stop to 1.0x ATR trailing
- Continue with 30% position

**Stage 4: Final 30%**
- Let it run to 4.0x ATR target
- Or trail at 1.0x ATR distance
- Or exit after 48 hours

## Expected Impact

### Trade Frequency:
- V1: 13 trades in 90 days (too few)
- V2 Target: 25-35 trades in 90 days (better balance)

### Win Rate:
- Should stay around 40-50% (good entry quality maintained)

### Profit Factor:
- V1: 0.47 (losing)
- V2 Target: >1.5 (profitable)
- Improved by taking profits earlier and more aggressively

### Average Win vs Loss:
- V1: Avg win $111, but losses bigger
- V2: Should capture more profit per win with partial exits
- Breakeven move protects against losses

## API Rate Limit Errors

The errors you're seeing are **temporary and expected**:

```
APIError(code=-1003): Too many requests; current limit of IP(13.233.2.23) is 2400 requests per minute
```

**Why this happens:**
- Bot is fetching historical data for 5 symbols × 4 timeframes = 20 API calls
- During startup, it needs to load 7 days of data for each
- Once cached, it only uses WebSocket (no more API calls)

**What to do:**
- **Nothing** - Let it run for 5-10 minutes
- Bot will cache all data and errors will stop
- After that, it uses WebSocket for real-time updates (no API polling)

**Monitoring:**
- Watch logs - errors should decrease over time
- After 10 minutes, should see "found in symbol_buffers" (using cache)
- No more rate limit errors after initial load

## Deployment

**Files to update on EC2:**
1. `config/config.json` - New thresholds and exit parameters

**Command:**
```powershell
.\deploy_strategy_improvements.ps1
```

Or manually:
```bash
ssh -i bb.pem ubuntu@13.233.2.23
cd trading-bot
# Upload new config.json
pkill -f main.py
nohup python3 main.py > bot.log 2>&1 &
```

## Testing Plan

### Phase 1 (Days 1-3):
- Monitor trade frequency (should see 1-2 trades per day)
- Verify partial exits are working
- Check that stops move to breakeven at 1.5x ATR

### Phase 2 (Days 4-7):
- Target: 10-15 trades total
- Target: Win rate 40-50%
- Target: Positive PnL
- Target: Profit factor >1.2

### Phase 3 (Day 8+):
- If metrics good, continue monitoring
- If profit factor >1.5 and 20+ trades, consider LIVE

## Success Criteria

**Do NOT go LIVE until:**
- ✅ Win rate > 40%
- ✅ Profit factor > 1.5
- ✅ At least 20 trades in PAPER mode
- ✅ Positive total PnL over 7+ days
- ✅ Partial exits working correctly
- ✅ Average win > average loss

## Rollback Plan

If performance worse than V1:
```bash
ssh -i bb.pem ubuntu@13.233.2.23
cd trading-bot
git checkout config/config.json
pkill -f main.py
nohup python3 main.py > bot.log 2>&1 &
```

## Key Differences from V1

| Parameter | V1 | V2 | Reason |
|-----------|----|----|--------|
| ADX Threshold | 25.0 | 22.0 | More trades |
| RVOL Threshold | 1.2 | 1.0 | More trades |
| Partial 1 % | 33% | 40% | Lock profit faster |
| Partial 2 ATR | 3.0x | 2.5x | More realistic |
| Final Target | 5.0x | 4.0x | More realistic |
| Breakeven | 2.0x | 1.5x | Protect faster |
| Max Hold | 24h | 48h | Let winners run |

## Notes

- The wider stops (3.5x ATR) are working well - keep them
- The delayed trailing (2.0x ATR activation) is working well - keep it
- The candle-close confirmation is working well - keep it
- Focus is now on: more trades + better profit capture
- Partial exits should significantly improve profit factor
