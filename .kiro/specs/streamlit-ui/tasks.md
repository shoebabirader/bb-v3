# Implementation Plan: Streamlit Trading Dashboard

## Overview

This plan implements a web-based Streamlit dashboard for monitoring and controlling the trading bot. The implementation follows a bottom-up approach: first building data access and utilities, then UI components, and finally integration and testing.

## Tasks

- [x] 1. Set up project structure and dependencies





  - Create `requirements_ui.txt` with Streamlit and related dependencies
  - Create `streamlit_app.py` as main entry point
  - Create `src/streamlit_data_provider.py` for data access
  - Create `src/streamlit_bot_controller.py` for bot control
  - Create `src/streamlit_config_editor.py` for config management
  - Create `src/streamlit_charts.py` for chart generation
  - _Requirements: 9.1, 9.2, 9.3_

- [x] 2. Implement Data Provider




  - [x] 2.1 Implement core data loading methods


    - Write `get_config()` to read config.json
    - Write `get_bot_status()` to check if bot process is running
    - Write `get_balance_and_pnl()` to read from binance_results.json
    - Write `get_open_positions()` to read positions
    - Write `get_market_data()` to read current price and indicators
    - _Requirements: 1.3, 2.1, 3.1, 3.2, 9.1, 9.2_

  - [x] 2.2 Write property test for file handling


    - **Property 16: Graceful File Handling**
    - **Validates: Requirements 9.4**

  - [x] 2.3 Implement caching mechanism


    - Write `_read_cached_json()` with 5-second TTL
    - Add cache invalidation logic
    - _Requirements: 9.5_

  - [x] 2.4 Implement trade history parsing


    - Write `_parse_trade_logs()` to read log files
    - Write `get_trade_history()` with limit parameter
    - _Requirements: 7.1, 9.3_

  - [x] 2.5 Write unit tests for data provider


    - Test with sample JSON files
    - Test with missing files
    - Test cache behavior
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 3. Implement Bot Controller





  - [x] 3.1 Implement process management


    - Write `start_bot()` to launch bot process
    - Write `stop_bot()` to terminate bot gracefully
    - Write `_is_running()` to check bot status
    - _Requirements: 5.1, 5.2, 1.1_

  - [x] 3.2 Implement emergency close functionality


    - Write `emergency_close_all()` to close positions
    - Add confirmation requirement
    - _Requirements: 5.3_

  - [x] 3.3 Write property test for control action feedback


    - **Property 7: Control Action Feedback**
    - **Validates: Requirements 5.5**

  - [x] 3.4 Write unit tests for bot controller


    - Test start/stop with mocked processes
    - Test error handling
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 4. Implement Config Editor





  - [x] 4.1 Implement config loading and saving


    - Write `load_config()` to read config.json
    - Write `save_config()` to write config.json
    - _Requirements: 6.1, 6.3_

  - [x] 4.2 Write property test for config round trip


    - **Property 9: Config Round Trip**
    - **Validates: Requirements 6.3**

  - [x] 4.3 Implement validation logic


    - Write `validate_config()` with all validation rules
    - Add validation for risk_per_trade, leverage, thresholds
    - _Requirements: 6.2, 6.5_

  - [x] 4.4 Write property test for config validation


    - **Property 8: Config Validation**
    - **Validates: Requirements 6.2, 6.5**

  - [x] 4.5 Write unit tests for config editor


    - Test validation with invalid inputs
    - Test save/load workflow
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [x] 5. Implement Chart Generator




  - [x] 5.1 Implement price chart generation


    - Write `create_price_chart()` with candlesticks
    - Add ATR bands overlay
    - Add position entry markers
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 5.2 Write property test for chart entry markers


    - **Property 4: Chart Entry Markers**
    - **Validates: Requirements 4.2**

  - [x] 5.3 Write property test for chart candle count


    - **Property 5: Chart Candle Count**
    - **Validates: Requirements 4.5**

  - [x] 5.4 Implement PnL chart generation


    - Write `create_pnl_chart()` for cumulative PnL
    - Add time series visualization
    - _Requirements: 8.2_

  - [x] 5.5 Write unit tests for chart generator


    - Test with sample candle data
    - Test with various position configurations
    - _Requirements: 4.1, 4.2, 4.3, 8.2_

