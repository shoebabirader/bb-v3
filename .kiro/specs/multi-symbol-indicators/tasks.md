# Implementation Plan: Multi-Symbol Indicator Display

- [x] 1. Add per-symbol indicator storage to TradingBot class





  - Add `_symbol_indicators` dictionary to `__init__()` method in `src/trading_bot.py`
  - Initialize as empty dict: `self._symbol_indicators: Dict[str, Dict[str, float]] = {}`
  - Add type import: `from typing import Dict` (if not already present)
  - _Requirements: 2.1, 2.2_

- [x] 2. Store indicators after processing each symbol





  - Locate the `_process_symbol()` method in `src/trading_bot.py`
  - After line 738 where `self.strategy.update_indicators()` is called
  - Add code to store current indicators in `_symbol_indicators[symbol]`
  - Store: adx, rvol, atr_15m, signal, timestamp
  - Handle both long_signal and short_signal to determine signal value
  - _Requirements: 1.1, 2.2_

- [x] 3. Update _save_realtime_state to read from per-symbol storage




  - Locate lines 1095-1104 in `_save_realtime_state()` method
  - Replace the conditional logic that only populates indicators for primary symbol
  - Add loop to read from `_symbol_indicators` dictionary for each symbol
  - If symbol not in dictionary, use 0.0 as default values
  - Preserve existing price fetching logic
  - _Requirements: 1.2, 2.3_

- [ ]* 4. Write unit tests for indicator storage
  - Create `tests/test_multi_symbol_indicators.py`
  - Test: `_symbol_indicators` dictionary is initialized
  - Test: Indicators are stored correctly after processing symbol
  - Test: Stored indicators are retrieved correctly in save state
  - Test: Missing symbol returns 0.0 values
  - _Requirements: 1.1, 1.2, 2.2, 2.3_

- [x] 5. Test with running bot





  - Start bot in paper mode with portfolio enabled
  - Wait 30 seconds for all symbols to be processed
  - Check `binance_results.json` for non-zero indicator values
  - Verify all 5 symbols have ADX, RVOL, ATR populated
  - _Requirements: 1.2, 1.3_

- [ ] 6. Verify dashboard display




  - Open Streamlit dashboard
  - Navigate to Market Data page
  - Verify all symbols show non-zero indicators
  - Verify indicators update every 5 seconds
  - Verify signal indicators (LONG/SHORT/NONE) display correctly
  - _Requirements: 1.3, 3.1, 3.2, 3.3_

- [x] 7. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.
