"""Property-based and unit tests for Portfolio Manager."""

import time
import pytest
from hypothesis import given, strategies as st, settings, assume
from src.config import Config
from src.models import Candle, Signal, Position, PortfolioMetrics
from src.portfolio_manager import PortfolioManager


# Helper function to generate candles
def generate_candles(count: int, base_price: float = 50000.0, volatility: float = 0.01) -> list:
    """Generate synthetic candle data for testing.
    
    Args:
        count: Number of candles to generate
        base_price: Base price for candles
        volatility: Price volatility factor
        
    Returns:
        List of Candle objects
    """
    import random
    candles = []
    current_price = base_price
    timestamp = int(time.time() * 1000) - (count * 3600000)  # Start count hours ago
    
    for i in range(count):
        # Add some random price movement
        price_change = current_price * volatility * (random.random() - 0.5) * 2
        current_price += price_change
        
        high = current_price * (1 + abs(random.random() * volatility))
        low = current_price * (1 - abs(random.random() * volatility))
        open_price = current_price + (random.random() - 0.5) * volatility * current_price
        close_price = current_price + (random.random() - 0.5) * volatility * current_price
        volume = random.uniform(100, 1000)
        
        candle = Candle(
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=volume
        )
        candles.append(candle)
        timestamp += 3600000  # 1 hour
    
    return candles


def generate_correlated_candles(
    base_candles: list, 
    correlation: float, 
    noise: float = 0.1
) -> list:
    """Generate candles correlated with base candles.
    
    Args:
        base_candles: Base candle series
        correlation: Desired correlation (-1 to 1)
        noise: Amount of random noise to add
        
    Returns:
        List of correlated candles
    """
    import random
    correlated = []
    
    for i, base_candle in enumerate(base_candles):
        # Calculate correlated price
        if i == 0:
            correlated_price = base_candle.close
        else:
            base_return = (base_candle.close - base_candles[i-1].close) / base_candles[i-1].close
            noise_factor = random.gauss(0, noise)
            correlated_return = correlation * base_return + noise_factor
            correlated_price = correlated[-1].close * (1 + correlated_return)
        
        # Create candle
        candle = Candle(
            timestamp=base_candle.timestamp,
            open=correlated_price * 0.999,
            high=correlated_price * 1.002,
            low=correlated_price * 0.998,
            close=correlated_price,
            volume=base_candle.volume * random.uniform(0.8, 1.2)
        )
        correlated.append(candle)
    
    return correlated


# Feature: advanced-trading-enhancements, Property 16: Correlation exposure limit
@given(
    wallet_balance=st.floats(min_value=1000.0, max_value=100000.0),
    confidence1=st.floats(min_value=0.5, max_value=1.0),
    confidence2=st.floats(min_value=0.5, max_value=1.0),
    correlation=st.floats(min_value=0.71, max_value=0.99)
)
@settings(max_examples=100)
def test_correlation_exposure_limit(wallet_balance, confidence1, confidence2, correlation):
    """For any two symbols with correlation >0.7, their combined portfolio 
    allocation must not exceed 50%.
    
    Property 16: Correlation exposure limit
    Validates: Requirements 5.3
    """
    # Create config
    config = Config()
    config.portfolio_symbols = ["BTCUSDT", "ETHUSDT"]
    config.portfolio_max_symbols = 2
    config.portfolio_correlation_threshold = 0.7
    config.portfolio_correlation_max_exposure = 0.5
    config.portfolio_max_single_allocation = 0.4
    
    # Create portfolio manager
    manager = PortfolioManager(config)
    
    # Directly set correlation in matrix (bypassing unreliable data generation)
    manager.correlation_matrix[("BTCUSDT", "ETHUSDT")] = correlation
    manager.correlation_matrix[("ETHUSDT", "BTCUSDT")] = correlation
    
    # Create signals with specified confidences
    signals = {
        "BTCUSDT": Signal(
            type="LONG_ENTRY",
            timestamp=int(time.time() * 1000),
            price=50000.0,
            indicators={'confidence': confidence1}
        ),
        "ETHUSDT": Signal(
            type="LONG_ENTRY",
            timestamp=int(time.time() * 1000),
            price=3000.0,
            indicators={'confidence': confidence2}
        )
    }
    
    # Calculate allocations
    allocations = manager.calculate_allocation(signals, wallet_balance)
    
    # Verify correlation limit is respected
    combined_allocation = allocations["BTCUSDT"] + allocations["ETHUSDT"]
    max_allowed = wallet_balance * config.portfolio_correlation_max_exposure
    
    assert combined_allocation <= max_allowed * 1.01, (  # Allow 1% tolerance for floating point
        f"Combined allocation {combined_allocation} exceeds limit {max_allowed} "
        f"for correlated symbols (correlation={correlation:.2f}, "
        f"BTCUSDT={allocations['BTCUSDT']}, ETHUSDT={allocations['ETHUSDT']})"
    )


