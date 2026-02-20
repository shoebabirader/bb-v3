"""Property-based and unit tests for Streamlit Chart Generator."""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from src.streamlit_charts import ChartGenerator
import plotly.graph_objects as go


# ===== PROPERTY-BASED TESTS =====

# Feature: streamlit-ui, Property 4: Chart Entry Markers
@given(
    num_candles=st.integers(min_value=10, max_value=200),
    num_positions=st.integers(min_value=1, max_value=10),
    base_price=st.floats(min_value=100.0, max_value=100000.0),
    side=st.sampled_from(['LONG', 'SHORT'])
)
@settings(deadline=None, max_examples=100)
def test_chart_entry_markers(num_candles, num_positions, base_price, side):
    """For any open positions, the price chart must include entry point markers 
    at the correct price and timestamp for each position.
    
    Property 4: Chart Entry Markers
    Validates: Requirements 4.2
    """
    # Generate candle data
    base_time = datetime(2026, 2, 1, 0, 0, 0)
    candles = []
    for i in range(num_candles):
        timestamp = base_time + timedelta(minutes=i * 15)
        candles.append({
            'timestamp': timestamp.isoformat(),
            'open': base_price + i,
            'high': base_price + i + 10,
            'low': base_price + i - 10,
            'close': base_price + i + 5,
            'volume': 1000.0
        })
    
    # Generate position data with entry times within candle range
    positions = []
    for i in range(num_positions):
        # Pick a random candle index for entry
        entry_idx = (i * num_candles) // num_positions
        entry_time = candles[entry_idx]['timestamp']
        entry_price = candles[entry_idx]['close']
        
        positions.append({
            'entry_time': entry_time,
            'entry_price': entry_price,
            'side': side,
            'symbol': 'BTCUSDT',
            'quantity': 0.1
        })
    
    # Create chart
    chart_gen = ChartGenerator()
    fig = chart_gen.create_price_chart(candles=candles, positions=positions)
    
    # Verify chart has data
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    
    # Count marker traces (should be one per position)
    marker_traces = [trace for trace in fig.data 
                     if hasattr(trace, 'mode') and trace.mode == 'markers']
    assert len(marker_traces) == num_positions, \
        f"Expected {num_positions} marker traces, got {len(marker_traces)}"
    
    # Verify each position has a corresponding marker
    for pos in positions:
        # Find marker trace for this position
        found_marker = False
        for trace in marker_traces:
            if (trace.x and len(trace.x) > 0 and 
                trace.y and len(trace.y) > 0):
                # Check if marker matches position
                if (str(trace.x[0]) == str(pos['entry_time']) and 
                    float(trace.y[0]) == float(pos['entry_price'])):
                    found_marker = True
                    
                    # Verify marker properties match side
                    if pos['side'] == 'LONG':
                        assert trace.marker.symbol == 'triangle-up'
                        assert trace.marker.color == 'green'
                    else:  # SHORT
                        assert trace.marker.symbol == 'triangle-down'
                        assert trace.marker.color == 'red'
                    break
        
        assert found_marker, \
            f"No marker found for position at {pos['entry_time']} with price {pos['entry_price']}"


# Feature: streamlit-ui, Property 5: Chart Candle Count
@given(
    num_candles=st.integers(min_value=1, max_value=500),
    base_price=st.floats(min_value=100.0, max_value=100000.0)
)
@settings(deadline=None, max_examples=100)
def test_chart_candle_count(num_candles, base_price):
    """For any chart update, the Dashboard must fetch and display exactly 
    the number of candles provided.
    
    Property 5: Chart Candle Count
    Validates: Requirements 4.5
    """
    # Generate candle data
    base_time = datetime(2026, 2, 1, 0, 0, 0)
    candles = []
    for i in range(num_candles):
        timestamp = base_time + timedelta(minutes=i * 15)
        candles.append({
            'timestamp': timestamp.isoformat(),
            'open': base_price + i,
            'high': base_price + i + 10,
            'low': base_price + i - 10,
            'close': base_price + i + 5,
            'volume': 1000.0
        })
    
    # Create chart
    chart_gen = ChartGenerator()
    fig = chart_gen.create_price_chart(candles=candles)
    
    # Verify chart has data
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    
    # Find the candlestick trace
    candlestick_trace = None
    for trace in fig.data:
        if isinstance(trace, go.Candlestick):
            candlestick_trace = trace
            break
    
    assert candlestick_trace is not None, "No candlestick trace found in chart"
    
    # Verify the number of candles matches input
    assert len(candlestick_trace.x) == num_candles, \
        f"Expected {num_candles} candles, got {len(candlestick_trace.x)}"
    assert len(candlestick_trace.open) == num_candles
    assert len(candlestick_trace.high) == num_candles
    assert len(candlestick_trace.low) == num_candles
    assert len(candlestick_trace.close) == num_candles


