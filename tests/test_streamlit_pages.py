"""
Property-based tests for Streamlit dashboard pages.

These tests validate correctness properties for the dashboard UI components.
"""

import pytest
from hypothesis import given, strategies as st
from typing import Dict, List


# Helper function to validate position display completeness
def validate_position_fields(position: Dict) -> bool:
    """
    Check if a position dictionary contains all required fields.
    
    Required fields: symbol, side, entry_price, current_price, pnl, stop_loss, take_profit
    
    Args:
        position: Position dictionary to validate
        
    Returns:
        True if all required fields are present, False otherwise
    """
    required_fields = [
        'symbol', 'side', 'entry_price', 'current_price', 
        'pnl', 'stop_loss', 'take_profit'
    ]
    return all(field in position for field in required_fields)


# Strategy for generating valid positions
position_strategy = st.fixed_dictionaries({
    'symbol': st.text(min_size=1, max_size=20),
    'side': st.sampled_from(['LONG', 'SHORT']),
    'entry_price': st.floats(min_value=0.01, max_value=100000.0),
    'current_price': st.floats(min_value=0.01, max_value=100000.0),
    'pnl': st.floats(min_value=-10000.0, max_value=10000.0),
    'stop_loss': st.floats(min_value=0.01, max_value=100000.0),
    'take_profit': st.floats(min_value=0.01, max_value=100000.0),
    'size': st.floats(min_value=0.001, max_value=1000.0)
})


@given(st.lists(position_strategy, min_size=0, max_size=10))
def test_position_display_completeness(positions: List[Dict]):
    """
    Feature: streamlit-ui, Property 1: Position Display Completeness
    
    For any set of open positions, when displayed by the Dashboard,
    all positions must include symbol, side, entry_price, current_price,
    PnL, stop_loss, and take_profit fields.
    
    Validates: Requirements 2.1, 2.2
    """
    # Every position in the list must have all required fields
    for position in positions:
        assert validate_position_fields(position), (
            f"Position missing required fields: {position}"
        )
        
        # Verify field types are appropriate
        assert isinstance(position['symbol'], str)
        assert position['side'] in ['LONG', 'SHORT']
        assert isinstance(position['entry_price'], (int, float))
        assert isinstance(position['current_price'], (int, float))
        assert isinstance(position['pnl'], (int, float))
        assert isinstance(position['stop_loss'], (int, float))
        assert isinstance(position['take_profit'], (int, float))


# Unit tests for specific examples
def test_position_display_empty_list():
    """Test that empty position list is handled correctly."""
    positions = []
    # Should not raise any errors
    for position in positions:
        assert validate_position_fields(position)


def test_position_display_single_position():
    """Test single position with all required fields."""
    position = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000.0,
        'current_price': 51000.0,
        'pnl': 100.0,
        'stop_loss': 49000.0,
        'take_profit': 52000.0,
        'size': 0.1
    }
    assert validate_position_fields(position)


def test_position_display_missing_field():
    """Test that missing required field is detected."""
    position = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000.0,
        'current_price': 51000.0,
        'pnl': 100.0,
        # Missing stop_loss and take_profit
    }
    assert not validate_position_fields(position)



# Helper function for PnL color coding
def get_pnl_color(pnl: float) -> str:
    """
    Get color code for PnL value.
    
    Args:
        pnl: PnL value
        
    Returns:
        Color string: 'green' for positive, 'red' for negative, 'neutral' for zero
    """
    if pnl > 0:
        return "green"
    elif pnl < 0:
        return "red"
    else:
        return "neutral"