# Feature: advanced-trading-enhancements, Property 17: Total risk invariant
@given(
    wallet_balance=st.floats(min_value=1000.0, max_value=100000.0),
    num_positions=st.integers(min_value=1, max_value=5),
    atr_multiplier=st.floats(min_value=1.0, max_value=3.0)
)
@settings(max_examples=100)
def test_total_risk_invariant(wallet_balance, num_positions, atr_multiplier):
    """For any portfolio state, the total portfolio risk must not exceed 
    the configured maximum risk.
    
    Property 17: Total risk invariant
    Validates: Requirements 5.4
    """
    # Create config
    config = Config()
    config.portfolio_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"]
    config.portfolio_max_symbols = 5
    config.portfolio_max_total_risk = 0.05  # 5%
    
    # Create portfolio manager
    manager = PortfolioManager(config)
    
    # Try to create positions with varying risk levels
    symbols = config.portfolio_symbols[:num_positions]
    
    for i, symbol in enumerate(symbols):
        entry_price = 50000.0 / (i + 1)  # Different prices
        quantity = 0.1 * (i + 1)
        stop_distance = entry_price * 0.02 * atr_multiplier  # 2% * multiplier
        
        position = Position(
            symbol=symbol,
            side="LONG",
            entry_price=entry_price,
            quantity=quantity,
            leverage=3,
            stop_loss=entry_price - stop_distance,
            trailing_stop=entry_price - stop_distance,
            entry_time=int(time.time() * 1000),
            unrealized_pnl=0.0
        )
        
        # Check if position can be added
        can_add = manager.can_add_position(symbol, position, wallet_balance)
        
        # If it can be added, add it
        if can_add:
            manager.update_position(symbol, position)
    
    # After all positions are added (or rejected), verify total risk is within limits
    metrics = manager.get_portfolio_metrics(wallet_balance)
    
    # Verify risk is within limits
    assert metrics.total_risk <= config.portfolio_max_total_risk, (
        f"Total portfolio risk {metrics.total_risk:.2%} exceeds maximum "
        f"{config.portfolio_max_total_risk:.2%}"
    )


# Feature: advanced-trading-enhancements, Property 18: Maximum single allocation
@given(
    wallet_balance=st.floats(min_value=1000.0, max_value=100000.0),
    confidence=st.floats(min_value=0.8, max_value=1.0),
    num_symbols=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=100)
def test_maximum_single_allocation(wallet_balance, confidence, num_symbols):
    """For any symbol allocation, even with high confidence signal, the 
    allocation must not exceed 40% of total capital.
    
    Property 18: Maximum single allocation
    Validates: Requirements 5.6
    """
    # Create config
    config = Config()
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"][:num_symbols]
    config.portfolio_symbols = symbols
    config.portfolio_max_symbols = num_symbols
    config.portfolio_max_single_allocation = 0.4
    
    # Create portfolio manager
    manager = PortfolioManager(config)
    
    # Generate price data for correlation matrix
    price_data = {}
    for symbol in symbols:
        price_data[symbol] = generate_candles(count=30, base_price=50000.0)
    
    manager.build_correlation_matrix(price_data)
    
    # Create signals with high confidence for all symbols
    signals = {}
    for symbol in symbols:
        signals[symbol] = Signal(
            type="LONG_ENTRY",
            timestamp=int(time.time() * 1000),
            price=50000.0,
            indicators={'confidence': confidence}
        )
    
    # Calculate allocations
    allocations = manager.calculate_allocation(signals, wallet_balance)
    
    # Verify no single allocation exceeds 40%
    max_allowed = wallet_balance * config.portfolio_max_single_allocation
    
    for symbol, allocation in allocations.items():
        assert allocation <= max_allowed * 1.01, (  # Allow 1% tolerance
            f"Allocation for {symbol} ({allocation}) exceeds maximum "
            f"{max_allowed} (40% of {wallet_balance})"
        )


