# Requirements Document: Multi-Symbol Indicator Display

## Introduction

The trading bot dashboard currently shows zeros (0.00) for ADX, RVOL, and ATR indicators for all symbols except the primary one in portfolio mode. This is because the bot only saves indicator data for the currently processed symbol, not all symbols in the portfolio. Users need to see real-time indicator values for all symbols to make informed trading decisions.

## Glossary

- **System**: The Binance Futures Trading Bot
- **Dashboard**: The Streamlit web interface that displays bot status and market data
- **Indicator**: Technical analysis metric (ADX, RVOL, ATR) calculated from price data
- **Portfolio Mode**: Trading configuration with multiple symbols enabled
- **Symbol**: A trading pair (e.g., DOTUSDT, XRPUSDT)
- **binance_results.json**: JSON file that stores bot state for dashboard consumption

## Requirements

### Requirement 1

**User Story:** As a trader using portfolio mode, I want to see real-time ADX, RVOL, and ATR values for all symbols on the Market Data page, so that I can monitor market conditions across my entire portfolio.

#### Acceptance Criteria

1. WHEN the bot processes each symbol in the event loop THEN the system SHALL store the calculated indicators (ADX, RVOL, ATR, signal) for that symbol
2. WHEN the bot saves realtime state to binance_results.json THEN the system SHALL include all stored indicator values in the symbols_data array
3. WHEN the dashboard displays the Market Data page THEN the system SHALL show non-zero indicator values for all symbols that have been processed
4. WHEN a symbol has not been processed yet THEN the system SHALL display 0.00 for its indicators with a visual indicator that data is loading
5. WHEN indicators are updated for a symbol THEN the system SHALL preserve the previous values until new values are calculated

### Requirement 2

**User Story:** As a developer maintaining the bot, I want indicator data to be stored per-symbol in a centralized location, so that the codebase is maintainable and scalable.

#### Acceptance Criteria

1. WHEN the TradingBot class initializes THEN the system SHALL create a dictionary to store per-symbol indicator data
2. WHEN the _process_symbol method calculates indicators THEN the system SHALL update the per-symbol indicator storage
3. WHEN the _save_realtime_state method is called THEN the system SHALL retrieve indicator data from the per-symbol storage
4. WHEN a symbol is removed from the portfolio THEN the system SHALL clean up its stored indicator data
5. WHEN the bot restarts THEN the system SHALL initialize empty indicator storage for all symbols

### Requirement 3

**User Story:** As a trader, I want the dashboard to update indicator values every 5 seconds, so that I have near real-time visibility into market conditions.

#### Acceptance Criteria

1. WHEN the dashboard auto-refreshes THEN the system SHALL read the latest binance_results.json file
2. WHEN binance_results.json is updated THEN the system SHALL reflect changes within 5 seconds on the dashboard
3. WHEN multiple symbols are being tracked THEN the system SHALL update all symbol indicators at the same refresh rate
4. WHEN the bot is processing symbols sequentially THEN the system SHALL ensure all symbols are processed within the 5-second refresh window
5. WHEN network latency occurs THEN the system SHALL display the last known good values until new data arrives
