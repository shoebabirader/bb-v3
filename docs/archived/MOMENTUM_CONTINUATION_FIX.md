# Momentum Continuation Filter - Late Entry Fix

## Problem Identified

The bot was entering trades on **exhausted moves** when starting up, causing immediate losses:

1. **Strong move happens** → Price drops/rises significantly with high volume
2. **Bot starts** → Fetches historical data showing the completed move
3. **All indicators align** → ADX high, RVOL high, trend confirmed
4. **Bot enters trade** → But the move is already complete
5. **Price reverses** → Position goes negative immediately

### Example:
- RIVERUSDT drops sharply before bot starts
- Bot detects: BEARISH trend, high ADX, high RVOL, price < VWAP
- Bot enters SHORT at the bottom
- Price bounces back up → SHORT position loses money

## Solution Implemented

Added a **Momentum Continuation Filter** that checks if the move is still active before entering:

### For LONG Signals:
1. ✅ At least 2 of last 3 candles are green (bullish)
2. ✅ Current candle is not strongly bearish
3. ✅ Price not overextended above 20-EMA (< 2% above)
4. ✅ Price making higher lows (uptrend intact)

### For SHORT Signals:
1. ✅ At least 2 of last 3 candles are red (bearish)
2. ✅ Current candle is not strongly bullish
3. ✅ Price not overextended below 20-EMA (< 2% below)
4. ✅ Price making lower highs (downtrend intact)

## How It Works

```python
# Before entering a trade, the bot now checks:
if not self._check_momentum_continuation(candles_15m, "SHORT"):
    logger.info("SHORT signal rejected - momentum exhausted or overextended")
    return None
```

### Rejection Scenarios:

1. **Exhausted Move**: Price already moved too far, now consolidating
2. **Overextended**: Price stretched too far from average (>2%)
3. **Reversal Starting**: Recent candles showing opposite direction
4. **Momentum Fading**: Not enough continuation candles

## Benefits

✅ **Prevents late entries** on exhausted moves
✅ **Reduces immediate losses** from entering at extremes
✅ **Improves entry timing** by waiting for continuation
✅ **Works in all modes** (BACKTEST, PAPER, LIVE)

## Technical Details

### Files Modified:
- `src/strategy.py` - Added momentum continuation check

### New Methods:
- `_check_momentum_continuation()` - Main filter logic
- `_calculate_simple_ema()` - EMA calculation for overextension check

### Integration Points:
- Called in `check_long_entry()` after all other conditions pass
- Called in `check_short_entry()` after all other conditions pass
- Uses stored `_candles_15m` from `update_indicators()`

## Testing

The fix will:
1. Reject signals immediately after bot startup if move is exhausted
2. Only enter when price is still moving in signal direction
3. Log rejection reason: "momentum exhausted or overextended"

## Configuration

No configuration changes needed. The filter uses:
- 20-period EMA for overextension (2% threshold)
- Last 3 candles for momentum check
- Current candle for direction confirmation

## Expected Behavior

### Before Fix:
```
[Bot starts]
[RIVERUSDT] SHORT signal detected at $3.50 (after drop from $3.80)
[Position opened] SHORT @ $3.50
[Price bounces] Current: $3.60 → Loss: -2.86%
```

### After Fix:
```
[Bot starts]
[RIVERUSDT] SHORT signal detected at $3.50
[Momentum check] 2 of last 3 candles are green → REJECTED
[No position opened]
[Waits for fresh signal with continuation]
```

## Monitoring

Watch for log messages:
- `"LONG signal rejected - momentum exhausted or overextended"`
- `"SHORT signal rejected - momentum exhausted or overextended"`

These indicate the filter is working and preventing bad entries.

## Next Steps

1. ✅ Fix is implemented and ready to test
2. Monitor paper trading for rejection rate
3. Adjust thresholds if too strict (currently 2% overextension, 2/3 candles)
4. Consider adding to backtest to measure improvement

---

**Status**: ✅ IMPLEMENTED
**Date**: 2026-02-14
**Impact**: Prevents late entries on exhausted moves
