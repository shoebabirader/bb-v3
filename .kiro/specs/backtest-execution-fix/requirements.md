# Backtest Execution Fix - Requirements Document

## Introduction

The current backtest engine has a critical flaw in trade execution simulation that causes unrealistic results. Trades are being entered and exited within the same candle, leading to immediate stop-loss hits and poor performance metrics that don't reflect real trading conditions.

## Glossary

- **Backtest Engine**: System component that simulates trading strategy on historical data
- **Candle**: OHLCV data point representing price action over a time period
- **Entry Execution**: Simulated order fill when opening a new position
- **Exit Execution**: Simulated order fill when closing an existing position
- **Trailing Stop**: Dynamic stop-loss that moves with favorable price action
- **Intra-Candle Execution**: Trade execution that occurs within a single candle period
- **Look-Ahead Bias**: Using future information not available at decision time

## Requirements

### Requirement 1

**User Story:** As a trader, I want backtest results to reflect realistic trade execution timing, so that I can trust the performance metrics for live trading decisions.

#### Acceptance Criteria

1. WHEN a long entry signal is generated THEN the system SHALL simulate entry at the NEXT candle's open price
2. WHEN a short entry signal is generated THEN the system SHALL simulate entry at the NEXT candle's open price  
3. WHEN a position is opened THEN the system SHALL NOT check for exit conditions until AT LEAST the candle AFTER entry
4. WHEN checking stop-loss hits THEN the system SHALL only evaluate stops starting from the candle after entry
5. WHEN a take-profit level is reached THEN the system SHALL simulate exit at the target price within that candle

### Requirement 2

**User Story:** As a trader, I want the backtest to avoid look-ahead bias, so that results accurately represent what would happen in real-time trading.

#### Acceptance Criteria

1. WHEN generating entry signals THEN the system SHALL only use indicator values calculated from completed candles
2. WHEN a candle is in progress THEN the system SHALL NOT generate entry signals until the candle closes
3. WHEN calculating indicators THEN the system SHALL use only historical data available at that point in time
4. WHEN simulating order fills THEN the system SHALL NOT use information from future candles
5. WHEN a position is entered THEN the system SHALL wait for the next candle before evaluating exit conditions

### Requirement 3

**User Story:** As a trader, I want realistic fill simulation with proper timing, so that backtest results match live trading execution.

#### Acceptance Criteria

1. WHEN an entry signal is generated on candle N THEN the system SHALL execute entry at the open of candle N+1
2. WHEN a stop-loss is set THEN the system SHALL only check if it was hit starting from candle N+2 (where N is entry candle)
3. WHEN a trailing stop is updated THEN the system SHALL apply the new stop level starting from the next candle
4. WHEN multiple positions exist THEN the system SHALL track entry candle index separately for each position
5. WHEN a position is closed THEN the system SHALL record the actual candle index where exit occurred

### Requirement 4

**User Story:** As a trader, I want proper handling of entry and exit timing in the backtest loop, so that trades have realistic duration and profit/loss patterns.

#### Acceptance Criteria

1. WHEN iterating through candles THEN the system SHALL maintain a reference to the entry candle index for each position
2. WHEN checking exit conditions THEN the system SHALL skip evaluation if current candle index <= entry candle index + 1
3. WHEN a position is opened THEN the system SHALL store the entry candle index in the Position object
4. WHEN calculating trade duration THEN the system SHALL ensure minimum duration of at least 2 candle periods
5. WHEN a stop is hit THEN the system SHALL verify the hit occurred at least 2 candles after entry

### Requirement 5

**User Story:** As a trader, I want the backtest to properly simulate the delay between signal generation and order execution, so that results account for real-world execution lag.

#### Acceptance Criteria

1. WHEN a signal is generated at the close of candle N THEN the system SHALL assume order placement occurs at that time
2. WHEN an order is placed THEN the system SHALL simulate fill at the open of candle N+1
3. WHEN the fill occurs THEN the system SHALL set stops and targets based on the fill price
4. WHEN stops are set THEN the system SHALL begin monitoring for stop hits starting from candle N+2
5. WHEN a take-profit is set THEN the system SHALL begin monitoring for TP hits starting from candle N+2
