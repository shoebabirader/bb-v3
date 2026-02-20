# Scaled Take Profit Feature - Spec Complete ✅

**Date:** 2026-02-20  
**Status:** Ready for Implementation

---

## Overview

The Scaled Take Profit feature spec is now complete with requirements, design, and implementation tasks. This feature will progressively lock in profits at multiple levels while letting winning positions run.

## Problem Being Solved

**Current Issue:**
- Bot enters trade, goes +6% in profit
- Doesn't reach +8% take profit target
- Momentum reverses
- Hits stop loss → Loss instead of profit

**Solution:**
- TP1 at +3%: Close 40%, move SL to breakeven
- TP2 at +5%: Close 30%, move SL to TP1
- TP3 at +8%: Close 30%, trade complete

**Result:** Lock in profits progressively, reduce reversal risk

---

## Spec Location

All spec files are in `.kiro/specs/scaled-take-profit/`:

1. **requirements.md** - 8 requirements with 35 acceptance criteria
2. **design.md** - Complete technical design with 10 correctness properties
3. **tasks.md** - 20 implementation tasks (all tests required)

---

## Key Design Decisions

### Configuration (Default)

```json
{
  "enable_scaled_take_profit": false,
  "scaled_tp_levels": [
    {"profit_pct": 0.03, "close_pct": 0.40},  // TP1: +3%, close 40%
    {"profit_pct": 0.05, "close_pct": 0.30},  // TP2: +5%, close 30%
    {"profit_pct": 0.08, "close_pct": 0.30}   // TP3: +8%, close 30%
  ],
  "scaled_tp_min_order_size": 0.001,
  "scaled_tp_fallback_to_single": true
}
```

### Architecture

**New Component:** `ScaledTakeProfitManager`
- Tracks TP levels hit per position
- Executes partial closes
- Updates stop loss ladder
- Handles edge cases

**Integration Points:**
- TradingBot (live/paper trading)
- BacktestEngine (historical testing)
- Dashboard (UI display)
- Config (settings management)

### Stop Loss Ladder

| Event | Stop Loss Level |
|-------|----------------|
| Entry | Initial SL (5x ATR) |
| TP1 Hit (+3%) | Breakeven (entry price) |
| TP2 Hit (+5%) | TP1 level (+3%) |
| TP3 Hit (+8%) | Trade closed |

---

## Implementation Tasks (20 Total)

### Core Implementation (12 tasks)
1. Configuration parameters
2. Position model extensions
3. Data models
4. ScaledTakeProfitManager core
5. Partial close execution
6. Stop loss ladder
7. Minimum order size handling
8. TP status tracking
9. TradingBot integration
10. Backtest integration
11. Comprehensive logging
12. Edge case handling

### Testing (8 tasks)
- 6 property-based tests
- 2 unit test suites
- All tests are REQUIRED

### UI & Deployment (8 tasks)
13. Dashboard TP display
14. Trade history display
15. Analytics
16. Configuration file
17. Backtest comparison
18. Paper mode testing
19. Documentation
20. Final checkpoint

---

## Correctness Properties

10 properties to ensure correctness:

1. **TP Level Ordering** - TPs hit in sequence
2. **Position Size Conservation** - No quantity lost/created
3. **Stop Loss Monotonicity (Long)** - SL only moves up
4. **Stop Loss Monotonicity (Short)** - SL only moves down
5. **Close Percentage Sum** - Percentages = 100%
6. **Minimum Order Size Compliance** - Respects Binance minimums
7. **Profit Level Monotonicity** - Profit levels ascending
8. **Partial Exit Recording** - All partials logged
9. **Remaining Size After Final TP** - Zero remaining
10. **Breakeven Protection** - SL at/above entry after TP1

---

## Expected Benefits

### Risk Management
✅ Lock in profits early (don't give back gains)  
✅ Reduce risk progressively  
✅ Better win rate (easier to hit 3% than 8%)  
✅ Psychological comfort

### Performance
✅ Higher win rate expected  
✅ Better risk/reward ratio  
✅ Professional trader approach  
✅ Maintains exposure for big moves

---

## Testing Strategy

### 1. Property-Based Tests (6 tests)
- Configuration validation
- TP level ordering
- Position size conservation
- Stop loss monotonicity
- Minimum order size compliance

### 2. Unit Tests (2 suites)
- Backtest integration
- Edge case handling

### 3. Integration Tests
- Full trade lifecycle
- Backtest comparison
- Dashboard display

### 4. Paper Trading (7 days)
- Real market conditions
- Verify partial closes
- Monitor for issues

---

## Deployment Plan

### Phase 1: Implementation (Tasks 1-12)
- Build core functionality
- Add all tests
- Integrate with bot and backtest

### Phase 2: UI & Testing (Tasks 13-17)
- Dashboard updates
- Backtest comparison
- Verify improvements

### Phase 3: Validation (Tasks 18-19)
- Paper trading for 7 days
- Monitor performance
- Document results

### Phase 4: Production (Task 20)
- Final checkpoint
- Deploy to EC2 if successful
- Monitor in LIVE mode

---

## Rollback Plan

If issues arise:

1. Set `enable_scaled_take_profit = false` in config
2. Restart bot
3. System reverts to single TP behavior
4. No data loss or position corruption

---

## Next Steps

**To start implementation:**

1. Open `.kiro/specs/scaled-take-profit/tasks.md`
2. Click "Start task" next to Task 1
3. Follow the implementation plan
4. Complete tasks in order
5. Run tests after each task

**Estimated Timeline:**
- Core implementation: 2-3 days
- Testing & UI: 1-2 days
- Paper trading validation: 7 days
- Total: ~10-12 days to production-ready

---

## Success Criteria

The feature will be considered successful if:

✅ All 20 tasks completed  
✅ All tests passing  
✅ Backtest shows improvement over single TP  
✅ Paper trading runs without errors for 7 days  
✅ Dashboard displays correctly  
✅ No position integrity issues  
✅ Partial closes execute as expected  

---

## Questions or Issues?

If you encounter any issues during implementation:

1. Check the design document for technical details
2. Review the requirements for acceptance criteria
3. Consult the correctness properties for expected behavior
4. Ask for clarification before proceeding

---

**The spec is complete and ready for implementation!** 🚀

You can start by opening the tasks file and beginning with Task 1: Add configuration parameters.
