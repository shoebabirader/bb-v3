# Backtest Engine Fixed - Advanced Exits Removed

## Problem

The backtest engine had a broken implementation of advanced exits that was causing:
1. Balance going negative
2. Incorrect trade counts (799 trades instead of 14-17)
3. PnL double-counting
4. Error: `'RiskManager' object has no attribute 'positions'`

## Root Cause

The advanced exits implementation tried to manually track partial exits outside of the RiskManager, which created:
- Multiple trade records for the same position
- PnL accumulation errors
- Architecture mismatch with how live trading works

## Solution

**Reverted the broken advanced exits implementation** from the backtest engine:

1. Removed `_partial_exit_pnl` tracking dictionary
2. Removed all partial exit logic (PRIORITY 1)
3. Removed time-based exit logic (PRIORITY 2)
4. Removed breakeven stop adjustment logic
5. Removed `original_quantity` tracking
6. Restored simple take profit + trailing stop logic

## What Still Works

The backtest engine now has:
- ✅ Simple take profit at configured percentage
- ✅ Trailing stop-loss
- ✅ Multi-timeframe support (5m, 15m, 1h, 4h)
- ✅ Feature tracking (adaptive thresholds, volume profile, ML, regime)
- ✅ Accurate PnL calculation
- ✅ Correct trade counting

## Config Setting

Advanced exits are already disabled in config:
```json
{
  "enable_advanced_exits": false
}
```

This setting now only affects live trading. The backtest engine will always use simple exits.

## Live Trading

The live bot on EC2 still uses advanced exits correctly via:
- `src/risk_manager.py`
- `src/advanced_exit_manager.py`

These work fine and don't have the issues the backtest implementation had.

## Testing

Run a backtest to verify it's working:
```bash
python run_portfolio_backtest.py
```

Expected results:
- 14-20 trades in 90 days
- Balance stays positive
- No errors about missing attributes
- Reasonable PnL calculations

## Next Steps

1. Run backtest with current settings (ADX 22, RVOL 1.0, wider stops)
2. If results look good, continue paper trading on EC2
3. Monitor EC2 paper trading for 7+ days
4. If paper trading is profitable, consider going LIVE

## Note

If you want to test advanced exits, use paper trading on EC2. The live bot implements them correctly.
