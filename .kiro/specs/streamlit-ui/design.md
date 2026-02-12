# Design Document: Streamlit Trading Dashboard

## Overview

The Streamlit Trading Dashboard is a web-based user interface for monitoring and controlling the Binance futures trading bot. It provides real-time visualization, bot control, configuration management, and performance analytics through an intuitive browser-based interface.

The dashboard runs as a separate process from the trading bot, reading shared data files (config.json, binance_results.json, log files) to display current state. This architecture ensures the dashboard doesn't interfere with bot operations while providing comprehensive monitoring capabilities.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   UI Layer   │  │ Data Provider│  │   Controls   │     │
│  │  (Pages)     │←─│   (Reader)   │  │  (Actions)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓ ↑
                    ┌───────────────┐
                    │  Shared Files │
                    │ - config.json │
                    │ - results.json│
                    │ - logs/*.log  │
                    └───────────────┘
                            ↓ ↑
┌─────────────────────────────────────────────────────────────┐
│                      Trading Bot                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Strategy   │  │ Risk Manager │  │Order Executor│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Dashboard → Files**: Dashboard reads config, results, and logs
2. **Dashboard → Bot**: Control actions (start/stop) via subprocess management
3. **Bot → Files**: Bot writes results, logs, and updates config
4. **Files → Dashboard**: Dashboard auto-refreshes to show latest data

## Components and Interfaces

### 1. Main Dashboard (streamlit_app.py)

The entry point for the Streamlit application. Manages page routing, layout, and auto-refresh.

```python
def main():
    """Main dashboard entry point."""
    st.set_page_config(
        page_title="Trading Bot Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Auto-refresh every 5 seconds
    st_autorefresh(interval=5000, key="datarefresh")
    
    # Sidebar navigation
    page = st.sidebar.selectbox("Navigation", [
        "Dashboard", "Positions", "Trade History", 
        "Analytics", "Settings", "Controls"
    ])
    
    # Route to appropriate page
    if page == "Dashboard":
        show_dashboard_page()
    elif page == "Positions":
        show_positions_page()
    # ... etc
```

### 2. Data Provider (src/streamlit_data_provider.py)

Reads bot state from files with caching to avoid excessive I/O.

```python
class StreamlitDataProvider:
    """Provides data to Streamlit dashboard by reading bot files."""
    
    def __init__(self, config_path: str = "config/config.json",
                 results_path: str = "binance_results.json",
                 logs_dir: str = "logs"):
        self.config_path = config_path
        self.results_path = results_path
        self.logs_dir = logs_dir
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 5  # seconds
    
    def get_config(self) -> Dict:
        """Load configuration from config.json."""
        return self._read_cached_json(self.config_path, "config")
    
    def get_bot_status(self) -> Dict:
        """Get current bot status (running/stopped, last update)."""
        # Check if main.py process is running
        is_running = self._is_bot_process_running()
        last_update = self._get_last_log_timestamp()
        
        return {
            "is_running": is_running,
            "last_update": last_update,
            "status": "Running" if is_running else "Stopped"
        }
    
    def get_balance_and_pnl(self) -> Dict:
        """Get current balance and total PnL from results file."""
        results = self._read_cached_json(self.results_path, "results")
        return {
            "balance": results.get("balance", 0.0),
            "total_pnl": results.get("total_pnl", 0.0),
            "total_pnl_percent": results.get("total_pnl_percent", 0.0)
        }
    
    def get_open_positions(self) -> List[Dict]:
        """Get list of open positions."""
        results = self._read_cached_json(self.results_path, "results")
        return results.get("open_positions", [])
    
    def get_trade_history(self, limit: int = 20) -> List[Dict]:
        """Get recent completed trades from log files."""
        trades = self._parse_trade_logs()
        return trades[-limit:] if trades else []
    
    def get_market_data(self) -> Dict:
        """Get current price and indicator values."""
        # Read from latest log entry or results file
        results = self._read_cached_json(self.results_path, "results")
        return {
            "current_price": results.get("current_price", 0.0),
            "adx": results.get("adx", 0.0),
            "rvol": results.get("rvol", 0.0),
            "atr": results.get("atr", 0.0),
            "signal": results.get("signal", "NONE")
        }
    
    def _read_cached_json(self, filepath: str, cache_key: str) -> Dict:
        """Read JSON file with caching."""
        now = time.time()
        
        # Check cache
        if cache_key in self._cache:
            cache_age = now - self._cache_timestamps.get(cache_key, 0)
            if cache_age < self._cache_ttl:
                return self._cache[cache_key]
        
        # Read file
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            self._cache[cache_key] = data
            self._cache_timestamps[cache_key] = now
            return data
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
    
    def _is_bot_process_running(self) -> bool:
        """Check if bot process is running."""
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'python' in cmdline[0].lower() and 'main.py' in ' '.join(cmdline):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    def _get_last_log_timestamp(self) -> Optional[datetime]:
        """Get timestamp of most recent log entry."""
        # Parse latest log file for most recent timestamp
        # Implementation details...
        pass
    
    def _parse_trade_logs(self) -> List[Dict]:
        """Parse trade history from log files."""
        # Implementation details...
        pass
```

### 3. Bot Controller (src/streamlit_bot_controller.py)

Manages bot process lifecycle (start/stop/restart).

```python
class BotController:
    """Controls the trading bot process."""
    
    def __init__(self):
        self.bot_script = "main.py"
        self.process = None
    
    def start_bot(self) -> Tuple[bool, str]:
        """Start the trading bot process."""
        if self._is_running():
            return False, "Bot is already running"
        
        try:
            self.process = subprocess.Popen(
                [sys.executable, self.bot_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(2)  # Wait for startup
            
            if self.process.poll() is None:
                return True, "Bot started successfully"
            else:
                return False, "Bot failed to start"
        except Exception as e:
            return False, f"Error starting bot: {str(e)}"
    
    def stop_bot(self) -> Tuple[bool, str]:
        """Stop the trading bot process gracefully."""
        if not self._is_running():
            return False, "Bot is not running"
        
        try:
            # Find and terminate the process
            for proc in psutil.process_iter(['name', 'cmdline']):
                cmdline = proc.info['cmdline']
                if cmdline and 'python' in cmdline[0].lower() and 'main.py' in ' '.join(cmdline):
                    proc.terminate()
                    proc.wait(timeout=10)
                    return True, "Bot stopped successfully"
            
            return False, "Bot process not found"
        except Exception as e:
            return False, f"Error stopping bot: {str(e)}"
    
    def emergency_close_all(self) -> Tuple[bool, str]:
        """Close all open positions immediately."""
        # This would call the bot's emergency close function
        # or directly interact with Binance API
        pass
    
    def _is_running(self) -> bool:
        """Check if bot is currently running."""
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'python' in cmdline[0].lower() and 'main.py' in ' '.join(cmdline):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
```

### 4. Config Editor (src/streamlit_config_editor.py)

Provides UI for editing configuration with validation.

```python
class ConfigEditor:
    """Manages configuration editing with validation."""
    
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = config_path
    
    def load_config(self) -> Dict:
        """Load current configuration."""
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def save_config(self, config: Dict) -> Tuple[bool, str]:
        """Save configuration after validation."""
        # Validate config
        is_valid, error_msg = self.validate_config(config)
        if not is_valid:
            return False, error_msg
        
        # Save to file
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True, "Configuration saved successfully"
        except Exception as e:
            return False, f"Error saving config: {str(e)}"
    
    def validate_config(self, config: Dict) -> Tuple[bool, str]:
        """Validate configuration parameters."""
        errors = []
        
        # Validate risk_per_trade
        if config.get("risk_per_trade", 0) <= 0 or config.get("risk_per_trade", 0) > 1.0:
            errors.append("risk_per_trade must be between 0 and 1.0")
        
        # Validate leverage
        if config.get("leverage", 0) < 1 or config.get("leverage", 0) > 125:
            errors.append("leverage must be between 1 and 125")
        
        # Validate ADX threshold
        if config.get("adx_threshold", 0) < 0 or config.get("adx_threshold", 0) > 100:
            errors.append("adx_threshold must be between 0 and 100")
        
        # ... more validations
        
        if errors:
            return False, "; ".join(errors)
        return True, ""
```

### 5. Chart Generator (src/streamlit_charts.py)

Creates interactive charts using Plotly.

```python
class ChartGenerator:
    """Generates charts for the dashboard."""
    
    def create_price_chart(self, candles: List[Dict], 
                          positions: List[Dict] = None,
                          atr_bands: Dict = None) -> go.Figure:
        """Create candlestick chart with overlays."""
        fig = go.Figure()
        
        # Add candlesticks
        fig.add_trace(go.Candlestick(
            x=[c['timestamp'] for c in candles],
            open=[c['open'] for c in candles],
            high=[c['high'] for c in candles],
            low=[c['low'] for c in candles],
            close=[c['close'] for c in candles],
            name="Price"
        ))
        
        # Add ATR bands if provided
        if atr_bands:
            fig.add_trace(go.Scatter(
                x=atr_bands['timestamps'],
                y=atr_bands['upper'],
                name="ATR Upper",
                line=dict(dash='dash', color='gray')
            ))
            fig.add_trace(go.Scatter(
                x=atr_bands['timestamps'],
                y=atr_bands['lower'],
                name="ATR Lower",
                line=dict(dash='dash', color='gray')
            ))
        
        # Mark position entries
        if positions:
            for pos in positions:
                fig.add_trace(go.Scatter(
                    x=[pos['entry_time']],
                    y=[pos['entry_price']],
                    mode='markers',
                    marker=dict(
                        size=12,
                        symbol='triangle-up' if pos['side'] == 'LONG' else 'triangle-down',
                        color='green' if pos['side'] == 'LONG' else 'red'
                    ),
                    name=f"{pos['side']} Entry"
                ))
        
        fig.update_layout(
            title="Price Chart",
            xaxis_title="Time",
            yaxis_title="Price",
            height=600
        )
        
        return fig
    
    def create_pnl_chart(self, trades: List[Dict]) -> go.Figure:
        """Create cumulative PnL chart."""
        cumulative_pnl = []
        running_total = 0
        timestamps = []
        
        for trade in trades:
            running_total += trade['pnl']
            cumulative_pnl.append(running_total)
            timestamps.append(trade['exit_time'])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=cumulative_pnl,
            mode='lines',
            fill='tozeroy',
            name="Cumulative PnL"
        ))
        
        fig.update_layout(
            title="Cumulative PnL Over Time",
            xaxis_title="Time",
            yaxis_title="PnL (USDT)",
            height=400
        )
        
        return fig
```

## Data Models

The dashboard uses the existing data models from `src/models.py`:

- **Position**: Open trading positions
- **Trade**: Completed trades
- **PerformanceMetrics**: Analytics and statistics
- **Candle**: Price data for charts

Additional dashboard-specific models:

```python
@dataclass
class DashboardState:
    """Current state of the dashboard."""
    bot_status: str  # "Running" or "Stopped"
    last_update: datetime
    balance: float
    total_pnl: float
    open_positions: List[Position]
    recent_trades: List[Trade]
    current_price: float
    indicators: Dict[str, float]
    signal: str  # "LONG", "SHORT", "NONE"
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Position Display Completeness
*For any* set of open positions, when displayed by the Dashboard, all positions must include symbol, side, entry_price, current_price, PnL, stop_loss, and take_profit fields.
**Validates: Requirements 2.1, 2.2**

### Property 2: PnL Color Coding
*For any* PnL value displayed, the color must be green when PnL > 0, red when PnL < 0, and neutral when PnL == 0.
**Validates: Requirements 2.5**

### Property 3: Indicator Highlighting
*For any* indicator values that exceed their configured thresholds, the Dashboard must apply highlighting to those indicators.
**Validates: Requirements 3.3**

### Property 4: Chart Entry Markers
*For any* open positions, the price chart must include entry point markers at the correct price and timestamp for each position.
**Validates: Requirements 4.2**

### Property 5: Chart Candle Count
*For any* chart update, the Dashboard must fetch and display exactly 100 candles for the selected timeframe.
**Validates: Requirements 4.5**

### Property 6: Control Action Confirmations
*For any* dangerous control action (stop bot, emergency close), the Control_Panel must display a confirmation dialog before executing.
**Validates: Requirements 5.4**

### Property 7: Control Action Feedback
*For any* control action result (success or failure), the Control_Panel must display an appropriate feedback message.
**Validates: Requirements 5.5**

### Property 8: Config Validation
*For any* configuration input that violates validation rules, the Config_Editor must reject the input and display an error message.
**Validates: Requirements 6.2, 6.5**

### Property 9: Config Round Trip
*For any* valid configuration, saving then loading the configuration must produce equivalent values.
**Validates: Requirements 6.3**

### Property 10: Trade Display Completeness
*For any* trade in the history, when displayed, it must include entry_time, exit_time, symbol, side, PnL, and return_percentage fields.
**Validates: Requirements 7.2**

### Property 11: Trade Sorting
*For any* trade list, sorting by date or PnL must correctly reorder trades according to the selected field.
**Validates: Requirements 7.3**

### Property 12: Win Rate Calculation
*For any* set of trades, the calculated win rate must equal (winning_trades / total_trades) * 100.
**Validates: Requirements 7.4**

### Property 13: Sharpe Ratio Calculation
*For any* trade history with non-zero standard deviation, the Sharpe ratio must be calculated as (mean_return - risk_free_rate) / std_dev_return.
**Validates: Requirements 8.3**

### Property 14: Maximum Drawdown Calculation
*For any* equity curve, the maximum drawdown must be the largest peak-to-trough decline in cumulative PnL.
**Validates: Requirements 8.4**

### Property 15: Time Period Filtering
*For any* time period filter (24h, 7d, 30d), only trades with exit_time within that period must be included in analytics.
**Validates: Requirements 8.5**

### Property 16: Graceful File Handling
*For any* missing or corrupted data file, the Data_Provider must return default values without raising exceptions.
**Validates: Requirements 9.4**

## Error Handling

### File Access Errors
- **Missing config.json**: Use default configuration values
- **Missing binance_results.json**: Show "No data available" message
- **Missing log files**: Show empty trade history
- **Corrupted JSON**: Log error and use defaults

### Process Control Errors
- **Bot already running**: Display warning message
- **Bot not found**: Display error message
- **Permission denied**: Display error with instructions
- **Timeout**: Display timeout error after 10 seconds

### Validation Errors
- **Invalid config values**: Show specific error messages
- **Out of range values**: Show acceptable range
- **Missing required fields**: Highlight missing fields

### Network Errors
- **API connection failed**: Show connection error
- **Rate limit exceeded**: Show rate limit warning
- **Authentication failed**: Show API key error

## Testing Strategy

### Unit Tests
Unit tests verify specific examples, edge cases, and error conditions:

- Test data provider with sample JSON files
- Test config validation with invalid inputs
- Test chart generation with sample data
- Test bot controller process management
- Test error handling for missing files

### Property-Based Tests
Property tests verify universal properties across all inputs:

- **Property 1-16**: Each correctness property must be implemented as a property-based test
- Minimum 100 iterations per property test
- Each test tagged with: **Feature: streamlit-ui, Property N: [property text]**

### Integration Tests
- Test full dashboard load with real data files
- Test bot start/stop workflow
- Test config save/load workflow
- Test chart rendering with various data sizes

### Manual Testing
- Test responsive layout on different screen sizes
- Test auto-refresh behavior
- Test UI interactions (buttons, dropdowns, etc.)
- Test visual appearance and styling

### Testing Framework
- **pytest**: Unit and integration tests
- **hypothesis**: Property-based testing
- **pytest-mock**: Mocking file I/O and processes
- **streamlit.testing**: Streamlit component testing

Example property test:
```python
from hypothesis import given, strategies as st
import pytest

@given(st.lists(st.floats(min_value=-1000, max_value=1000)))
def test_pnl_color_coding(pnl_values):
    """Feature: streamlit-ui, Property 2: PnL Color Coding
    
    For any PnL value, color must be green when positive,
    red when negative, and neutral when zero.
    """
    for pnl in pnl_values:
        color = get_pnl_color(pnl)
        
        if pnl > 0:
            assert color == "green"
        elif pnl < 0:
            assert color == "red"
        else:
            assert color == "neutral"
```

## Dependencies

New dependencies for Streamlit UI:

```
streamlit>=1.28.0
streamlit-autorefresh>=0.0.1
plotly>=5.17.0
psutil>=5.9.0
pandas>=2.0.0
```

These will be added to a separate `requirements_ui.txt` file to keep UI dependencies separate from core bot dependencies.

## Deployment

### Running the Dashboard

```bash
# Install UI dependencies
pip install -r requirements_ui.txt

# Start the dashboard
streamlit run streamlit_app.py

# Dashboard will be available at http://localhost:8501
```

### Running Bot and Dashboard Together

```bash
# Terminal 1: Start the trading bot
python main.py

# Terminal 2: Start the dashboard
streamlit run streamlit_app.py
```

### Windows Batch Script

```batch
@echo off
echo Starting Trading Bot Dashboard...
start cmd /k "python main.py"
timeout /t 3
start cmd /k "streamlit run streamlit_app.py"
echo Dashboard starting at http://localhost:8501
```

## Security Considerations

- **API Keys**: Never display full API keys in UI (use redaction)
- **Config Editing**: Validate all inputs before saving
- **Process Control**: Require confirmation for dangerous actions
- **File Access**: Use read-only access where possible
- **Error Messages**: Don't expose sensitive information in errors

## Performance Considerations

- **Caching**: Cache file reads for 5 seconds to reduce I/O
- **Auto-refresh**: Limit refresh rate to 5 seconds
- **Chart Data**: Limit candles to 100 to avoid memory issues
- **Trade History**: Limit display to 20 most recent trades
- **Log Parsing**: Parse only recent log files, not entire history
