# Design Document: Multi-Symbol Indicator Display

## Overview

This design addresses the issue where the trading bot dashboard shows zero values for technical indicators (ADX, RVOL, ATR) for all symbols except the currently processed one. The solution involves adding per-symbol indicator storage in the TradingBot class and modifying the state-saving logic to include all symbol indicators.

## Architecture

The fix involves three main components:

1. **TradingBot Class**: Add `_symbol_indicators` dictionary to store indicators per symbol
2. **_process_symbol Method**: Update to store calculated indicators in the dictionary
3. **_save_realtime_state Method**: Modify to read from the per-symbol indicator storage

### Data Flow

```
Event Loop → Process Symbol → Calculate Indicators → Store in _symbol_indicators
                                                              ↓
Dashboard ← Read JSON ← Save State ← Read from _symbol_indicators
```

## Components and Interfaces

### 1. TradingBot._symbol_indicators

**Type**: `Dict[str, Dict[str, float]]`

**Structure**:
```python
{
    "DOTUSDT": {
        "adx": 44.00,
        "rvol": 0.59,
        "atr": 0.0099,
        "signal": "NONE",
        "timestamp": 1739587216.477
    },
    "XRPUSDT": {
        "adx": 32.15,
        "rvol": 1.23,
        "atr": 0.0045,
        "signal": "LONG",
        "timestamp": 1739587216.477
    }
}
```

**Purpose**: Central storage for per-symbol indicator data

### 2. TradingBot.__init__() Modification

Add initialization of the indicator storage dictionary:

```python
# Per-symbol indicator storage for dashboard
self._symbol_indicators: Dict[str, Dict[str, float]] = {}
```

### 3. TradingBot._process_symbol() Modification

After calculating indicators (line 738), store them:

```python
# Store indicators for this symbol (for dashboard display)
self._symbol_indicators[symbol] = {
    "adx": self.strategy.current_indicators.adx,
    "rvol": self.strategy.current_indicators.rvol,
    "atr": self.strategy.current_indicators.atr_15m,
    "signal": "LONG" if long_signal else "SHORT" if short_signal else "NONE",
    "timestamp": time.time()
}
```

### 4. TradingBot._save_realtime_state() Modification

Replace lines 1095-1104 with logic that reads from `_symbol_indicators`:

```python
# Collect per-symbol market data
symbols_data = []
for symbol in trading_symbols:
    try:
        # Get latest candles for this symbol
        symbol_candles = self.data_manager.get_latest_candles("15m", 1, symbol=symbol)
        symbol_price = symbol_candles[-1].close if symbol_candles else 0.0
        
        # Get stored indicators for this symbol
        if symbol in self._symbol_indicators:
            stored = self._symbol_indicators[symbol]
            symbol_adx = stored.get("adx", 0.0)
            symbol_rvol = stored.get("rvol", 0.0)
            symbol_atr = stored.get("atr", 0.0)
            symbol_signal = stored.get("signal", "NONE")
        else:
            # Symbol not processed yet
            symbol_adx = 0.0
            symbol_rvol = 0.0
            symbol_atr = 0.0
            symbol_signal = "NONE"
        
        symbols_data.append({
            "symbol": symbol,
            "current_price": symbol_price,
            "adx": symbol_adx,
            "rvol": symbol_rvol,
            "atr": symbol_atr,
            "signal": symbol_signal
        })
    except Exception as e:
        logger.debug(f"Error getting data for {symbol}: {e}")
        continue
```

## Data Models

### SymbolIndicators (Conceptual)

```python
{
    "adx": float,        # ADX value (0-100)
    "rvol": float,       # Relative volume (0-5+)
    "atr": float,        # Average True Range in price units
    "signal": str,       # "LONG", "SHORT", or "NONE"
    "timestamp": float   # Unix timestamp of last update
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Indicator persistence across symbols

*For any* symbol in the trading portfolio, after the bot processes that symbol and calculates indicators, those indicator values should be stored and retrievable until the next update for that symbol.

**Validates: Requirements 1.1, 1.5, 2.2**

### Property 2: Complete symbol data in JSON output

*For any* symbol in the trading portfolio, when the bot saves state to binance_results.json, the symbols_data array should contain an entry for that symbol with either calculated indicator values or zeros if not yet processed.

**Validates: Requirements 1.2, 2.3**

### Property 3: Dashboard displays stored values

*For any* symbol with stored indicator data, when the dashboard reads binance_results.json, it should display the stored ADX, RVOL, and ATR values, not zeros.

**Validates: Requirements 1.3, 3.2**

### Property 4: Indicator staleness detection

*For any* symbol indicator data, if the timestamp is older than 60 seconds, the dashboard should indicate that the data may be stale.

**Validates: Requirements 1.4, 3.5**

## Error Handling

1. **Missing Symbol Data**: If a symbol hasn't been processed yet, display 0.00 with "(Loading...)" indicator
2. **Stale Data**: If indicator timestamp is >60 seconds old, show warning icon
3. **Exception During Storage**: Log error but continue processing other symbols
4. **Exception During Retrieval**: Fall back to 0.00 values for that symbol

## Testing Strategy

### Unit Tests

1. Test `_symbol_indicators` dictionary initialization
2. Test indicator storage in `_process_symbol()`
3. Test indicator retrieval in `_save_realtime_state()`
4. Test handling of missing symbol data
5. Test JSON serialization of indicator data

### Integration Tests

1. Test full flow: process symbol → store indicators → save state → read JSON
2. Test multiple symbols processed in sequence
3. Test dashboard display with real indicator values
4. Test indicator updates over time

### Manual Testing

1. Start bot in paper mode with 5 symbols
2. Wait for all symbols to be processed (check logs)
3. Open dashboard Market Data page
4. Verify all symbols show non-zero ADX, RVOL, ATR values
5. Verify values update every 5 seconds
6. Verify signal indicators (LONG/SHORT/NONE) are correct

## Implementation Notes

1. **Minimal Changes**: Only modify 3 locations in `src/trading_bot.py`
2. **Backward Compatible**: Existing single-symbol mode continues to work
3. **Performance**: Dictionary lookup is O(1), no performance impact
4. **Memory**: Stores ~5 floats per symbol, negligible memory usage
5. **Thread Safety**: Not needed - single-threaded event loop

## Deployment

1. Update `src/trading_bot.py` with the three modifications
2. Restart the bot (existing positions will be preserved)
3. Dashboard will automatically pick up new indicator data
4. No configuration changes required