# ===== UNIT TESTS =====

def test_portfolio_manager_initialization():
    """Test PortfolioManager initialization."""
    config = Config()
    config.portfolio_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    config.portfolio_max_symbols = 5
    
    manager = PortfolioManager(config)
    
    assert len(manager.symbols) == 3
    assert manager.symbols == ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    assert len(manager.positions) == 3
    assert all(pos is None for pos in manager.positions.values())


def test_correlation_calculation():
    """Test correlation calculation between two symbols."""
    config = Config()
    config.portfolio_symbols = ["BTCUSDT", "ETHUSDT"]
    
    manager = PortfolioManager(config)
    
    # Generate data
    base_candles = generate_candles(count=30, base_price=50000.0)
    correlated_candles = generate_correlated_candles(base_candles, correlation=0.9, noise=0.01)
    
    price_data = {
        "BTCUSDT": base_candles,
        "ETHUSDT": correlated_candles
    }
    
    correlation = manager.calculate_correlation("BTCUSDT", "ETHUSDT", price_data)
    
    # Should return a valid correlation value between -1 and 1
    assert -1.0 <= correlation <= 1.0
    # Should not be exactly 0 (since we generated correlated data)
    assert correlation != 0.0


def test_correlation_calculation_insufficient_data():
    """Test correlation calculation with insufficient data."""
    config = Config()
    config.portfolio_symbols = ["BTCUSDT", "ETHUSDT"]
    
    manager = PortfolioManager(config)
    
    # Generate insufficient data (< 30 candles)
    base_candles = generate_candles(count=10, base_price=50000.0)
    
    price_data = {
        "BTCUSDT": base_candles,
        "ETHUSDT": base_candles
    }
    
    correlation = manager.calculate_correlation("BTCUSDT", "ETHUSDT", price_data)
    
    # Should return 0.0 for insufficient data
    assert correlation == 0.0


def test_allocation_with_no_signals():
    """Test allocation calculation with no valid signals."""
    config = Config()
    config.portfolio_symbols = ["BTCUSDT", "ETHUSDT"]
    
    manager = PortfolioManager(config)
    
    # Empty signals
    signals = {}
    allocations = manager.calculate_allocation(signals, 10000.0)
    
    # Should return zero allocations
    assert all(alloc == 0.0 for alloc in allocations.values())


def test_allocation_proportional_to_confidence():
    """Test that allocation is proportional to signal confidence."""
    config = Config()
    config.portfolio_symbols = ["BTCUSDT", "ETHUSDT"]
    config.portfolio_max_single_allocation = 0.4
    
    manager = PortfolioManager(config)
    
    # Generate uncorrelated data
    price_data = {
        "BTCUSDT": generate_candles(count=30, base_price=50000.0),
        "ETHUSDT": generate_candles(count=30, base_price=3000.0)
    }
    manager.build_correlation_matrix(price_data)
    
    # Create signals with different confidences
    signals = {
        "BTCUSDT": Signal(
            type="LONG_ENTRY",
            timestamp=int(time.time() * 1000),
            price=50000.0,
            indicators={'confidence': 0.8}
        ),
        "ETHUSDT": Signal(
            type="LONG_ENTRY",
            timestamp=int(time.time() * 1000),
            price=3000.0,
            indicators={'confidence': 0.4}
        )
    }
    
    allocations = manager.calculate_allocation(signals, 10000.0)
    
    # Higher confidence should get more allocation
    assert allocations["BTCUSDT"] > allocations["ETHUSDT"]


