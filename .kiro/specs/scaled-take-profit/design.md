# Design Document: Scaled Take Profit Strategy

## Overview

The Scaled Take Profit feature implements a progressive profit-taking strategy that closes portions of a position at multiple price levels while moving the stop loss upward to protect gains. This approach significantly reduces the risk of giving back profits when momentum reverses before reaching the final target.

**Key Benefits:**
- Locks in profits progressively at multiple levels
- Reduces risk of full reversal losses
- Higher win rate (easier to hit first TP than final TP)
- Professional trader approach to position management
- Maintains exposure for larger moves

**Strategy Flow:**
1. Position enters at price X
2. Price reaches TP1 (+3%) → Close 40%, move SL to breakeven
3. Price reaches TP2 (+5%) → Close 30%, move SL to TP1 level
4. Price reaches TP3 (+8%) → Close remaining 30%, trade complete

## Architecture

### Component Interaction

```
┌─────────────────┐
│  Trading Bot    │
│   (main.py)     │
└────────┬────────┘
         │
         ├──────────────────────────────────────┐
         │                                      │
         v                                      v
┌────────────────────┐              ┌──────────────────────┐
│  Position Manager  │              │   Config Manager     │
│                    │◄─────────────│  (scaled_tp_config)  │
└────────┬───────────┘              └──────────────────────┘
         │
         v
┌────────────────────────────┐
│  Scaled TP Manager         │
│  (new component)           │
│  - Track TP levels hit     │
│  - Calculate partial sizes │
│  - Execute partial closes  │
│  - Update stop loss ladder │
└────────┬───────────────────┘
         │
         ├──────────────┬──────────────┬────────────────┐
         v              v              v                v
┌────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐
│  Binance   │  │   Backtest   │  │   Logger   │  │Dashboard │
│    API     │  │    Engine    │  │            │  │          │
└────────────┘  └──────────────┘  └────────────┘  └──────────┘
```

### Data Flow

1. **Position Entry:**
   - Bot enters position with full size
   - Scaled TP Manager initializes TP tracking for symbol
   - Sets initial stop loss

2. **Price Monitoring:**
   - Each candle, check current price against TP levels
   - If TP level hit → trigger partial close
   - Update stop loss to new level
   - Log partial exit details

3. **Partial Close Execution:**
   - Calculate quantity to close (percentage of remaining)
   - Verify meets Binance minimum order size
   - Place reduceOnly market order
   - Update position size in memory
   - Record partial exit in trade history

4. **Stop Loss Update:**
   - Move stop loss to previous TP level
   - Ensure stop only moves in favorable direction
   - Update position object with new stop

## Components and Interfaces

### 1. ScaledTakeProfitManager (New Component)

**Location:** `src/scaled_tp_manager.py`

**Responsibilities:**
- Track which TP levels have been hit for each position
- Calculate partial close quantities
- Execute partial closes via Binance API
- Update stop loss ladder
- Handle edge cases (gaps, minimums, failures)

**Interface:**

```python
class ScaledTakeProfitManager:
    def __init__(self, config: Config, client: Optional[Client] = None):
        """Initialize with configuration and optional Binance client."""
        
    def check_take_profit_levels(
        self, 
        position: Position, 
        current_price: float
    ) -> Optional[PartialCloseAction]:
        """Check if any TP level should be triggered.
        
        Returns:
            PartialCloseAction if TP hit, None otherwise
        """
        
    def execute_partial_close(
        self, 
        position: Position, 
        action: PartialCloseAction
    ) -> PartialCloseResult:
        """Execute a partial close order.
        
        Returns:
            Result with success status, filled quantity, and profit
        """
        
    def update_stop_loss_ladder(
        self, 
        position: Position, 
        tp_level_hit: int
    ) -> float:
        """Update stop loss after TP level hit.
        
        Returns:
            New stop loss price
        """
        
    def get_tp_status(self, symbol: str) -> TPStatus:
        """Get current TP status for a symbol."""
        
    def reset_tracking(self, symbol: str) -> None:
        """Reset TP tracking when position closes."""
```

### 2. Configuration Extensions

**Location:** `src/config.py`

**New Parameters:**

