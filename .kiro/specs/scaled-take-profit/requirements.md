# Requirements Document: Scaled Take Profit Strategy

## Introduction

This feature implements a scaled (partial) take profit strategy that progressively locks in profits at multiple price levels while letting winning positions run. Instead of a single fixed take profit target, the system will close portions of the position at different profit levels and progressively move the stop loss to protect gains.

## Glossary

- **Scaled Take Profit**: A strategy that closes portions of a position at multiple profit levels
- **Partial Close**: Closing a percentage of the position while keeping the remainder open
- **Stop Loss Ladder**: Progressive movement of stop loss to higher levels as take profit targets are hit
- **TP Level**: Take Profit Level - a specific profit percentage target
- **Position Remainder**: The portion of the position still open after partial closes

## Requirements

### Requirement 1

**User Story:** As a trader, I want to lock in profits progressively at multiple levels, so that I don't give back all gains when momentum reverses before reaching my final target.

#### Acceptance Criteria

1. WHEN a position reaches the first take profit level THEN the system SHALL close a configured percentage of the position and move the stop loss to breakeven
2. WHEN a position reaches the second take profit level THEN the system SHALL close another configured percentage of the position and move the stop loss to the first take profit level
3. WHEN a position reaches the third take profit level THEN the system SHALL close the remaining position percentage
4. WHEN any take profit level is hit THEN the system SHALL log the partial close with the profit amount and remaining position size
5. WHEN the stop loss is moved after a take profit hit THEN the system SHALL update the position's stop loss to the new level

### Requirement 2

**User Story:** As a trader, I want to configure the take profit levels and percentages, so that I can adjust the strategy based on market conditions and my risk tolerance.

#### Acceptance Criteria

1. WHEN the system loads configuration THEN it SHALL read the scaled take profit settings including profit levels and close percentages
2. WHEN scaled take profit is enabled THEN the system SHALL use the configured TP levels instead of the single take profit percentage
3. WHEN scaled take profit is disabled THEN the system SHALL fall back to the original single take profit behavior
4. WHEN the sum of close percentages does not equal 100% THEN the system SHALL log a warning and normalize the percentages
5. WHEN take profit levels are not in ascending order THEN the system SHALL log an error and disable scaled take profit

### Requirement 3

**User Story:** As a trader, I want the system to handle Binance minimum order sizes, so that partial closes don't fail due to exchange limitations.

#### Acceptance Criteria

1. WHEN calculating a partial close quantity THEN the system SHALL verify it meets Binance minimum order size requirements
2. WHEN a partial close quantity is below the minimum THEN the system SHALL skip that take profit level and proceed to the next
3. WHEN the remaining position after a partial close is below the minimum THEN the system SHALL close the entire remaining position
4. WHEN all partial closes would be below minimum size THEN the system SHALL fall back to single take profit behavior
5. WHEN a partial close order is placed THEN the system SHALL use the reduceOnly flag to prevent increasing position size

### Requirement 4

**User Story:** As a trader, I want to see which take profit levels have been hit in my trade history, so that I can analyze the effectiveness of the scaled exit strategy.

#### Acceptance Criteria

1. WHEN a partial take profit is executed THEN the system SHALL record the TP level number, percentage closed, and profit amount
2. WHEN viewing trade history THEN the system SHALL display all partial exits for a single trade as separate entries linked to the original trade
3. WHEN a trade completes THEN the system SHALL calculate total profit across all partial exits plus the final exit
4. WHEN displaying position status THEN the system SHALL show which TP levels have been hit and which remain
5. WHEN a position has partial exits THEN the system SHALL track the average exit price across all closes

### Requirement 5

**User Story:** As a trader, I want the backtest engine to support scaled take profit, so that I can evaluate the strategy's historical performance before using it live.

#### Acceptance Criteria

1. WHEN running a backtest with scaled take profit enabled THEN the system SHALL simulate partial closes at each TP level
2. WHEN a backtest position reaches a TP level THEN the system SHALL reduce the position size by the configured percentage
3. WHEN a backtest position's stop loss is moved THEN the system SHALL use the new stop loss level for subsequent candles
4. WHEN a backtest completes THEN the system SHALL report total profit including all partial exits
5. WHEN comparing backtest results THEN the system SHALL show metrics for both scaled and single take profit strategies

### Requirement 6

**User Story:** As a trader, I want the system to handle edge cases gracefully, so that the scaled take profit strategy doesn't cause unexpected behavior or losses.

#### Acceptance Criteria

1. WHEN a position gaps through multiple TP levels in one candle THEN the system SHALL execute all applicable partial closes at their respective levels
2. WHEN a partial close order fails THEN the system SHALL retry once and log the failure if it persists
3. WHEN the system restarts with open positions that have hit some TP levels THEN it SHALL restore the correct remaining position size and stop loss level
4. WHEN a position reverses before hitting any TP level THEN the system SHALL exit at the original stop loss
5. WHEN network issues prevent a partial close THEN the system SHALL maintain position integrity and not lose track of the remaining size

### Requirement 7

**User Story:** As a trader, I want clear logging of scaled take profit actions, so that I can debug issues and understand what the system is doing.

#### Acceptance Criteria

1. WHEN a TP level is hit THEN the system SHALL log the level number, close percentage, quantity closed, and new stop loss
2. WHEN a partial close order is placed THEN the system SHALL log the order details including symbol, side, quantity, and order ID
3. WHEN a partial close completes THEN the system SHALL log the fill price and realized profit
4. WHEN the stop loss is moved THEN the system SHALL log the old and new stop loss levels
5. WHEN scaled take profit is disabled due to configuration errors THEN the system SHALL log a clear error message explaining why

### Requirement 8

**User Story:** As a trader, I want the Streamlit dashboard to display scaled take profit information, so that I can monitor my positions and see which TP levels have been hit.

#### Acceptance Criteria

1. WHEN viewing an open position with scaled TP THEN the dashboard SHALL display all TP levels with their target prices and close percentages
2. WHEN a TP level has been hit THEN the dashboard SHALL mark it as completed with a checkmark
3. WHEN viewing position details THEN the dashboard SHALL show the original position size and current remaining size
4. WHEN viewing trade history THEN the dashboard SHALL group partial exits under the original trade entry
5. WHEN viewing analytics THEN the dashboard SHALL show average profit per TP level and hit rate for each level