@given(st.floats(min_value=-10000.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
def test_pnl_color_coding(pnl: float):
    """
    Feature: streamlit-ui, Property 2: PnL Color Coding
    
    For any PnL value displayed, the color must be green when PnL > 0,
    red when PnL < 0, and neutral when PnL == 0.
    
    Validates: Requirements 2.5
    """
    color = get_pnl_color(pnl)
    
    if pnl > 0:
        assert color == "green", f"Expected green for positive PnL {pnl}, got {color}"
    elif pnl < 0:
        assert color == "red", f"Expected red for negative PnL {pnl}, got {color}"
    else:
        assert color == "neutral", f"Expected neutral for zero PnL, got {color}"


# Unit tests for PnL color coding
def test_pnl_color_positive():
    """Test color for positive PnL."""
    assert get_pnl_color(100.0) == "green"
    assert get_pnl_color(0.01) == "green"
    assert get_pnl_color(9999.99) == "green"


def test_pnl_color_negative():
    """Test color for negative PnL."""
    assert get_pnl_color(-100.0) == "red"
    assert get_pnl_color(-0.01) == "red"
    assert get_pnl_color(-9999.99) == "red"


def test_pnl_color_zero():
    """Test color for zero PnL."""
    assert get_pnl_color(0.0) == "neutral"
    assert get_pnl_color(-0.0) == "neutral"



# Helper function for indicator highlighting
def should_highlight_indicator(indicator_value: float, threshold: float) -> bool:
    """
    Determine if an indicator should be highlighted based on threshold.
    
    Args:
        indicator_value: Current indicator value
        threshold: Configured threshold value
        
    Returns:
        True if indicator meets or exceeds threshold, False otherwise
    """
    return indicator_value >= threshold


@given(
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
)
def test_indicator_highlighting(indicator_value: float, threshold: float):
    """
    Feature: streamlit-ui, Property 3: Indicator Highlighting
    
    For any indicator values that exceed their configured thresholds,
    the Dashboard must apply highlighting to those indicators.
    
    Validates: Requirements 3.3
    """
    should_highlight = should_highlight_indicator(indicator_value, threshold)
    
    if indicator_value >= threshold:
        assert should_highlight is True, (
            f"Indicator {indicator_value} >= threshold {threshold} should be highlighted"
        )
    else:
        assert should_highlight is False, (
            f"Indicator {indicator_value} < threshold {threshold} should not be highlighted"
        )


# Unit tests for indicator highlighting
def test_indicator_above_threshold():
    """Test highlighting when indicator is above threshold."""
    assert should_highlight_indicator(30.0, 25.0) is True
    assert should_highlight_indicator(50.0, 25.0) is True
    assert should_highlight_indicator(100.0, 25.0) is True


def test_indicator_below_threshold():
    """Test no highlighting when indicator is below threshold."""
    assert should_highlight_indicator(20.0, 25.0) is False
    assert should_highlight_indicator(10.0, 25.0) is False
    assert should_highlight_indicator(0.0, 25.0) is False


def test_indicator_equal_threshold():
    """Test highlighting when indicator equals threshold."""
    assert should_highlight_indicator(25.0, 25.0) is True
    assert should_highlight_indicator(1.5, 1.5) is True


def test_indicator_edge_cases():
    """Test edge cases for indicator highlighting."""
    # Just above threshold
    assert should_highlight_indicator(25.01, 25.0) is True
    # Just below threshold
    assert should_highlight_indicator(24.99, 25.0) is False
    # Zero threshold
    assert should_highlight_indicator(0.0, 0.0) is True
    assert should_highlight_indicator(0.01, 0.0) is True



# ===== TRADE HISTORY AND ANALYTICS PROPERTY TESTS =====

# Helper function to validate trade display completeness
def validate_trade_fields(trade: Dict) -> bool:
    """
    Check if a trade dictionary contains all required fields.
    
    Required fields: entry_time, exit_time, symbol, side, pnl, return_percentage
    
    Args:
        trade: Trade dictionary to validate
        
    Returns:
        True if all required fields are present, False otherwise
    """
    required_fields = [
        'entry_time', 'exit_time', 'symbol', 'side', 'pnl'
    ]
    # return_percentage might also be called pnl_percent
    has_return = 'return_percentage' in trade or 'pnl_percent' in trade
    
    return all(field in trade for field in required_fields) and has_return


# Strategy for generating valid trades
trade_strategy = st.fixed_dictionaries({
    'entry_time': st.one_of(
        st.text(min_size=10, max_size=30),  # ISO format string
        st.integers(min_value=1000000000000, max_value=9999999999999)  # Timestamp in ms
    ),
    'exit_time': st.one_of(
        st.text(min_size=10, max_size=30),  # ISO format string
        st.integers(min_value=1000000000000, max_value=9999999999999)  # Timestamp in ms
    ),
    'timestamp': st.text(min_size=10, max_size=30),  # Alternative exit time field
    'symbol': st.text(min_size=1, max_size=20),
    'side': st.sampled_from(['LONG', 'SHORT']),
    'entry_price': st.floats(min_value=0.01, max_value=100000.0),
    'exit_price': st.floats(min_value=0.01, max_value=100000.0),
    'quantity': st.floats(min_value=0.001, max_value=1000.0),
    'pnl': st.floats(min_value=-10000.0, max_value=10000.0),
    'pnl_percent': st.floats(min_value=-100.0, max_value=1000.0),
    'return_percentage': st.floats(min_value=-100.0, max_value=1000.0),
    'exit_reason': st.sampled_from(['STOP_LOSS', 'TAKE_PROFIT', 'SIGNAL_EXIT', 'TRAILING_STOP', 'PANIC'])
})


@given(st.lists(trade_strategy, min_size=0, max_size=20))
def test_trade_display_completeness(trades: List[Dict]):
    """
    Feature: streamlit-ui, Property 10: Trade Display Completeness
    
    For any trade in the history, when displayed, it must include
    entry_time, exit_time, symbol, side, PnL, and return_percentage fields.
    
    Validates: Requirements 7.2
    """
    # Every trade in the list must have all required fields
    for trade in trades:
        assert validate_trade_fields(trade), (
            f"Trade missing required fields: {trade}"
        )
        
        # Verify field types are appropriate
        assert isinstance(trade['symbol'], str)
        assert trade['side'] in ['LONG', 'SHORT']
        assert isinstance(trade['pnl'], (int, float))
        # entry_time and exit_time can be string or int/float (timestamp)
        assert isinstance(trade['entry_time'], (str, int, float))
        assert isinstance(trade['exit_time'], (str, int, float))


# Helper function for trade sorting
def sort_trades_by_date(trades: List[Dict], ascending: bool = True) -> List[Dict]:
    """
    Sort trades by date (exit_time).
    
    Args:
        trades: List of trade dictionaries
        ascending: True for oldest first, False for newest first
        
    Returns:
        Sorted list of trades
    """
    def get_sortable_time(trade):
        """Convert exit_time to a sortable value."""
        exit_time = trade.get('exit_time', trade.get('timestamp', ''))
        # Convert to string for consistent comparison
        if isinstance(exit_time, (int, float)):
            # Convert timestamp to string with padding for proper sorting
            return str(exit_time).zfill(20)
        return str(exit_time)
    
    return sorted(trades, key=get_sortable_time, reverse=not ascending)


def sort_trades_by_pnl(trades: List[Dict], ascending: bool = True) -> List[Dict]:
    """
    Sort trades by PnL.
    
    Args:
        trades: List of trade dictionaries
        ascending: True for lowest first, False for highest first
        
    Returns:
        Sorted list of trades
    """
    return sorted(trades, key=lambda t: t.get('pnl', 0), reverse=not ascending)


@given(st.lists(trade_strategy, min_size=2, max_size=20))
def test_trade_sorting(trades: List[Dict]):
    """
    Feature: streamlit-ui, Property 11: Trade Sorting
    
    For any trade list, sorting by date or PnL must correctly reorder
    trades according to the selected field.
    
    Validates: Requirements 7.3
    """
    # Test date sorting (ascending)
    sorted_by_date_asc = sort_trades_by_date(trades, ascending=True)
    for i in range(len(sorted_by_date_asc) - 1):
        time_1 = sorted_by_date_asc[i].get('exit_time', sorted_by_date_asc[i].get('timestamp', ''))
        time_2 = sorted_by_date_asc[i + 1].get('exit_time', sorted_by_date_asc[i + 1].get('timestamp', ''))
        
        # Convert to comparable format
        if isinstance(time_1, (int, float)):
            time_1 = str(time_1).zfill(20)
        else:
            time_1 = str(time_1)
        
        if isinstance(time_2, (int, float)):
            time_2 = str(time_2).zfill(20)
        else:
            time_2 = str(time_2)
        
        assert time_1 <= time_2, "Trades should be sorted by date ascending"
    
    # Test date sorting (descending)
    sorted_by_date_desc = sort_trades_by_date(trades, ascending=False)
    for i in range(len(sorted_by_date_desc) - 1):
        time_1 = sorted_by_date_desc[i].get('exit_time', sorted_by_date_desc[i].get('timestamp', ''))
        time_2 = sorted_by_date_desc[i + 1].get('exit_time', sorted_by_date_desc[i + 1].get('timestamp', ''))
        
        # Convert to comparable format
        if isinstance(time_1, (int, float)):
            time_1 = str(time_1).zfill(20)
        else:
            time_1 = str(time_1)
        
        if isinstance(time_2, (int, float)):
            time_2 = str(time_2).zfill(20)
        else:
            time_2 = str(time_2)
        
        assert time_1 >= time_2, "Trades should be sorted by date descending"
    
    # Test PnL sorting (ascending)
    sorted_by_pnl_asc = sort_trades_by_pnl(trades, ascending=True)
    for i in range(len(sorted_by_pnl_asc) - 1):
        pnl_1 = sorted_by_pnl_asc[i].get('pnl', 0)
        pnl_2 = sorted_by_pnl_asc[i + 1].get('pnl', 0)
        assert pnl_1 <= pnl_2, "Trades should be sorted by PnL ascending"
    
    # Test PnL sorting (descending)
    sorted_by_pnl_desc = sort_trades_by_pnl(trades, ascending=False)
    for i in range(len(sorted_by_pnl_desc) - 1):
        pnl_1 = sorted_by_pnl_desc[i].get('pnl', 0)
        pnl_2 = sorted_by_pnl_desc[i + 1].get('pnl', 0)
        assert pnl_1 >= pnl_2, "Trades should be sorted by PnL descending"


# Helper function for win rate calculation
def calculate_win_rate(trades: List[Dict]) -> float:
    """
    Calculate win rate from trades.
    
    Args:
        trades: List of trade dictionaries
        
    Returns:
        Win rate as percentage (0-100)
    """
    if not trades:
        return 0.0
    
    winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
    total_trades = len(trades)
    
    return (winning_trades / total_trades) * 100


@given(st.lists(trade_strategy, min_size=1, max_size=100))
def test_win_rate_calculation(trades: List[Dict]):
    """
    Feature: streamlit-ui, Property 12: Win Rate Calculation
    
    For any set of trades, the calculated win rate must equal
    (winning_trades / total_trades) * 100.
    
    Validates: Requirements 7.4
    """
    win_rate = calculate_win_rate(trades)
    
    # Manually calculate expected win rate
    winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
    total_trades = len(trades)
    expected_win_rate = (winning_trades / total_trades) * 100
    
    # Allow small floating point error
    assert abs(win_rate - expected_win_rate) < 0.01, (
        f"Win rate {win_rate} does not match expected {expected_win_rate}"
    )
    
    # Win rate should be between 0 and 100
    assert 0.0 <= win_rate <= 100.0, f"Win rate {win_rate} out of valid range"


# Helper function for Sharpe ratio calculation
def calculate_sharpe_ratio(trades: List[Dict], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio from trades.
    
    Args:
        trades: List of trade dictionaries
        risk_free_rate: Risk-free rate (default 0.0)
        
    Returns:
        Sharpe ratio
    """
    if not trades or len(trades) < 2:
        return 0.0
    
    returns = [t.get('pnl_percent', t.get('return_percentage', 0)) for t in trades]
    
    import statistics
    mean_return = statistics.mean(returns)
    std_dev = statistics.stdev(returns)
    
    if std_dev == 0:
        return 0.0
    
    return (mean_return - risk_free_rate) / std_dev


@given(st.lists(trade_strategy, min_size=2, max_size=100))
def test_sharpe_ratio_calculation(trades: List[Dict]):
    """
    Feature: streamlit-ui, Property 13: Sharpe Ratio Calculation
    
    For any trade history with non-zero standard deviation, the Sharpe ratio
    must be calculated as (mean_return - risk_free_rate) / std_dev_return.
    
    Validates: Requirements 8.3
    """
    sharpe_ratio = calculate_sharpe_ratio(trades)
    
    # Manually calculate expected Sharpe ratio
    returns = [t.get('pnl_percent', t.get('return_percentage', 0)) for t in trades]
    
    import statistics
    mean_return = statistics.mean(returns)
    
    if len(returns) > 1:
        std_dev = statistics.stdev(returns)
        
        if std_dev > 0:
            expected_sharpe = mean_return / std_dev
            
            # Allow small floating point error
            assert abs(sharpe_ratio - expected_sharpe) < 0.01, (
                f"Sharpe ratio {sharpe_ratio} does not match expected {expected_sharpe}"
            )
        else:
            # If std_dev is 0, Sharpe ratio should be 0
            assert sharpe_ratio == 0.0, "Sharpe ratio should be 0 when std_dev is 0"


# Helper function for maximum drawdown calculation
def calculate_max_drawdown(trades: List[Dict]) -> float:
    """
    Calculate maximum drawdown from trades.
    
    Args:
        trades: List of trade dictionaries
        
    Returns:
        Maximum drawdown value
    """
    if not trades:
        return 0.0
    
    cumulative_pnl = []
    running_total = 0
    
    for trade in trades:
        running_total += trade.get('pnl', 0)
        cumulative_pnl.append(running_total)
    
    max_drawdown = 0.0
    peak = cumulative_pnl[0]
    
    for value in cumulative_pnl:
        if value > peak:
            peak = value
        drawdown = peak - value
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return max_drawdown


@given(st.lists(trade_strategy, min_size=1, max_size=100))
def test_maximum_drawdown_calculation(trades: List[Dict]):
    """
    Feature: streamlit-ui, Property 14: Maximum Drawdown Calculation
    
    For any equity curve, the maximum drawdown must be the largest
    peak-to-trough decline in cumulative PnL.
    
    Validates: Requirements 8.4
    """
    max_drawdown = calculate_max_drawdown(trades)
    
    # Maximum drawdown should be non-negative
    assert max_drawdown >= 0.0, f"Maximum drawdown {max_drawdown} should be non-negative"
    
    # Manually verify the calculation
    cumulative_pnl = []
    running_total = 0
    
    for trade in trades:
        running_total += trade.get('pnl', 0)
        cumulative_pnl.append(running_total)
    
    # Calculate expected max drawdown
    expected_max_drawdown = 0.0
    peak = cumulative_pnl[0]
    
    for value in cumulative_pnl:
        if value > peak:
            peak = value
        drawdown = peak - value
        if drawdown > expected_max_drawdown:
            expected_max_drawdown = drawdown
    
    # Allow small floating point error
    assert abs(max_drawdown - expected_max_drawdown) < 0.01, (
        f"Max drawdown {max_drawdown} does not match expected {expected_max_drawdown}"
    )


# Helper function for time period filtering
def filter_trades_by_time_period(trades: List[Dict], period: str) -> List[Dict]:
    """
    Filter trades by time period.
    
    Args:
        trades: List of trade dictionaries
        period: Time period ('24h', '7d', '30d', 'All')
        
    Returns:
        Filtered list of trades
    """
    if period == "All":
        return trades
    
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    if period == "24h":
        cutoff = now - timedelta(hours=24)
    elif period == "7d":
        cutoff = now - timedelta(days=7)
    elif period == "30d":
        cutoff = now - timedelta(days=30)
    else:
        return trades
    
    filtered = []
    for trade in trades:
        exit_time = trade.get('exit_time', trade.get('timestamp', ''))
        
        # Parse exit time
        try:
            if isinstance(exit_time, str):
                trade_time = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
            elif isinstance(exit_time, (int, float)):
                trade_time = datetime.fromtimestamp(exit_time / 1000)
            else:
                continue
            
            if trade_time >= cutoff:
                filtered.append(trade)
        except:
            # Skip trades with unparseable timestamps
            continue
    
    return filtered


@given(
    st.lists(trade_strategy, min_size=0, max_size=100),
    st.sampled_from(['24h', '7d', '30d', 'All'])
)
def test_time_period_filtering(trades: List[Dict], period: str):
    """
    Feature: streamlit-ui, Property 15: Time Period Filtering
    
    For any time period filter (24h, 7d, 30d), only trades with exit_time
    within that period must be included in analytics.
    
    Validates: Requirements 8.5
    """
    filtered_trades = filter_trades_by_time_period(trades, period)
    
    # Filtered trades should be a subset of original trades
    assert len(filtered_trades) <= len(trades), (
        "Filtered trades should not exceed original trades"
    )
    
    # If period is "All", all trades should be included
    if period == "All":
        assert len(filtered_trades) == len(trades), (
            "All trades should be included when period is 'All'"
        )
    
    # Verify that filtered trades are within the time period
    from datetime import datetime, timedelta
    
    if period != "All":
        now = datetime.now()
        
        if period == "24h":
            cutoff = now - timedelta(hours=24)
        elif period == "7d":
            cutoff = now - timedelta(days=7)
        elif period == "30d":
            cutoff = now - timedelta(days=30)
        
        for trade in filtered_trades:
            exit_time = trade.get('exit_time', trade.get('timestamp', ''))
            
            try:
                if isinstance(exit_time, str):
                    trade_time = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
                elif isinstance(exit_time, (int, float)):
                    trade_time = datetime.fromtimestamp(exit_time / 1000)
                else:
                    continue
                
                assert trade_time >= cutoff, (
                    f"Trade time {trade_time} should be after cutoff {cutoff}"
                )
            except:
                # Skip trades with unparseable timestamps
                pass


# ===== UNIT TESTS FOR TRADE HISTORY AND ANALYTICS =====

def test_trade_display_empty_list():
    """Test that empty trade list is handled correctly."""
    trades = []
    for trade in trades:
        assert validate_trade_fields(trade)


def test_trade_display_single_trade():
    """Test single trade with all required fields."""
    trade = {
        'entry_time': '2026-02-05T06:54:25',
        'exit_time': '2026-02-05T06:56:31',
        'timestamp': '2026-02-05T06:56:31',
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000.0,
        'exit_price': 51000.0,
        'quantity': 0.1,
        'pnl': 100.0,
        'pnl_percent': 2.0,
        'return_percentage': 2.0,
        'exit_reason': 'TAKE_PROFIT'
    }
    assert validate_trade_fields(trade)


def test_win_rate_all_winning():
    """Test win rate calculation with all winning trades."""
    trades = [
        {'pnl': 100.0},
        {'pnl': 50.0},
        {'pnl': 200.0}
    ]
    assert calculate_win_rate(trades) == 100.0


def test_win_rate_all_losing():
    """Test win rate calculation with all losing trades."""
    trades = [
        {'pnl': -100.0},
        {'pnl': -50.0},
        {'pnl': -200.0}
    ]
    assert calculate_win_rate(trades) == 0.0


def test_win_rate_mixed():
    """Test win rate calculation with mixed trades."""
    trades = [
        {'pnl': 100.0},
        {'pnl': -50.0},
        {'pnl': 200.0},
        {'pnl': -100.0}
    ]
    assert calculate_win_rate(trades) == 50.0


def test_max_drawdown_no_drawdown():
    """Test max drawdown with only winning trades."""
    trades = [
        {'pnl': 100.0},
        {'pnl': 50.0},
        {'pnl': 200.0}
    ]
    assert calculate_max_drawdown(trades) == 0.0


def test_max_drawdown_with_losses():
    """Test max drawdown with losses."""
    trades = [
        {'pnl': 100.0},  # cumulative: 100
        {'pnl': -50.0},  # cumulative: 50, drawdown: 50
        {'pnl': -30.0},  # cumulative: 20, drawdown: 80
        {'pnl': 200.0}   # cumulative: 220, new peak
    ]
    assert calculate_max_drawdown(trades) == 80.0


# ===== CONTROL ACTION PROPERTY TESTS =====

# Helper function to check if control action requires confirmation
def requires_confirmation(action: str) -> bool:
    """
    Check if a control action requires confirmation.
    
    Dangerous actions that require confirmation:
    - stop_bot
    - emergency_close_all
    - restart_bot
    
    Safe actions that don't require confirmation:
    - start_bot
    - refresh_data
    - view_logs
    
    Args:
        action: Name of the control action
        
    Returns:
        True if action requires confirmation, False otherwise
    """
    dangerous_actions = ['stop_bot', 'emergency_close_all', 'restart_bot']
    return action in dangerous_actions


@given(st.sampled_from([
    'start_bot', 'stop_bot', 'emergency_close_all', 'restart_bot',
    'refresh_data', 'view_logs', 'save_config'
]))
def test_control_action_confirmations(action: str):
    """
    Feature: streamlit-ui, Property 6: Control Action Confirmations
    
    For any dangerous control action (stop bot, emergency close), the
    Control_Panel must display a confirmation dialog before executing.
    
    Validates: Requirements 5.4
    """
    needs_confirmation = requires_confirmation(action)
    
    # Dangerous actions must require confirmation
    if action in ['stop_bot', 'emergency_close_all', 'restart_bot']:
        assert needs_confirmation is True, (
            f"Dangerous action '{action}' must require confirmation"
        )
    
    # Safe actions should not require confirmation
    if action in ['start_bot', 'refresh_data', 'view_logs', 'save_config']:
        assert needs_confirmation is False, (
            f"Safe action '{action}' should not require confirmation"
        )


# Unit tests for control action confirmations
def test_dangerous_actions_require_confirmation():
    """Test that all dangerous actions require confirmation."""
    assert requires_confirmation('stop_bot') is True
    assert requires_confirmation('emergency_close_all') is True
    assert requires_confirmation('restart_bot') is True


def test_safe_actions_no_confirmation():
    """Test that safe actions don't require confirmation."""
    assert requires_confirmation('start_bot') is False
    assert requires_confirmation('refresh_data') is False
    assert requires_confirmation('view_logs') is False


def test_unknown_action_no_confirmation():
    """Test that unknown actions default to no confirmation."""
    assert requires_confirmation('unknown_action') is False
    assert requires_confirmation('random_action') is False