```python
# Scaled Take Profit Configuration
enable_scaled_take_profit: bool = False
scaled_tp_levels: list = field(default_factory=lambda: [
    {"profit_pct": 0.03, "close_pct": 0.40},  # TP1: +3%, close 40%
    {"profit_pct": 0.05, "close_pct": 0.30},  # TP2: +5%, close 30%
    {"profit_pct": 0.08, "close_pct": 0.30}   # TP3: +8%, close 30%
])
scaled_tp_min_order_size: float = 0.001  # Binance minimum (symbol-specific)
scaled_tp_fallback_to_single: bool = True  # Fall back if minimums not met
```

### 3. Data Models

**Location:** `src/models.py`

**New Classes:**

```python
@dataclass
class PartialCloseAction:
    """Action to close part of a position."""
    tp_level: int  # 1, 2, or 3
    profit_pct: float  # Target profit percentage
    close_pct: float  # Percentage of position to close
    target_price: float  # Price at which to close
    quantity: float  # Actual quantity to close
    new_stop_loss: float  # New stop loss after close

@dataclass
class PartialCloseResult:
    """Result of a partial close execution."""
    success: bool
    order_id: Optional[str]
    filled_quantity: float
    fill_price: float
    realized_profit: float
    error_message: Optional[str]

@dataclass
class TPStatus:
    """Status of take profit levels for a position."""
    symbol: str
    levels_hit: List[int]  # [1, 2] means TP1 and TP2 hit
    remaining_size_pct: float  # 0.30 means 30% remaining
    current_stop_loss: float
    next_tp_level: Optional[int]  # Next TP to hit (None if all hit)
    next_tp_price: Optional[float]
```

**Position Model Extension:**

```python
@dataclass
class Position:
    # ... existing fields ...
    
    # New fields for scaled TP
    original_quantity: float = 0.0  # Initial position size
    partial_exits: List[Dict] = field(default_factory=list)  # History of partials
    tp_levels_hit: List[int] = field(default_factory=list)  # [1, 2, 3]
```

### 4. Backtest Engine Integration

**Location:** `src/backtest_engine.py`

**Modifications:**

```python
def _check_exit_conditions(self, position: Position, candle: dict) -> Optional[str]:
    """Check if position should be exited (modified for scaled TP)."""
    
    # If scaled TP enabled, check TP levels
    if self.config.enable_scaled_take_profit:
        action = self.scaled_tp_manager.check_take_profit_levels(
            position, 
            candle['close']
        )
        
        if action:
            # Simulate partial close
            result = self._simulate_partial_close(position, action, candle)
            
            # If this was final TP, exit completely
            if len(position.tp_levels_hit) == len(self.config.scaled_tp_levels):
                return "SCALED_TP_FINAL"
            
            # Otherwise, continue holding with reduced size
            return None
    
    # ... existing exit logic ...
```

### 5. Dashboard Integration

**Location:** `streamlit_app.py` and `src/streamlit_data_provider.py`

**New Display Elements:**

- Position card shows TP levels with checkmarks for completed
- Progress bar showing which TPs hit
- Remaining position size percentage
- Average exit price across partials
- Profit breakdown by TP level

## Data Models

### Configuration Schema

```json
{
  "enable_scaled_take_profit": true,
  "scaled_tp_levels": [
    {
      "profit_pct": 0.03,
      "close_pct": 0.40,
      "description": "First take profit"
    },
    {
      "profit_pct": 0.05,
      "close_pct": 0.30,
      "description": "Second take profit"
    },
    {
      "profit_pct": 0.08,
      "close_pct": 0.30,
      "description": "Final take profit"
    }
  ],
  "scaled_tp_min_order_size": 0.001,
  "scaled_tp_fallback_to_single": true
}
```

### Position Tracking Schema

