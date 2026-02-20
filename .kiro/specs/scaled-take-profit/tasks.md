# Implementation Plan: Scaled Take Profit Strategy

- [x] 1. Add configuration parameters for scaled take profit





  - Add `enable_scaled_take_profit`, `scaled_tp_levels`, `scaled_tp_min_order_size`, `scaled_tp_fallback_to_single` to Config class
  - Add validation logic for TP levels (ascending order, percentages sum to 100%)
  - Add default configuration values
  - _Requirements: 2.1, 2.2, 2.4, 2.5_

- [x] 1.1 Write property test for configuration validation


  - **Property 5: Close percentage sum**
  - **Property 7: Profit level monotonicity**
  - **Validates: Requirements 2.4, 2.5**

- [x] 2. Extend Position model for scaled TP tracking




  - Add `original_quantity`, `partial_exits`, `tp_levels_hit` fields to Position dataclass
  - Update Position initialization to set original_quantity
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 3. Create data models for scaled TP operations










  - Create `PartialCloseAction` dataclass
  - Create `PartialCloseResult` dataclass
  - Create `TPStatus` dataclass
  - _Requirements: 4.1, 4.4_

- [x] 4. Implement ScaledTakeProfitManager core logic





  - Create `src/scaled_tp_manager.py` file
  - Implement `__init__` method with config and client
  - Implement `check_take_profit_levels` method to detect TP hits
  - Implement `_calculate_target_prices` helper method
  - Implement `_calculate_partial_quantity` helper method
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 4.1 Write property test for TP level checking


  - **Property 1: TP level ordering**
  - **Validates: Requirements 1.1, 1.2, 1.3**

- [x] 5. Implement partial close execution logic





  - Implement `execute_partial_close` method in ScaledTakeProfitManager
  - Add Binance API integration for reduceOnly market orders
  - Add order status verification
  - Add retry logic for failed orders
  - _Requirements: 1.4, 3.5_

- [x] 5.1 Write property test for position size conservation


  - **Property 2: Position size conservation**
  - **Validates: Requirements 1.1, 1.2, 1.3**

- [x] 6. Implement stop loss ladder logic






  - Implement `update_stop_loss_ladder` method
  - Calculate new stop loss based on TP level hit
  - Ensure stop loss only moves favorably (up for longs, down for shorts)
  - Update Position object with new stop loss
  - _Requirements: 1.5_

- [x] 6.1 Write property test for stop loss monotonicity



  - **Property 3: Stop loss monotonicity (Long)**
  - **Property 4: Stop loss monotonicity (Short)**
  - **Validates: Requirements 1.5**

- [x] 7. Implement minimum order size handling





  - Add `_check_minimum_order_size` method
  - Skip TP levels below minimum
  - Close remaining if below minimum
  - Fall back to single TP if all partials below minimum
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 7.1 Write property test for minimum order size compliance


  - **Property 6: Minimum order size compliance**
  - **Validates: Requirements 3.1, 3.2, 3.3**

- [x] 8. Implement TP status tracking and reset





  - Implement `get_tp_status` method
  - Implement `reset_tracking` method
  - Add internal tracking dictionary for symbols
  - _Requirements: 4.4_

- [x] 9. Integrate ScaledTakeProfitManager into TradingBot





  - Initialize ScaledTakeProfitManager in TradingBot.__init__
  - Add scaled TP check in position monitoring loop
  - Execute partial closes when TP levels hit
  - Update position after partial closes
  - Log all scaled TP actions
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.1, 7.2, 7.3, 7.4_

- [x] 10. Integrate scaled TP into backtest engine





  - Add ScaledTakeProfitManager to BacktestEngine
  - Modify `_check_exit_conditions` to handle scaled TP
  - Implement `_simulate_partial_close` method
  - Update position size after simulated partials
  - Track partial exits in backtest results
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 10.1 Write unit tests for backtest integration


  - Test partial close simulation
  - Test position size updates
  - Test stop loss ladder in backtest
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 11. Add comprehensive logging for scaled TP





  - Log TP level hits with price and profit
  - Log partial close orders with details
  - Log partial close completions with fill price
  - Log stop loss updates
  - Log configuration errors
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 12. Handle edge cases and error scenarios





  - Handle price gaps through multiple TPs
  - Handle position restoration after restart
  - Handle network interruptions during partial close
  - Handle API failures with retry logic
  - Handle insufficient balance scenarios
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 12.1 Write unit tests for edge cases


  - Test price gap handling
  - Test position restoration
  - Test network interruption recovery
  - Test API failure retry
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 13. Update dashboard to display scaled TP information





  - Add TP level progress indicators to position cards
  - Show which TP levels have been hit (checkmarks)
  - Display original vs remaining position size
  - Show current stop loss level
  - Display next TP target price
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 14. Add trade history display for partial exits






  - Group partial exits under original trade entry
  - Show profit breakdown by TP level
  - Calculate and display average exit price
  - Show total profit across all partials
  - _Requirements: 8.4, 4.2, 4.3, 4.5_

- [ ] 15. Add analytics for scaled TP performance





  - Calculate average profit per TP level
  - Calculate hit rate for each TP level
  - Compare scaled TP vs single TP performance
  - Display metrics in dashboard analytics tab
  - _Requirements: 8.5_

- [ ] 16. Update configuration file with scaled TP settings
  - Add scaled TP configuration to config.json
  - Set `enable_scaled_take_profit = false` by default
  - Add example TP levels configuration
  - Document all new parameters
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 17. Run comprehensive backtest comparison
  - Run backtest with scaled TP enabled
  - Run backtest with single TP (current behavior)
  - Compare win rates, profit factors, total PnL
  - Analyze which approach performs better
  - Document results
  - _Requirements: 5.5_

- [ ] 18. Test in PAPER mode
  - Deploy to local machine with scaled TP enabled
  - Monitor for 3-7 days
  - Verify partial closes execute correctly
  - Verify stop loss ladder works
  - Verify dashboard displays correctly
  - Check for any errors or edge cases
  - _Requirements: All_

- [ ] 19. Create deployment documentation
  - Document how to enable scaled TP
  - Document configuration parameters
  - Provide example configurations
  - Document rollback procedure
  - Create troubleshooting guide
  - _Requirements: All_

- [ ] 20. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