- [x] 6. Checkpoint - Ensure all core components pass tests





  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement Dashboard Pages





  - [x] 7.1 Create main dashboard page


    - Implement `show_dashboard_page()` with status display
    - Show balance, PnL, and bot status
    - Add warning indicator for stopped bot
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [x] 7.2 Write property test for position display


    - **Property 1: Position Display Completeness**
    - **Validates: Requirements 2.1, 2.2**

  - [x] 7.3 Write property test for PnL color coding


    - **Property 2: PnL Color Coding**
    - **Validates: Requirements 2.5**

  - [x] 7.2 Create positions page


    - Implement `show_positions_page()` with position table
    - Display all required fields (symbol, side, entry, current, PnL, stops)
    - Add color coding for PnL
    - Handle empty state
    - _Requirements: 2.1, 2.2, 2.3, 2.5_

  - [x] 7.3 Create market data display


    - Show current price and indicators
    - Add highlighting for indicators meeting thresholds
    - Display signal status
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 7.4 Write property test for indicator highlighting


    - **Property 3: Indicator Highlighting**
    - **Validates: Requirements 3.3**

  - [x] 7.5 Create chart page


    - Implement `show_chart_page()` with price chart
    - Add timeframe selector
    - Integrate chart generator
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 8. Implement Trade History and Analytics



  - [x] 8.1 Create trade history page


    - Implement `show_trade_history_page()` with trade table
    - Display all required fields
    - Add sorting by date and PnL
    - Handle empty state
    - Calculate and display win rate
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 8.2 Write property test for trade display


    - **Property 10: Trade Display Completeness**
    - **Validates: Requirements 7.2**


  - [x] 8.3 Write property test for trade sorting

    - **Property 11: Trade Sorting**
    - **Validates: Requirements 7.3**


  - [x] 8.4 Write property test for win rate calculation

    - **Property 12: Win Rate Calculation**
    - **Validates: Requirements 7.4**


  - [x] 8.2 Create analytics page
    - Implement `show_analytics_page()` with metrics display
    - Show total PnL, win rate, average profit
    - Add cumulative PnL chart
    - Calculate and display Sharpe ratio
    - Calculate and display maximum drawdown
    - Add time period filter (24h, 7d, 30d, All)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_


  - [x] 8.3 Write property test for Sharpe ratio

    - **Property 13: Sharpe Ratio Calculation**
    - **Validates: Requirements 8.3**


  - [x] 8.4 Write property test for maximum drawdown

    - **Property 14: Maximum Drawdown Calculation**
    - **Validates: Requirements 8.4**

  - [x] 8.5 Write property test for time period filtering



    - **Property 15: Time Period Filtering**
    - **Validates: Requirements 8.5**

- [x] 9. Implement Settings and Controls





  - [x] 9.1 Create settings page

    - Implement `show_settings_page()` with config editor UI
    - Add input fields for all editable parameters
    - Add validation and error display
    - Add save button with confirmation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 9.2 Create controls page


    - Implement `show_controls_page()` with bot control buttons
    - Add Start Bot button
    - Add Stop Bot button
    - Add Emergency Close All button
    - Add confirmation dialogs for dangerous actions
    - Display success/error messages
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_


  - [x] 9.3 Write property test for control confirmations

    - **Property 6: Control Action Confirmations**
    - **Validates: Requirements 5.4**

- [x] 10. Implement Main App and Navigation





  - [x] 10.1 Create main app structure


    - Implement `main()` function with page routing
    - Add sidebar navigation
    - Configure page layout (wide mode)
    - Add auto-refresh with 5-second interval
    - _Requirements: 1.4, 10.1, 10.2, 10.3, 10.4, 10.5_


  - [x] 10.2 Add styling and branding

    - Set page title and icon
    - Add custom CSS for better appearance
    - Ensure responsive layout
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_


  - [x] 10.3 Write integration tests

    - Test full dashboard load
    - Test page navigation
    - Test data refresh
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 11. Create Launch Scripts






  - [x] 11.1 Create Windows batch script

    - Write `start_dashboard.bat` to launch bot and dashboard
    - Add proper error handling
    - _Requirements: All_


  - [x] 11.2 Create Python launch script

    - Write `start_dashboard.py` for cross-platform support
    - Add command-line options
    - _Requirements: All_


  - [x] 11.3 Write documentation

    - Create README for dashboard usage
    - Document configuration options
    - Add troubleshooting guide
    - _Requirements: All_

- [x] 12. Final checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests ensure components work together correctly
- The dashboard runs independently of the bot, reading shared files
- Auto-refresh keeps data current without manual intervention
- Confirmation dialogs prevent accidental dangerous actions