# ===== UNIT TESTS =====

class TestPriceChartGeneration:
    """Unit tests for price chart generation.
    
    Validates: Requirements 4.1, 4.2, 4.3
    """
    
    def test_create_price_chart_with_sample_candles(self):
        """Test creating price chart with sample candle data."""
        candles = [
            {
                'timestamp': '2026-02-01T00:00:00',
                'open': 50000.0,
                'high': 50500.0,
                'low': 49500.0,
                'close': 50200.0,
                'volume': 1000.0
            },
            {
                'timestamp': '2026-02-01T00:15:00',
                'open': 50200.0,
                'high': 50800.0,
                'low': 50000.0,
                'close': 50600.0,
                'volume': 1200.0
            },
            {
                'timestamp': '2026-02-01T00:30:00',
                'open': 50600.0,
                'high': 51000.0,
                'low': 50400.0,
                'close': 50900.0,
                'volume': 1100.0
            }
        ]
        
        chart_gen = ChartGenerator()
        fig = chart_gen.create_price_chart(candles=candles)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        
        # Find candlestick trace
        candlestick_trace = None
        for trace in fig.data:
            if isinstance(trace, go.Candlestick):
                candlestick_trace = trace
                break
        
        assert candlestick_trace is not None
        assert len(candlestick_trace.x) == 3
        assert candlestick_trace.open[0] == 50000.0
        assert candlestick_trace.close[2] == 50900.0
    
    def test_create_price_chart_with_empty_candles(self):
        """Test creating price chart with empty candle list."""
        chart_gen = ChartGenerator()
        fig = chart_gen.create_price_chart(candles=[])
        
        assert isinstance(fig, go.Figure)
        # Should have annotation for "No data available"
        assert len(fig.layout.annotations) > 0
    
    def test_create_price_chart_with_positions(self):
        """Test creating price chart with position markers."""
        candles = [
            {
                'timestamp': '2026-02-01T00:00:00',
                'open': 50000.0,
                'high': 50500.0,
                'low': 49500.0,
                'close': 50200.0,
                'volume': 1000.0
            },
            {
                'timestamp': '2026-02-01T00:15:00',
                'open': 50200.0,
                'high': 50800.0,
                'low': 50000.0,
                'close': 50600.0,
                'volume': 1200.0
            }
        ]
        
        positions = [
            {
                'entry_time': '2026-02-01T00:00:00',
                'entry_price': 50000.0,
                'side': 'LONG',
                'symbol': 'BTCUSDT'
            },
            {
                'entry_time': '2026-02-01T00:15:00',
                'entry_price': 50200.0,
                'side': 'SHORT',
                'symbol': 'ETHUSDT'
            }
        ]
        
        chart_gen = ChartGenerator()
        fig = chart_gen.create_price_chart(candles=candles, positions=positions)
        
        assert isinstance(fig, go.Figure)
        
        # Count marker traces
        marker_traces = [trace for trace in fig.data 
                         if hasattr(trace, 'mode') and trace.mode == 'markers']
        assert len(marker_traces) == 2
        
        # Verify LONG marker
        long_marker = marker_traces[0]
        assert long_marker.marker.symbol == 'triangle-up'
        assert long_marker.marker.color == 'green'
        
        # Verify SHORT marker
        short_marker = marker_traces[1]
        assert short_marker.marker.symbol == 'triangle-down'
        assert short_marker.marker.color == 'red'
    
    def test_create_price_chart_with_atr_bands(self):
        """Test creating price chart with ATR bands overlay."""
        candles = [
            {
                'timestamp': '2026-02-01T00:00:00',
                'open': 50000.0,
                'high': 50500.0,
                'low': 49500.0,
                'close': 50200.0,
                'volume': 1000.0
            },
            {
                'timestamp': '2026-02-01T00:15:00',
                'open': 50200.0,
                'high': 50800.0,
                'low': 50000.0,
                'close': 50600.0,
                'volume': 1200.0
            }
        ]
        
        atr_bands = {
            'timestamps': ['2026-02-01T00:00:00', '2026-02-01T00:15:00'],
            'upper': [51000.0, 51500.0],
            'lower': [49000.0, 49500.0]
        }
        
        chart_gen = ChartGenerator()
        fig = chart_gen.create_price_chart(candles=candles, atr_bands=atr_bands)
        
        assert isinstance(fig, go.Figure)
        
        # Should have candlestick + 2 ATR band traces
        assert len(fig.data) >= 3
        
        # Find ATR band traces
        atr_traces = [trace for trace in fig.data if 'ATR' in trace.name]
        assert len(atr_traces) == 2