def test_rebalance_interval():
    """Test that rebalancing respects the configured interval."""
    config = Config()
    config.portfolio_symbols = ["BTCUSDT"]
    config.portfolio_rebalance_interval = 3600  # 1 hour
    
    manager = PortfolioManager(config)
    
    signals = {
        "BTCUSDT": Signal(
            type="LONG_ENTRY",
            timestamp=int(time.time() * 1000),
            price=50000.0,
            indicators={'confidence': 0.8}
        )
    }
    
    # First rebalance should work
    result1 = manager.rebalance_portfolio(signals, 10000.0)
    assert len(result1) > 0
    
    # Immediate second rebalance should be skipped
    result2 = manager.rebalance_portfolio(signals, 10000.0)
    assert len(result2) == 0


def test_portfolio_metrics_calculation():
    """Test portfolio metrics calculation."""
    config = Config()
    config.portfolio_symbols = ["BTCUSDT", "ETHUSDT"]
    
    manager = PortfolioManager(config)
    
    # Add some positions
    position1 = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=50000.0,
        quantity=0.1,
        leverage=3,
        stop_loss=49000.0,
        trailing_stop=49000.0,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=100.0
    )
    
    position2 = Position(
        symbol="ETHUSDT",
        side="LONG",
        entry_price=3000.0,
        quantity=1.0,
        leverage=3,
        stop_loss=2940.0,
        trailing_stop=2940.0,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=50.0
    )
    
    manager.update_position("BTCUSDT", position1)
    manager.update_position("ETHUSDT", position2)
    
    # Add some realized PnL
    manager.update_pnl("BTCUSDT", 200.0)
    manager.update_pnl("ETHUSDT", -50.0)
    
    # Calculate metrics
    metrics = manager.get_portfolio_metrics(10000.0)
    
    assert metrics.total_value == 10000.0 + 100.0 + 50.0  # balance + unrealized
    assert metrics.total_pnl == 200.0 - 50.0 + 100.0 + 50.0  # realized + unrealized
    assert metrics.diversification_ratio == 1.0  # 2 active / 2 total
    assert metrics.total_risk > 0.0


def test_check_total_risk():
    """Test total risk checking."""
    config = Config()
    config.portfolio_symbols = ["BTCUSDT"]
    config.portfolio_max_total_risk = 0.05  # 5%
    
    manager = PortfolioManager(config)
    
    # Add position with low risk
    position = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=50000.0,
        quantity=0.01,  # Small position
        leverage=3,
        stop_loss=49000.0,
        trailing_stop=49000.0,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    manager.update_position("BTCUSDT", position)
    
    # Should be within risk limits
    assert manager.check_total_risk(10000.0) == True


def test_update_position():
    """Test position update."""
    config = Config()
    config.portfolio_symbols = ["BTCUSDT"]
    
    manager = PortfolioManager(config)
    
    position = Position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=50000.0,
        quantity=0.1,
        leverage=3,
        stop_loss=49000.0,
        trailing_stop=49000.0,
        entry_time=int(time.time() * 1000),
        unrealized_pnl=0.0
    )
    
    manager.update_position("BTCUSDT", position)
    
    assert manager.positions["BTCUSDT"] == position
    
    # Close position
    manager.update_position("BTCUSDT", None)
    assert manager.positions["BTCUSDT"] is None


def test_update_pnl():
    """Test PnL update."""
    config = Config()
    config.portfolio_symbols = ["BTCUSDT"]
    
    manager = PortfolioManager(config)
    
    assert manager.per_symbol_pnl["BTCUSDT"] == 0.0
    
    manager.update_pnl("BTCUSDT", 100.0)
    assert manager.per_symbol_pnl["BTCUSDT"] == 100.0
    
    manager.update_pnl("BTCUSDT", -50.0)
    assert manager.per_symbol_pnl["BTCUSDT"] == 50.0
