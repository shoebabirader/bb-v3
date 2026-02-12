# Requirements Document: Streamlit Trading Dashboard

## Introduction

A web-based user interface for monitoring and controlling the Binance futures trading bot. The dashboard provides real-time visualization of bot status, positions, performance metrics, and allows configuration changes without editing JSON files.

## Glossary

- **Dashboard**: The main Streamlit web interface
- **Bot**: The existing trading bot (main.py and related modules)
- **Data_Provider**: Module that reads bot state from files and logs
- **Control_Panel**: UI section with bot control buttons
- **Config_Editor**: UI section for modifying bot settings
- **Position**: An open trade with entry price, size, and PnL
- **Signal**: Trading signal (LONG/SHORT) based on indicators

## Requirements

### Requirement 1: Real-Time Status Display

**User Story:** As a trader, I want to see the bot's current status at a glance, so that I know if it's running correctly.

#### Acceptance Criteria

1. WHEN the dashboard loads, THE Dashboard SHALL display the current bot status (Running/Stopped)
2. WHEN the bot is running, THE Dashboard SHALL show the last update timestamp
3. WHEN displaying status, THE Dashboard SHALL show current balance and total PnL
4. THE Dashboard SHALL refresh status information every 5 seconds automatically
5. WHEN the bot is stopped, THE Dashboard SHALL display a warning indicator

### Requirement 2: Position Monitoring

**User Story:** As a trader, I want to see my open positions and their performance, so that I can track my trades.

#### Acceptance Criteria

1. WHEN positions exist, THE Dashboard SHALL display all open positions with symbol, side, entry price, current price, and PnL
2. WHEN displaying positions, THE Dashboard SHALL show stop loss and take profit levels
3. WHEN no positions are open, THE Dashboard SHALL display "No open positions"
4. THE Dashboard SHALL update position data every 5 seconds
5. WHEN displaying PnL, THE Dashboard SHALL use color coding (green for profit, red for loss)

### Requirement 3: Live Price and Indicators

**User Story:** As a trader, I want to see current price and indicator values, so that I understand market conditions.

#### Acceptance Criteria

1. WHEN displaying market data, THE Dashboard SHALL show current price for the configured symbol
2. WHEN displaying indicators, THE Dashboard SHALL show ADX, RVOL, and ATR values
3. WHEN indicators meet signal conditions, THE Dashboard SHALL highlight them
4. THE Dashboard SHALL display current signal status (LONG/SHORT/NONE)
5. THE Dashboard SHALL update market data every 5 seconds

### Requirement 4: Interactive Price Chart

**User Story:** As a trader, I want to see a price chart with indicators, so that I can visualize market movements.

#### Acceptance Criteria

1. WHEN displaying the chart, THE Dashboard SHALL show candlestick price data for the configured timeframe
2. WHEN positions exist, THE Dashboard SHALL mark entry points on the chart
3. WHEN displaying the chart, THE Dashboard SHALL overlay ATR bands
4. THE Dashboard SHALL allow selecting different timeframes (5m, 15m, 1h, 4h)
5. WHEN the chart updates, THE Dashboard SHALL fetch the latest 100 candles

### Requirement 5: Bot Control Panel

**User Story:** As a trader, I want to start, stop, and control the bot, so that I can manage trading operations.

#### Acceptance Criteria

1. WHEN the user clicks "Start Bot", THE Control_Panel SHALL launch the bot process
2. WHEN the user clicks "Stop Bot", THE Control_Panel SHALL terminate the bot process gracefully
3. WHEN the user clicks "Emergency Close All", THE Control_Panel SHALL close all open positions immediately
4. WHEN executing control actions, THE Control_Panel SHALL display confirmation dialogs for dangerous operations
5. WHEN control actions complete, THE Control_Panel SHALL show success or error messages

### Requirement 6: Configuration Editor

**User Story:** As a trader, I want to modify bot settings through the UI, so that I don't need to edit JSON files manually.

#### Acceptance Criteria

1. WHEN displaying settings, THE Config_Editor SHALL show all editable configuration parameters
2. WHEN the user modifies settings, THE Config_Editor SHALL validate input values
3. WHEN the user saves settings, THE Config_Editor SHALL write changes to config.json
4. WHEN settings are saved, THE Config_Editor SHALL display a confirmation message
5. WHEN invalid values are entered, THE Config_Editor SHALL show error messages and prevent saving

### Requirement 7: Trade History

**User Story:** As a trader, I want to see my recent trades, so that I can review my trading performance.

#### Acceptance Criteria

1. WHEN displaying trade history, THE Dashboard SHALL show the last 20 completed trades
2. WHEN displaying trades, THE Dashboard SHALL show entry time, exit time, symbol, side, PnL, and return percentage
3. WHEN displaying trade history, THE Dashboard SHALL allow sorting by date or PnL
4. THE Dashboard SHALL calculate and display win rate percentage
5. WHEN no trades exist, THE Dashboard SHALL display "No trade history available"

### Requirement 8: Performance Analytics

**User Story:** As a trader, I want to see performance metrics and charts, so that I can evaluate bot effectiveness.

#### Acceptance Criteria

1. WHEN displaying analytics, THE Dashboard SHALL show total PnL, win rate, and average profit per trade
2. WHEN displaying analytics, THE Dashboard SHALL show a cumulative PnL chart over time
3. WHEN displaying analytics, THE Dashboard SHALL calculate and show Sharpe ratio
4. WHEN displaying analytics, THE Dashboard SHALL show maximum drawdown
5. THE Dashboard SHALL allow filtering analytics by time period (24h, 7d, 30d, All)

### Requirement 9: Data Persistence and Loading

**User Story:** As a developer, I want the dashboard to read bot state from files, so that it works independently of the bot process.

#### Acceptance Criteria

1. WHEN loading data, THE Data_Provider SHALL read configuration from config/config.json
2. WHEN loading positions, THE Data_Provider SHALL read from binance_results.json
3. WHEN loading trade history, THE Data_Provider SHALL parse log files in the logs directory
4. WHEN files are missing, THE Data_Provider SHALL handle errors gracefully and show default values
5. THE Data_Provider SHALL cache data for 5 seconds to avoid excessive file reads

### Requirement 10: Responsive Layout

**User Story:** As a trader, I want the dashboard to work on different screen sizes, so that I can monitor from any device.

#### Acceptance Criteria

1. WHEN displaying on desktop, THE Dashboard SHALL use a multi-column layout
2. WHEN displaying on mobile, THE Dashboard SHALL stack sections vertically
3. WHEN resizing the browser, THE Dashboard SHALL adjust layout automatically
4. THE Dashboard SHALL use Streamlit's responsive grid system
5. WHEN displaying charts, THE Dashboard SHALL scale them to fit the viewport