class TestPnLChartGeneration:
    """Unit tests for PnL chart generation.
    
    Validates: Requirements 8.2
    """
    
    def test_create_pnl_chart_with_sample_trades(self):
        """Test creating PnL chart with sample trade data."""
        trades = [
            {
                'exit_time': '2026-02-01T00:00:00',
                'pnl': 100.0,
                'symbol': 'BTCUSDT'
            },
            {
                'exit_time': '2026-02-01T01:00:00',
                'pnl': -50.0,
                'symbol': 'ETHUSDT'
            },
            {
                'exit_time': '2026-02-01T02:00:00',
                'pnl': 200.0,
                'symbol': 'BTCUSDT'
            },
            {
                'exit_time': '2026-02-01T03:00:00',
                'pnl': 150.0,
                'symbol': 'ETHUSDT'
            }
        ]
        
        chart_gen = ChartGenerator()
        fig = chart_gen.create_pnl_chart(trades=trades)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        
        # Find the PnL trace
        pnl_trace = fig.data[0]
        assert len(pnl_trace.x) == 4
        assert len(pnl_trace.y) == 4
        
        # Verify cumulative PnL calculation
        assert pnl_trace.y[0] == 100.0
        assert pnl_trace.y[1] == 50.0  # 100 - 50
        assert pnl_trace.y[2] == 250.0  # 50 + 200
        assert pnl_trace.y[3] == 400.0  # 250 + 150
    
    def test_create_pnl_chart_with_empty_trades(self):
        """Test creating PnL chart with empty trade list."""
        chart_gen = ChartGenerator()
        fig = chart_gen.create_pnl_chart(trades=[])
        
        assert isinstance(fig, go.Figure)
        # Should have annotation for "No trade data available"
        assert len(fig.layout.annotations) > 0
    
    def test_create_pnl_chart_positive_final_pnl(self):
        """Test PnL chart with positive final PnL uses green color."""
        trades = [
            {'exit_time': '2026-02-01T00:00:00', 'pnl': 100.0},
            {'exit_time': '2026-02-01T01:00:00', 'pnl': 50.0},
            {'exit_time': '2026-02-01T02:00:00', 'pnl': 150.0}
        ]
        
        chart_gen = ChartGenerator()
        fig = chart_gen.create_pnl_chart(trades=trades)
        
        pnl_trace = fig.data[0]
        # Final PnL is 300.0 (positive), so line should be green
        assert pnl_trace.line.color == 'green'
    
    def test_create_pnl_chart_negative_final_pnl(self):
        """Test PnL chart with negative final PnL uses red color."""
        trades = [
            {'exit_time': '2026-02-01T00:00:00', 'pnl': -100.0},
            {'exit_time': '2026-02-01T01:00:00', 'pnl': -50.0},
            {'exit_time': '2026-02-01T02:00:00', 'pnl': -150.0}
        ]
        
        chart_gen = ChartGenerator()
        fig = chart_gen.create_pnl_chart(trades=trades)
        
        pnl_trace = fig.data[0]
        # Final PnL is -300.0 (negative), so line should be red
        assert pnl_trace.line.color == 'red'
    
    def test_create_pnl_chart_with_various_configurations(self):
        """Test PnL chart with various trade configurations."""
        # Test with single trade
        trades = [{'exit_time': '2026-02-01T00:00:00', 'pnl': 100.0}]
        chart_gen = ChartGenerator()
        fig = chart_gen.create_pnl_chart(trades=trades)
        assert len(fig.data[0].y) == 1
        assert fig.data[0].y[0] == 100.0
        
        # Test with many trades
        trades = [{'exit_time': f'2026-02-01T{i:02d}:00:00', 'pnl': 10.0} 
                  for i in range(24)]
        fig = chart_gen.create_pnl_chart(trades=trades)
        assert len(fig.data[0].y) == 24
        assert fig.data[0].y[-1] == 240.0  # 24 * 10.0