```json
{
  "symbol": "BTCUSDT",
  "entry_price": 50000.0,
  "original_quantity": 0.1,
  "current_quantity": 0.03,
  "tp_levels_hit": [1, 2],
  "partial_exits": [
    {
      "tp_level": 1,
      "exit_time": 1708450000000,
      "exit_price": 51500.0,
      "quantity_closed": 0.04,
      "profit": 60.0,
      "profit_pct": 0.03,
      "new_stop_loss": 50000.0
    },
    {
      "tp_level": 2,
      "exit_time": 1708453600000,
      "exit_price": 52500.0,
      "quantity_closed": 0.03,
      "profit": 75.0,
      "profit_pct": 0.05,
      "new_stop_loss": 51500.0
    }
  ],
  "current_stop_loss": 51500.0
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: TP Level Ordering
*For any* position with scaled TP enabled, TP levels must be hit in ascending order (TP1 before TP2 before TP3)
**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Position Size Conservation
*For any* position after partial closes, the sum of all closed quantities plus remaining quantity must equal the original quantity
**Validates: Requirements 1.1, 1.2, 1.3**

### Property 3: Stop Loss Monotonicity (Long)
*For any* long position, after each TP level hit, the new stop loss must be greater than or equal to the previous stop loss
**Validates: Requirements 1.5**

### Property 4: Stop Loss Monotonicity (Short)
*For any* short position, after each TP level hit, the new stop loss must be less than or equal to the previous stop loss
**Validates: Requirements 1.5**

### Property 5: Close Percentage Sum
*For any* scaled TP configuration, the sum of all close percentages must equal 1.0 (100%)
**Validates: Requirements 2.4**

### Property 6: Minimum Order Size Compliance
*For any* partial close action, if the calculated quantity is below the minimum order size, the action must be skipped or adjusted
**Validates: Requirements 3.1, 3.2, 3.3**

### Property 7: Profit Level Monotonicity
*For any* scaled TP configuration, profit levels must be in strictly ascending order
**Validates: Requirements 2.5**

### Property 8: Partial Exit Recording
*For any* successful partial close, the system must record the TP level, quantity, price, and profit in the position's partial_exits list
**Validates: Requirements 4.1, 4.2**

### Property 9: Remaining Size After Final TP
*For any* position where all TP levels have been hit, the remaining quantity must be zero
**Validates: Requirements 1.3**

### Property 10: Breakeven Protection
*For any* position where TP1 has been hit, the stop loss must be at or above (for longs) or at or below (for shorts) the entry price
**Validates: Requirements 1.1**

## Error Handling

### 1. Configuration Errors

**Invalid TP Levels:**
- **Error:** TP levels not in ascending order
- **Action:** Log error, disable scaled TP, fall back to single TP
- **Message:** "Scaled TP disabled: profit levels must be in ascending order"

**Invalid Close Percentages:**
- **Error:** Close percentages don't sum to 100%
- **Action:** Normalize percentages, log warning
- **Message:** "Scaled TP percentages normalized from X% to 100%"

### 2. Order Execution Errors

**Minimum Size Violation:**
- **Error:** Partial close quantity below Binance minimum
- **Action:** Skip this TP level, proceed to next
- **Message:** "TP{level} skipped: quantity {qty} below minimum {min}"

**API Failure:**
- **Error:** Binance API returns error on partial close
- **Action:** Retry once, if fails log error and continue
- **Message:** "Partial close failed for {symbol} TP{level}: {error}"

**Insufficient Balance:**
- **Error:** Not enough position size to close
- **Action:** Close remaining amount, mark as final TP
- **Message:** "Closing remaining {qty} at TP{level} (insufficient for full close)"

### 3. Edge Cases

**Price Gaps Through Multiple TPs:**
- **Scenario:** Price jumps from below TP1 to above TP2 in one candle
- **Action:** Execute all applicable partial closes in order
- **Logging:** Log each TP hit with timestamp and price

**Position Restoration After Restart:**
- **Scenario:** Bot restarts with open position that has hit some TPs
- **Action:** Restore TP tracking from position.partial_exits
- **Validation:** Verify remaining quantity matches expected

**Network Interruption During Partial Close:**
- **Scenario:** Order placed but confirmation not received
- **Action:** Query order status, update position accordingly
- **Fallback:** If status unknown, assume order failed and retry

## Testing Strategy

### Unit Tests

**Test Coverage:**
1. TP level checking logic
2. Partial close quantity calculations
3. Stop loss ladder updates
4. Configuration validation
5. Minimum order size handling
6. Edge case scenarios

**Example Tests:**
```python
def test_tp_level_ordering():
    """Test that TP levels are checked in correct order."""
    
def test_position_size_conservation():
    """Test that partial closes don't lose or create quantity."""
    
def test_stop_loss_moves_up_only_for_longs():
    """Test stop loss only moves favorably for long positions."""
    
def test_minimum_order_size_skip():
    """Test that sub-minimum partials are skipped."""
