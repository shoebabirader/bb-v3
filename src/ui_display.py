"""Terminal UI Dashboard for Binance Futures Trading Bot.

This module provides a rich terminal interface for monitoring trading activity,
displaying real-time metrics, and showing backtest results.
"""

from typing import List, Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box

from src.models import Position, Trade, PerformanceMetrics


class UIDisplay:
    """Terminal UI display using Rich library for real-time monitoring.
    
    Provides methods to render dashboard, display backtest results,
    show notifications, and handle panic close confirmations.
    """
    
    def __init__(self):
        """Initialize the UI display with Rich console."""
        self.console = Console()
        self.live_display: Optional[Live] = None
        
    def render_dashboard(
        self,
        positions: List[Position],
        trades: List[Trade],
        indicators: dict,
        wallet_balance: float,
        mode: str = "LIVE",
        market_regime: Optional[str] = None,
        ml_prediction: Optional[float] = None,
        volume_profile: Optional[dict] = None,
        adaptive_thresholds: Optional[dict] = None
    ) -> Panel:
        """Render main dashboard with live updates.
        
        Displays:
        - Current PnL (unrealized and realized)
        - Win rate
        - Trend status (1h and 15m)
        - RVOL level
        - ADX value
        - Market regime (if provided)
        - ML prediction probability (if provided)
        - Volume profile levels (POC, VAH, VAL) (if provided)
        - Adaptive thresholds (if provided)
        - Open positions
        - Recent trades
        
        Args:
            positions: List of currently open positions
            trades: List of completed trades
            indicators: Dictionary of current indicator values
            wallet_balance: Current wallet balance in USDT
            mode: Operating mode ("BACKTEST", "PAPER", "LIVE")
            market_regime: Current market regime (optional)
            ml_prediction: ML prediction probability 0.0-1.0 (optional)
            volume_profile: Dict with 'poc', 'vah', 'val' keys (optional)
            adaptive_thresholds: Dict with 'adx', 'rvol' keys (optional)
            
        Returns:
            Rich Panel containing the formatted dashboard
        """
        # Calculate metrics
        unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
        realized_pnl = sum(trade.pnl for trade in trades)
        total_pnl = unrealized_pnl + realized_pnl
        
        # Calculate win rate
        if trades:
            winning_trades = sum(1 for t in trades if t.pnl > 0)
            win_rate = (winning_trades / len(trades)) * 100
        else:
            win_rate = 0.0
            
        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Header with mode and timestamp
        mode_color = {
            "BACKTEST": "yellow",
            "PAPER": "cyan",
            "LIVE": "red"
        }.get(mode, "white")
        
        header_text = Text()
        header_text.append("Binance Futures Trading Bot", style="bold white")
        header_text.append(f" | Mode: ", style="white")
        header_text.append(mode, style=f"bold {mode_color}")
        header_text.append(f" | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim white")
        
        layout["header"].update(Panel(header_text, border_style="blue"))
        
        # Body - split into metrics and positions
        layout["body"].split_row(
            Layout(name="metrics", ratio=2),
            Layout(name="advanced", ratio=1),
            Layout(name="positions", ratio=1)
        )
        
        # Metrics section
        metrics_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        metrics_table.add_column("Metric", style="cyan", width=20)
        metrics_table.add_column("Value", justify="right")
        
        # PnL with color coding
        pnl_color = "green" if total_pnl >= 0 else "red"
        pnl_symbol = "+" if total_pnl >= 0 else ""
        metrics_table.add_row(
            "Total PnL",
            Text(f"{pnl_symbol}${total_pnl:.2f}", style=f"bold {pnl_color}")
        )
        
        unrealized_color = "green" if unrealized_pnl >= 0 else "red"
        unrealized_symbol = "+" if unrealized_pnl >= 0 else ""
        metrics_table.add_row(
            "Unrealized PnL",
            Text(f"{unrealized_symbol}${unrealized_pnl:.2f}", style=unrealized_color)
        )
        
        realized_color = "green" if realized_pnl >= 0 else "red"
        realized_symbol = "+" if realized_pnl >= 0 else ""
        metrics_table.add_row(
            "Realized PnL",
            Text(f"{realized_symbol}${realized_pnl:.2f}", style=realized_color)
        )
        
        metrics_table.add_row("Wallet Balance", f"${wallet_balance:.2f}")
        metrics_table.add_row("Total Trades", str(len(trades)))
        
        # Win rate with color coding
        win_rate_color = "green" if win_rate >= 50 else "yellow" if win_rate >= 40 else "red"
        metrics_table.add_row(
            "Win Rate",
            Text(f"{win_rate:.1f}%", style=win_rate_color)
        )
        
        # Trend indicators
        trend_1h = indicators.get('trend_1h', 'NEUTRAL')
        trend_1h_color = "green" if trend_1h == "BULLISH" else "red" if trend_1h == "BEARISH" else "yellow"
        metrics_table.add_row(
            "1H Trend",
            Text(trend_1h, style=f"bold {trend_1h_color}")
        )
        
        trend_15m = indicators.get('trend_15m', 'NEUTRAL')
        trend_15m_color = "green" if trend_15m == "BULLISH" else "red" if trend_15m == "BEARISH" else "yellow"
        metrics_table.add_row(
            "15M Trend",
            Text(trend_15m, style=trend_15m_color)
        )
        
        # RVOL with color coding
        rvol = indicators.get('rvol', 0.0)
        rvol_color = "green" if rvol >= 1.2 else "yellow" if rvol >= 1.0 else "white"
        metrics_table.add_row(
            "RVOL",
            Text(f"{rvol:.2f}", style=rvol_color)
        )
        
        # ADX with color coding
        adx = indicators.get('adx', 0.0)
        adx_color = "green" if adx >= 25 else "yellow" if adx >= 20 else "white"
        metrics_table.add_row(
            "ADX",
            Text(f"{adx:.1f}", style=adx_color)
        )
        
        # Current price
        current_price = indicators.get('current_price', 0.0)
        metrics_table.add_row("Current Price", f"${current_price:.2f}")
        
        layout["metrics"].update(Panel(metrics_table, title="Metrics", border_style="cyan"))
        
        # Advanced features section
        advanced_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        advanced_table.add_column("Feature", style="magenta", width=18)
        advanced_table.add_column("Value", justify="left", width=20)
        
        # Market regime
        if market_regime:
            regime_colors = {
                "TRENDING_BULLISH": "green",
                "TRENDING_BEARISH": "red",
                "RANGING": "yellow",
                "VOLATILE": "orange1",
                "UNCERTAIN": "dim white"
            }
            regime_color = regime_colors.get(market_regime, "white")
            regime_display = market_regime.replace("_", " ")
            advanced_table.add_row(
                "Market Regime",
                Text(regime_display, style=f"bold {regime_color}")
            )
        
        # ML prediction
        if ml_prediction is not None:
            ml_color = "green" if ml_prediction > 0.7 else "red" if ml_prediction < 0.3 else "yellow"
            ml_direction = "BULLISH" if ml_prediction > 0.5 else "BEARISH"
            advanced_table.add_row(
                "ML Prediction",
                Text(f"{ml_prediction:.2f} ({ml_direction})", style=ml_color)
            )
        
        # Volume profile levels
        if volume_profile:
            poc = volume_profile.get('poc')
            vah = volume_profile.get('vah')
            val = volume_profile.get('val')
            
            if poc is not None:
                advanced_table.add_row("POC", f"${poc:.2f}")
            if vah is not None:
                advanced_table.add_row("VAH", f"${vah:.2f}")
            if val is not None:
                advanced_table.add_row("VAL", f"${val:.2f}")
        
        # Adaptive thresholds
        if adaptive_thresholds:
            adx_threshold = adaptive_thresholds.get('adx')
            rvol_threshold = adaptive_thresholds.get('rvol')
            
            if adx_threshold is not None:
                advanced_table.add_row("ADX Threshold", f"{adx_threshold:.1f}")
            if rvol_threshold is not None:
                advanced_table.add_row("RVOL Threshold", f"{rvol_threshold:.2f}")
        
        # Only show advanced panel if there's data
        if market_regime or ml_prediction is not None or volume_profile or adaptive_thresholds:
            layout["advanced"].update(Panel(advanced_table, title="Advanced Features", border_style="magenta"))
        else:
            layout["advanced"].update(Panel(
                Text("No advanced data", style="dim white", justify="center"),
                title="Advanced Features",
                border_style="magenta"
            ))
        
        # Positions section
        if positions:
            positions_table = Table(show_header=True, box=box.SIMPLE_HEAD, padding=(0, 1))
            positions_table.add_column("Side", style="cyan", width=8)
            positions_table.add_column("Entry", justify="right", width=10)
            positions_table.add_column("PnL", justify="right", width=10)
            
            for pos in positions:
                side_color = "green" if pos.side == "LONG" else "red"
                pnl_color = "green" if pos.unrealized_pnl >= 0 else "red"
                pnl_symbol = "+" if pos.unrealized_pnl >= 0 else ""
                
                positions_table.add_row(
                    Text(pos.side, style=side_color),
                    f"${pos.entry_price:.2f}",
                    Text(f"{pnl_symbol}${pos.unrealized_pnl:.2f}", style=pnl_color)
                )
            
            layout["positions"].update(Panel(positions_table, title="Open Positions", border_style="yellow"))
        else:
            layout["positions"].update(Panel(
                Text("No open positions", style="dim white", justify="center"),
                title="Open Positions",
                border_style="yellow"
            ))
        
        # Footer with controls
        footer_text = Text()
        footer_text.append("Controls: ", style="bold white")
        footer_text.append("[ESC]", style="bold red")
        footer_text.append(" Panic Close | ", style="white")
        footer_text.append("[Ctrl+C]", style="bold yellow")
        footer_text.append(" Exit", style="white")
        
        layout["footer"].update(Panel(footer_text, border_style="blue"))
        
        return Panel(layout, title="Trading Dashboard", border_style="bold blue", padding=(1, 2))
    
    def display_backtest_results(self, results: PerformanceMetrics, initial_balance: float = 10000.0):
        """Display backtest performance metrics in a formatted table.
        
        Args:
            results: PerformanceMetrics object with backtest results
            initial_balance: Initial balance used for backtest
        """
        self.console.print("\n")
        self.console.rule("[bold cyan]Backtest Results", style="cyan")
        self.console.print("\n")
        
        # Create results table
        table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED, padding=(0, 2))
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", justify="right", width=20)
        
        # Trade statistics
        table.add_row("Total Trades", str(results.total_trades))
        table.add_row("Winning Trades", str(results.winning_trades))
        table.add_row("Losing Trades", str(results.losing_trades))
        
        # Win rate with color
        win_rate_color = "green" if results.win_rate >= 50 else "yellow" if results.win_rate >= 40 else "red"
        table.add_row(
            "Win Rate",
            Text(f"{results.win_rate:.2f}%", style=f"bold {win_rate_color}")
        )
        
        # PnL metrics
        pnl_color = "green" if results.total_pnl >= 0 else "red"
        pnl_symbol = "+" if results.total_pnl >= 0 else ""
        table.add_row(
            "Total PnL",
            Text(f"{pnl_symbol}${results.total_pnl:.2f}", style=f"bold {pnl_color}")
        )
        
        roi_color = "green" if results.roi >= 0 else "red"
        roi_symbol = "+" if results.roi >= 0 else ""
        table.add_row(
            "ROI",
            Text(f"{roi_symbol}{results.roi:.2f}%", style=f"bold {roi_color}")
        )
        
        # Risk metrics
        table.add_row(
            "Max Drawdown",
            Text(f"-${abs(results.max_drawdown):.2f}", style="red")
        )
        table.add_row(
            "Max Drawdown %",
            Text(f"-{abs(results.max_drawdown_percent):.2f}%", style="red")
        )
        
        # Performance metrics
        pf_color = "green" if results.profit_factor >= 1.5 else "yellow" if results.profit_factor >= 1.0 else "red"
        table.add_row(
            "Profit Factor",
            Text(f"{results.profit_factor:.2f}", style=pf_color)
        )
        
        sharpe_color = "green" if results.sharpe_ratio >= 1.0 else "yellow" if results.sharpe_ratio >= 0.5 else "red"
        table.add_row(
            "Sharpe Ratio",
            Text(f"{results.sharpe_ratio:.2f}", style=sharpe_color)
        )
        
        # Trade averages
        if results.average_win > 0:
            table.add_row("Average Win", Text(f"+${results.average_win:.2f}", style="green"))
        if results.average_loss < 0:
            table.add_row("Average Loss", Text(f"${results.average_loss:.2f}", style="red"))
        if results.largest_win > 0:
            table.add_row("Largest Win", Text(f"+${results.largest_win:.2f}", style="bold green"))
        if results.largest_loss < 0:
            table.add_row("Largest Loss", Text(f"${results.largest_loss:.2f}", style="bold red"))
        
        # Trade duration
        if results.average_trade_duration > 0:
            hours = results.average_trade_duration // 3600
            minutes = (results.average_trade_duration % 3600) // 60
            table.add_row("Avg Trade Duration", f"{hours}h {minutes}m")
        
        # Final balance
        final_balance = initial_balance + results.total_pnl
        final_color = "green" if final_balance >= initial_balance else "red"
        table.add_row("Initial Balance", f"${initial_balance:.2f}")
        table.add_row(
            "Final Balance",
            Text(f"${final_balance:.2f}", style=f"bold {final_color}")
        )
        
        self.console.print(table)
        self.console.print("\n")
    
    def show_notification(self, message: str, level: str = "INFO"):
        """Display notification message with appropriate styling.
        
        Args:
            message: Notification message to display
            level: Notification level ("INFO", "WARNING", "ERROR", "SUCCESS")
        """
        level_styles = {
            "INFO": ("blue", "[i]"),
            "WARNING": ("yellow", "[WARNING]"),
            "ERROR": ("red", "[X]"),
            "SUCCESS": ("green", "[OK]")
        }
        
        style, icon = level_styles.get(level.upper(), ("white", "•"))
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        notification_text = Text()
        notification_text.append(f"[{timestamp}] ", style="dim white")
        notification_text.append(f"{icon} ", style=f"bold {style}")
        notification_text.append(message, style=style)
        
        self.console.print(notification_text)
    
    def show_panic_confirmation(self, closed_positions: int, total_pnl: float):
        """Display panic close confirmation message.
        
        Args:
            closed_positions: Number of positions that were closed
            total_pnl: Total PnL from closed positions
        """
        self.console.print("\n")
        
        panel_content = Text()
        panel_content.append("🚨 PANIC CLOSE EXECUTED 🚨\n\n", style="bold red")
        panel_content.append(f"Closed Positions: {closed_positions}\n", style="white")
        
        pnl_color = "green" if total_pnl >= 0 else "red"
        pnl_symbol = "+" if total_pnl >= 0 else ""
        panel_content.append(f"Total PnL: {pnl_symbol}${total_pnl:.2f}\n\n", style=f"bold {pnl_color}")
        panel_content.append("All positions have been closed.\n", style="yellow")
        panel_content.append("Signal generation has been stopped.", style="yellow")
        
        panel = Panel(
            panel_content,
            title="Emergency Exit",
            border_style="bold red",
            padding=(1, 2)
        )
        
        self.console.print(panel)
        self.console.print("\n")
    
    def render_portfolio_view(
        self,
        portfolio_metrics: Optional[dict] = None
    ) -> Panel:
        """Render portfolio view with multi-symbol information.
        
        Displays:
        - All active symbols
        - Per-symbol PnL
        - Correlation matrix
        - Portfolio-level metrics
        
        Args:
            portfolio_metrics: Dictionary containing:
                - 'symbols': List of active symbol names
                - 'per_symbol_pnl': Dict mapping symbol to PnL
                - 'correlation_matrix': Dict of (symbol1, symbol2) -> correlation
                - 'total_value': Total portfolio value
                - 'total_pnl': Total portfolio PnL
                - 'total_risk': Total portfolio risk percentage
                - 'diversification_ratio': Portfolio diversification ratio
                
        Returns:
            Rich Panel containing the formatted portfolio view
        """
        if not portfolio_metrics:
            return Panel(
                Text("No portfolio data available", style="dim white", justify="center"),
                title="Portfolio View",
                border_style="blue",
                padding=(1, 2)
            )
        
        layout = Layout()
        layout.split_column(
            Layout(name="summary", size=8),
            Layout(name="symbols"),
            Layout(name="correlation", size=10)
        )
        
        # Portfolio summary
        summary_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        summary_table.add_column("Metric", style="cyan", width=25)
        summary_table.add_column("Value", justify="right")
        
        total_value = portfolio_metrics.get('total_value', 0.0)
        total_pnl = portfolio_metrics.get('total_pnl', 0.0)
        total_risk = portfolio_metrics.get('total_risk', 0.0)
        diversification_ratio = portfolio_metrics.get('diversification_ratio', 0.0)
        
        summary_table.add_row("Total Portfolio Value", f"${total_value:.2f}")
        
        pnl_color = "green" if total_pnl >= 0 else "red"
        pnl_symbol = "+" if total_pnl >= 0 else ""
        summary_table.add_row(
            "Total Portfolio PnL",
            Text(f"{pnl_symbol}${total_pnl:.2f}", style=f"bold {pnl_color}")
        )
        
        risk_color = "green" if total_risk <= 2.0 else "yellow" if total_risk <= 3.0 else "red"
        summary_table.add_row(
            "Total Portfolio Risk",
            Text(f"{total_risk:.2f}%", style=risk_color)
        )
        
        div_color = "green" if diversification_ratio >= 0.7 else "yellow" if diversification_ratio >= 0.5 else "red"
        summary_table.add_row(
            "Diversification Ratio",
            Text(f"{diversification_ratio:.2f}", style=div_color)
        )
        
        layout["summary"].update(Panel(summary_table, title="Portfolio Summary", border_style="cyan"))
        
        # Per-symbol PnL
        symbols = portfolio_metrics.get('symbols', [])
        per_symbol_pnl = portfolio_metrics.get('per_symbol_pnl', {})
        
        if symbols and per_symbol_pnl:
            symbols_table = Table(show_header=True, box=box.SIMPLE_HEAD, padding=(0, 1))
            symbols_table.add_column("Symbol", style="cyan", width=12)
            symbols_table.add_column("PnL", justify="right", width=15)
            symbols_table.add_column("Status", justify="center", width=10)
            
            for symbol in symbols:
                pnl = per_symbol_pnl.get(symbol, 0.0)
                pnl_color = "green" if pnl >= 0 else "red"
                pnl_symbol = "+" if pnl >= 0 else ""
                
                status = "ACTIVE" if pnl != 0 else "IDLE"
                status_color = "green" if status == "ACTIVE" else "dim white"
                
                symbols_table.add_row(
                    symbol,
                    Text(f"{pnl_symbol}${pnl:.2f}", style=pnl_color),
                    Text(status, style=status_color)
                )
            
            layout["symbols"].update(Panel(symbols_table, title="Symbol Performance", border_style="yellow"))
        else:
            layout["symbols"].update(Panel(
                Text("No active symbols", style="dim white", justify="center"),
                title="Symbol Performance",
                border_style="yellow"
            ))
        
        # Correlation matrix
        correlation_matrix = portfolio_metrics.get('correlation_matrix', {})
        
        if correlation_matrix and len(symbols) > 1:
            corr_table = Table(show_header=True, box=box.SIMPLE_HEAD, padding=(0, 1))
            corr_table.add_column("", style="cyan", width=10)
            
            for symbol in symbols:
                corr_table.add_column(symbol[:8], justify="center", width=8)
            
            for symbol1 in symbols:
                row_data = [symbol1[:8]]
                for symbol2 in symbols:
                    if symbol1 == symbol2:
                        row_data.append(Text("1.00", style="dim white"))
                    else:
                        # Try both orderings of the tuple
                        corr = correlation_matrix.get((symbol1, symbol2))
                        if corr is None:
                            corr = correlation_matrix.get((symbol2, symbol1), 0.0)
                        
                        corr_color = "red" if abs(corr) > 0.7 else "yellow" if abs(corr) > 0.5 else "green"
                        row_data.append(Text(f"{corr:.2f}", style=corr_color))
                
                corr_table.add_row(*row_data)
            
            layout["correlation"].update(Panel(corr_table, title="Correlation Matrix", border_style="magenta"))
        else:
            layout["correlation"].update(Panel(
                Text("Insufficient data for correlation", style="dim white", justify="center"),
                title="Correlation Matrix",
                border_style="magenta"
            ))
        
        return Panel(layout, title="Portfolio View", border_style="bold blue", padding=(1, 2))
    
    def render_feature_status(
        self,
        feature_status: Optional[dict] = None
    ) -> Panel:
        """Render feature status indicators.
        
        Displays:
        - Which features are enabled/disabled
        - ML predictor accuracy
        - Last threshold adjustment timestamp
        
        Args:
            feature_status: Dictionary containing:
                - 'adaptive_thresholds': bool (enabled/disabled)
                - 'ml_predictor': bool (enabled/disabled)
                - 'ml_accuracy': float (0.0-1.0)
                - 'volume_profile': bool (enabled/disabled)
                - 'market_regime': bool (enabled/disabled)
                - 'portfolio_manager': bool (enabled/disabled)
                - 'advanced_exits': bool (enabled/disabled)
                - 'last_threshold_adjustment': int (timestamp)
                
        Returns:
            Rich Panel containing the formatted feature status
        """
        if not feature_status:
            return Panel(
                Text("No feature status data available", style="dim white", justify="center"),
                title="Feature Status",
                border_style="blue",
                padding=(1, 2)
            )
        
        layout = Layout()
        layout.split_column(
            Layout(name="features", ratio=2),
            Layout(name="details", ratio=1)
        )
        
        # Feature toggles
        features_table = Table(show_header=True, box=box.SIMPLE_HEAD, padding=(0, 1))
        features_table.add_column("Feature", style="cyan", width=25)
        features_table.add_column("Status", justify="center", width=12)
        
        feature_names = {
            'adaptive_thresholds': 'Adaptive Thresholds',
            'ml_predictor': 'ML Predictor',
            'volume_profile': 'Volume Profile',
            'market_regime': 'Market Regime',
            'portfolio_manager': 'Portfolio Manager',
            'advanced_exits': 'Advanced Exits'
        }
        
        for key, name in feature_names.items():
            enabled = feature_status.get(key, False)
            if enabled:
                status_text = Text("[OK] ENABLED", style="bold green")
            else:
                status_text = Text("[X] DISABLED", style="dim red")
            
            features_table.add_row(name, status_text)
        
        layout["features"].update(Panel(features_table, title="Feature Toggles", border_style="cyan"))
        
        # Feature details
        details_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        details_table.add_column("Detail", style="magenta", width=22)
        details_table.add_column("Value", justify="right")
        
        # ML accuracy
        ml_accuracy = feature_status.get('ml_accuracy')
        if ml_accuracy is not None:
            accuracy_pct = ml_accuracy * 100
            accuracy_color = "green" if accuracy_pct >= 55 else "red"
            details_table.add_row(
                "ML Accuracy",
                Text(f"{accuracy_pct:.1f}%", style=accuracy_color)
            )
        
        # Last threshold adjustment
        last_adjustment = feature_status.get('last_threshold_adjustment')
        if last_adjustment:
            try:
                adjustment_time = datetime.fromtimestamp(last_adjustment)
                time_ago = datetime.now() - adjustment_time
                
                if time_ago.total_seconds() < 3600:
                    minutes = int(time_ago.total_seconds() / 60)
                    time_str = f"{minutes}m ago"
                else:
                    hours = int(time_ago.total_seconds() / 3600)
                    time_str = f"{hours}h ago"
                
                details_table.add_row("Last Threshold Adj", time_str)
            except (ValueError, OSError):
                details_table.add_row("Last Threshold Adj", "N/A")
        
        layout["details"].update(Panel(details_table, title="Feature Details", border_style="magenta"))
        
        return Panel(layout, title="Feature Status", border_style="bold blue", padding=(1, 2))
    
    def clear_screen(self):
        """Clear the terminal screen."""
        self.console.clear()
    
    def print_separator(self):
        """Print a visual separator line."""
        self.console.rule(style="dim white")