```

### Property-Based Tests

**Test 1: Position Size Conservation Property**
- **Feature:** scaled-take-profit, Property 2
- **Strategy:** Generate random positions with random partial closes
- **Verify:** Sum of closes + remaining = original quantity
- **Iterations:** 100

**Test 2: Stop Loss Monotonicity Property**
- **Feature:** scaled-take-profit, Property 3 & 4
- **Strategy:** Generate random positions, simulate TP hits
- **Verify:** Stop loss only moves favorably (up for longs, down for shorts)
- **Iterations:** 100

**Test 3: Close Percentage Sum Property**
- **Feature:** scaled-take-profit, Property 5
- **Strategy:** Generate random TP configurations
- **Verify:** Close percentages sum to 1.0 after normalization
- **Iterations:** 100

### Integration Tests

1. **Full Trade Lifecycle:**
   - Enter position
   - Hit TP1 → verify partial close and SL move
   - Hit TP2 → verify second partial and SL move
   - Hit TP3 → verify final close
   - Verify total profit matches expected

2. **Backtest Integration:**
   - Run backtest with scaled TP enabled
   - Verify all partial exits recorded
   - Compare results to single TP backtest
   - Verify metrics calculated correctly

3. **Dashboard Display:**
   - Open position with some TPs hit
   - Verify dashboard shows correct status
   - Verify TP progress indicators
   - Verify profit breakdown

## Performance Considerations

### Memory Impact

**Additional Memory Per Position:**
- TP tracking: ~200 bytes
- Partial exits history: ~100 bytes per partial (max 3)
- Total: ~500 bytes per position

**Impact:** Negligible (< 1KB per position)

### API Rate Limits

**Additional API Calls:**
- Partial close orders: 2-3 per position (vs 1 for single TP)
- Stop loss updates: 2-3 per position

**Mitigation:**
- Batch stop loss updates where possible
- Use reduceOnly flag to avoid separate SL orders

### Computation Overhead

**Per Candle:**
- Check 3 TP levels vs 1: ~3x comparison operations
- Calculate partial quantities: O(1) per TP

**Impact:** Negligible (< 1ms per position per candle)

## Migration Strategy

### Phase 1: Add Feature (Disabled by Default)

1. Add `ScaledTakeProfitManager` class
2. Add configuration parameters
3. Integrate into position management
4. Add backtest support
5. Keep `enable_scaled_take_profit = false` by default

### Phase 2: Testing

1. Run backtests comparing scaled vs single TP
2. Test in PAPER mode for 7 days
3. Verify all edge cases handled
4. Validate dashboard displays correctly

### Phase 3: Gradual Rollout

1. Enable for PAPER mode users first
2. Monitor for issues
3. Enable for LIVE mode after validation
4. Provide migration guide for existing users

### Backward Compatibility

- Existing positions continue with single TP
- New positions use scaled TP if enabled
- Configuration remains valid with or without scaled TP settings
- Dashboard shows appropriate UI for both modes

## Security Considerations

### API Key Safety

- Use same API key validation as existing system
- Partial close orders use reduceOnly flag
- No additional permissions required

### Position Integrity

- Validate remaining quantity after each partial
- Prevent over-closing (total closes > original size)
- Log all partial closes for audit trail

### Configuration Validation

- Validate TP levels on startup
- Reject invalid configurations
- Provide clear error messages

## Deployment Plan

### Local Testing

1. Implement `ScaledTakeProfitManager`
2. Add unit tests
3. Add property-based tests
4. Run backtests
5. Verify results

### Paper Trading

1. Deploy to local machine in PAPER mode
2. Monitor for 7 days
3. Verify partial closes execute correctly
4. Check dashboard displays

### EC2 Deployment

1. Deploy code to EC2
2. Update config with scaled TP settings
3. Restart bot in PAPER mode
4. Monitor for 7 days
5. If successful, consider LIVE mode

### Rollback Plan

- Set `enable_scaled_take_profit = false`
- Restart bot
- System reverts to single TP behavior
- No data loss or position corruption

---

## Summary

The Scaled Take Profit feature provides a professional-grade exit strategy that significantly improves risk management by locking in profits progressively. The implementation is modular, well-tested, and backward compatible, allowing for safe deployment and easy rollback if needed.

**Key Implementation Points:**
- New `ScaledTakeProfitManager` component
- Configuration-driven TP levels
- Full backtest support
- Dashboard integration
- Comprehensive error handling
- Property-based testing for correctness
