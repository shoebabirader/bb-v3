"""Main Trading Bot orchestration class for Binance Futures Trading Bot.

This module provides the main TradingBot class that coordinates all subsystems
and implements the main event loop for real-time trading.
"""

import time
import logging
import signal
import sys
from typing import Optional, List, Dict
from binance.client import Client

# Try to import pynput for keyboard listener (optional for headless servers)
try:
    from pynput import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    keyboard = None

from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer
from src.order_executor import OrderExecutor
from src.ui_display import UIDisplay
from src.backtest_engine import BacktestEngine
from src.logger import get_logger, TradingLogger
from src.models import PerformanceMetrics
from src.portfolio_manager import PortfolioManager
from src.scaled_tp_manager import ScaledTakeProfitManager


# Configure logging with BOTH file and console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(sys.stdout)  # Print to console
    ]
)
logger = logging.getLogger(__name__)
logger.info("=" * 80)
logger.info("TRADING BOT STARTING")
logger.info("=" * 80)


class TradingBot:
    """Main trading bot orchestrator.
    
    Coordinates all subsystems:
    - Data management (historical and real-time)
    - Strategy engine (signal generation)
    - Risk management (position sizing and stops)
    - Order execution (Binance API integration)
    - UI display (terminal dashboard)
    - Logging and persistence
    
    Supports three operational modes:
    - BACKTEST: Simulate strategy on historical data
    - PAPER: Real-time trading with simulated execution
    - LIVE: Real-time trading with actual order execution
    """
    
    def __init__(self, config: Config):
        """Initialize TradingBot with configuration.
        
        Args:
            config: Configuration object with all parameters
        """
        self.config = config
        self.running = False
        self._panic_triggered = False
        
        # Initialize logger
        self.logger = get_logger(config=config)
        
        # Initialize Binance client (needed for all modes to fetch data)
        self.client: Optional[Client] = None
        if config.api_key and config.api_secret:
            self.client = Client(config.api_key, config.api_secret)
            logger.info("Binance client initialized")
        elif config.run_mode in ["PAPER", "LIVE"]:
            raise ValueError("API keys required for PAPER and LIVE modes")
        
        # Initialize subsystems
        self.data_manager = DataManager(config, self.client)
        self.strategy = StrategyEngine(config)
        self.position_sizer = PositionSizer(config)
        self.risk_manager = RiskManager(config, self.position_sizer)
        self.order_executor = OrderExecutor(config, self.client)
        self.ui_display = UIDisplay()
        
        # Initialize portfolio manager (if enabled)
        self.portfolio_manager: Optional[PortfolioManager] = None
        if config.enable_portfolio_management:
            self.portfolio_manager = PortfolioManager(config)
            logger.info(f"Portfolio Manager initialized with {len(config.portfolio_symbols)} symbols")
        
        # Initialize scaled take profit manager
        self.scaled_tp_manager = ScaledTakeProfitManager(config, self.client)
        if config.enable_scaled_take_profit:
            logger.info(f"Scaled TP Manager initialized with {len(config.scaled_tp_levels)} levels")
        
        # Initialize backtest engine (only for BACKTEST mode)
        self.backtest_engine: Optional[BacktestEngine] = None
        if config.run_mode == "BACKTEST":
            self.backtest_engine = BacktestEngine(config, self.strategy, self.risk_manager)
        
        # Keyboard listener for panic close (optional, only on systems with display)
        self.keyboard_listener: Optional[any] = None
        
        # Wallet balance tracking
        self.wallet_balance = 10000.0  # Default for backtest/paper
        
        # Per-symbol indicator storage for dashboard
        self._symbol_indicators: Dict[str, Dict[str, float]] = {}
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"TradingBot initialized in {config.run_mode} mode")
    
    def _fetch_multi_symbol_data(self, symbols: List[str], days: int = 7):
        """Fetch historical data for multiple symbols.
        
        Args:
            symbols: List of symbols to fetch data for
            days: Number of days of historical data
        """
        for idx, symbol in enumerate(symbols):
            try:
                # Add delay between symbols to avoid rate limiting (except for first symbol)
                if idx > 0:
                    delay = 0.5  # 500ms delay between symbols
                    logger.info(f"Waiting {delay}s before fetching {symbol} data...")
                    time.sleep(delay)
                
                logger.info(f"Fetching 15m data for {symbol}...")
                candles_15m = self.data_manager.fetch_historical_data(days=days, timeframe="15m", symbol=symbol)
                logger.info(f"  Fetched {len(candles_15m)} candles for {symbol} 15m")
                
                logger.info(f"Fetching 1h data for {symbol}...")
                candles_1h = self.data_manager.fetch_historical_data(days=days, timeframe="1h", symbol=symbol)
                logger.info(f"  Fetched {len(candles_1h)} candles for {symbol} 1h")
                
                # Fetch additional timeframes if multi-timeframe is enabled
                if self.config.enable_multi_timeframe:
                    logger.info(f"Multi-timeframe enabled, fetching 5m data for {symbol}...")
                    candles_5m = self.data_manager.fetch_historical_data(days=days, timeframe="5m", symbol=symbol)
                    logger.info(f"  Fetched {len(candles_5m)} candles for {symbol} 5m")
                    
                    logger.info(f"Multi-timeframe enabled, fetching 4h data for {symbol}...")
                    candles_4h = self.data_manager.fetch_historical_data(days=days, timeframe="4h", symbol=symbol)
                    logger.info(f"  Fetched {len(candles_4h)} candles for {symbol} 4h")
                else:
                    logger.info(f"Multi-timeframe disabled, skipping 5m and 4h data for {symbol}")
                
                logger.info(f"[OK] Fetched historical data for {symbol}")
            except Exception as e:
                logger.error(f"[X] Error fetching data for {symbol}: {e}", exc_info=True)
                raise  # Re-raise to stop execution if data fetch fails
    
    def _get_trading_symbols(self) -> List[str]:
        """Get list of symbols to trade.
        
        Returns:
            List of symbol strings. If portfolio management is enabled,
            returns all portfolio symbols. Otherwise, returns single primary symbol.
        """
        if self.config.enable_portfolio_management and self.portfolio_manager:
            return self.portfolio_manager.symbols
        else:
            return [self.config.symbol]
    
    def start(self):
        """Start the trading bot based on configured mode.
        
        Routes to appropriate execution method based on run_mode:
        - BACKTEST: Run backtest on historical data
        - PAPER: Start paper trading with real-time data
        - LIVE: Start live trading with real execution
        """
        self.logger.log_system_event(f"Starting TradingBot in {self.config.run_mode} mode")
        
        try:
            if self.config.run_mode == "BACKTEST":
                self._run_backtest()
            elif self.config.run_mode == "PAPER":
                self._run_paper_trading()
            elif self.config.run_mode == "LIVE":
                self._run_live_trading()
            else:
                raise ValueError(f"Invalid run_mode: {self.config.run_mode}")
        
        except Exception as e:
            self.logger.log_error(e, "Error in TradingBot.start()")
            self.ui_display.show_notification(f"Fatal error: {str(e)}", "ERROR")
            raise
        
        finally:
            self._shutdown()
    
    def _run_backtest(self):
        """Run backtest mode on historical data."""
        self.ui_display.show_notification("Starting backtest mode...", "INFO")
        
        try:
            # Determine which symbols to backtest
            if self.config.enable_portfolio_management and len(self.config.portfolio_symbols) > 1:
                symbols_to_test = self.config.portfolio_symbols[:self.config.portfolio_max_symbols]
                self.ui_display.show_notification(
                    f"Portfolio mode: Backtesting {len(symbols_to_test)} symbols: {', '.join(symbols_to_test)}",
                    "INFO"
                )
            else:
                symbols_to_test = [self.config.symbol]
                self.ui_display.show_notification(
                    f"Single symbol mode: Backtesting {self.config.symbol}",
                    "INFO"
                )
            
            # Store original symbol
            original_symbol = self.config.symbol
            
            # Aggregate results across all symbols
            all_trades = []
            total_pnl = 0.0
            total_balance = 10000.0  # Starting balance
            
            # Run backtest for each symbol
            for symbol_idx, symbol in enumerate(symbols_to_test, 1):
                self.ui_display.show_notification(
                    f"[{symbol_idx}/{len(symbols_to_test)}] Backtesting {symbol}...",
                    "INFO"
                )
                
                # Temporarily set the symbol for this backtest
                self.config.symbol = symbol
                
                # Fetch historical data for this symbol
                self.ui_display.show_notification(
                    f"Fetching {self.config.backtest_days} days of historical data for {symbol}...",
                    "INFO"
                )
                
                candles_15m = self.data_manager.fetch_historical_data(
                    days=self.config.backtest_days,
                    timeframe="15m",
                    symbol=symbol
                )
                
                candles_1h = self.data_manager.fetch_historical_data(
                    days=self.config.backtest_days,
                    timeframe="1h",
                    symbol=symbol
                )
                
                # Fetch additional timeframes if multi-timeframe is enabled
                candles_5m = None
                candles_4h = None
                
                if self.config.enable_multi_timeframe:
                    candles_5m = self.data_manager.fetch_historical_data(
                        days=self.config.backtest_days,
                        timeframe="5m",
                        symbol=symbol
                    )
                    
                    candles_4h = self.data_manager.fetch_historical_data(
                        days=self.config.backtest_days,
                        timeframe="4h",
                        symbol=symbol
                    )
                    
                    self.ui_display.show_notification(
                        f"[{symbol}] Fetched {len(candles_15m)} 15m, {len(candles_1h)} 1h, "
                        f"{len(candles_5m)} 5m, {len(candles_4h)} 4h candles",
                        "SUCCESS"
                    )
                else:
                    self.ui_display.show_notification(
                        f"[{symbol}] Fetched {len(candles_15m)} 15m and {len(candles_1h)} 1h candles",
                        "SUCCESS"
                    )
                
                # Run backtest for this symbol
                self.ui_display.show_notification(f"Running backtest for {symbol}...", "INFO")
                
                # Use proportional balance for each symbol in portfolio mode
                if len(symbols_to_test) > 1:
                    symbol_balance = total_balance / len(symbols_to_test)
                else:
                    symbol_balance = total_balance
                
                results = self.backtest_engine.run_backtest(
                    candles_15m=candles_15m,
                    candles_1h=candles_1h,
                    initial_balance=symbol_balance,
                    candles_5m=candles_5m,
                    candles_4h=candles_4h
                )
                
                # Collect trades from this symbol
                symbol_trades = self.backtest_engine.get_trades()
                all_trades.extend(symbol_trades)
                total_pnl += results['total_pnl']
                
                self.ui_display.show_notification(
                    f"[{symbol}] Completed: {results['total_trades']} trades, "
                    f"PnL: ${results['total_pnl']:,.2f}, Win Rate: {results['win_rate']:.1f}%",
                    "SUCCESS"
                )
            
            # Restore original symbol
            self.config.symbol = original_symbol
            
            # Calculate aggregate metrics
            winning_trades = sum(1 for t in all_trades if t.pnl > 0)
            losing_trades = sum(1 for t in all_trades if t.pnl < 0)
            total_trades = len(all_trades)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
            roi = (total_pnl / total_balance * 100) if total_balance > 0 else 0.0
            
            # Calculate other metrics
            wins = [t.pnl for t in all_trades if t.pnl > 0]
            losses = [abs(t.pnl) for t in all_trades if t.pnl < 0]
            
            average_win = sum(wins) / len(wins) if wins else 0.0
            average_loss = sum(losses) / len(losses) if losses else 0.0
            largest_win = max(wins) if wins else 0.0
            largest_loss = max(losses) if losses else 0.0
            
            gross_profit = sum(wins)
            gross_loss = sum(losses)
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
            
            # Calculate max drawdown
            equity = total_balance
            peak = equity
            max_dd = 0.0
            for trade in all_trades:
                equity += trade.pnl
                if equity > peak:
                    peak = equity
                drawdown = peak - equity
                if drawdown > max_dd:
                    max_dd = drawdown
            
            # Calculate Sharpe ratio (simplified)
            if all_trades:
                returns = [t.pnl / total_balance for t in all_trades]
                avg_return = sum(returns) / len(returns)
                std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
                sharpe_ratio = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0.0
            else:
                sharpe_ratio = 0.0
            
            # Calculate average trade duration
            durations = [(t.exit_time - t.entry_time) / 1000 / 3600 for t in all_trades]  # hours
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            
            # Convert results to PerformanceMetrics
            metrics = PerformanceMetrics(
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                roi=roi,
                max_drawdown=max_dd,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe_ratio,
                average_win=average_win,
                average_loss=average_loss,
                largest_win=largest_win,
                largest_loss=largest_loss,
                average_trade_duration=avg_duration
            )
            
            # Display results
            self.ui_display.display_backtest_results(metrics, total_balance)
            
            if len(symbols_to_test) > 1:
                self.ui_display.show_notification(
                    f"Portfolio backtest complete: {len(symbols_to_test)} symbols, "
                    f"{total_trades} total trades, ${total_pnl:,.2f} PnL",
                    "SUCCESS"
                )
            
            # Save results
            self.logger.save_performance_metrics(metrics, self.config.log_file)
            self.ui_display.show_notification(
                f"Results saved to {self.config.log_file}",
                "SUCCESS"
            )
            
            # Log all trades
            for trade in all_trades:
                self.logger.log_trade(trade)
        
        except Exception as e:
            self.logger.log_error(e, "Error during backtest execution")
            self.ui_display.show_notification(f"Backtest error: {str(e)}", "ERROR")
            raise
    
    def _run_paper_trading(self):
        """Run paper trading mode with real-time data but simulated execution."""
        self.ui_display.show_notification("Starting paper trading mode...", "INFO")
        
        # Validate API authentication
        if not self.order_executor.validate_authentication():
            raise ValueError("API authentication failed. Check your API keys and permissions.")
        
        # Validate API permissions
        if not self.order_executor.validate_permissions():
            raise ValueError("API permissions validation failed. Check your API key permissions.")
        
        # Get list of symbols to trade
        trading_symbols = self._get_trading_symbols()
        
        # Warn if portfolio management is enabled with multiple symbols
        if self.config.enable_portfolio_management and len(trading_symbols) > 1:
            self.ui_display.show_notification(
                f"[OK] Portfolio management enabled with {len(trading_symbols)} symbols: {', '.join(trading_symbols)}",
                "SUCCESS"
            )
            self.ui_display.show_notification(
                f"Portfolio risk limits: Max total risk {self.config.portfolio_max_total_risk:.0%}, "
                f"Max single allocation {self.config.portfolio_max_single_allocation:.0%}",
                "INFO"
            )
        else:
            self.ui_display.show_notification(
                f"Trading single symbol: {self.config.symbol}",
                "INFO"
            )
        
        try:
            # Get initial balance
            self.wallet_balance = self.order_executor.get_account_balance()
            self.ui_display.show_notification(
                f"Initial balance: ${self.wallet_balance:.2f}",
                "INFO"
            )
            
            # Fetch initial historical data for all symbols
            self.ui_display.show_notification(
                f"Fetching initial historical data for {len(trading_symbols)} symbol(s)...",
                "INFO"
            )
            
            self._fetch_multi_symbol_data(trading_symbols, days=7)
            
            # Verify data was fetched successfully and wait if needed
            logger.info("Verifying all symbol data is loaded...")
            all_symbols_ready = True
            
            for symbol in trading_symbols:
                buffer_5m = self.data_manager._symbol_buffers.get(symbol, {}).get('5m', [])
                buffer_4h = self.data_manager._symbol_buffers.get(symbol, {}).get('4h', [])
                buffer_15m = self.data_manager._symbol_buffers.get(symbol, {}).get('15m', [])
                buffer_1h = self.data_manager._symbol_buffers.get(symbol, {}).get('1h', [])
                
                logger.info(f"  {symbol}: 15m={len(buffer_15m)}, 1h={len(buffer_1h)}, 5m={len(buffer_5m)}, 4h={len(buffer_4h)}")
                
                # Check minimum requirements
                if len(buffer_15m) < 50 or len(buffer_1h) < 30:
                    logger.error(f"  [X] {symbol}: Insufficient base timeframe data!")
                    all_symbols_ready = False
                
                # Check multi-timeframe requirements
                if self.config.enable_multi_timeframe:
                    if len(buffer_5m) == 0:
                        logger.error(f"  [X] {symbol}: 5m buffer is EMPTY!")
                        all_symbols_ready = False
                    if len(buffer_4h) == 0:
                        logger.error(f"  [X] {symbol}: 4h buffer is EMPTY!")
                        all_symbols_ready = False
            
            if not all_symbols_ready:
                error_msg = "Failed to load required data for all symbols. Cannot start trading."
                logger.error(error_msg)
                self.ui_display.show_notification(error_msg, "ERROR")
                raise RuntimeError(error_msg)
            
            logger.info("[OK] All symbol data verified successfully")
            self.ui_display.show_notification(
                f"[OK] Data loaded for {len(trading_symbols)} symbol(s)",
                "SUCCESS"
            )
            
            # Start WebSocket streams for all symbols
            self.ui_display.show_notification(
                f"Starting WebSocket streams for {len(trading_symbols)} symbol(s)...",
                "INFO"
            )
            
            for symbol in trading_symbols:
                self.data_manager.start_websocket_streams(symbol=symbol)
                logger.info(f"Started WebSocket for {symbol}")
            
            # Give WebSocket streams time to connect and receive initial data
            self.ui_display.show_notification(
                "Waiting for WebSocket connections to stabilize...",
                "INFO"
            )
            time.sleep(3)  # Wait 3 seconds for WebSocket to connect and receive data
            
            # Start keyboard listener for panic close
            self._start_keyboard_listener()
            
            # Run main event loop
            self._run_event_loop(simulate_execution=True)
        
        except Exception as e:
            self.logger.log_error(e, "Error during paper trading")
            
            # Check if it's a network timeout error
            error_msg = str(e)
            if any(keyword in error_msg.lower() for keyword in ['timeout', 'timed out', 'connection']):
                self.ui_display.show_notification(
                    "Network timeout connecting to Binance API",
                    "ERROR"
                )
                self.ui_display.show_notification(
                    "Possible causes: 1) Slow internet connection, 2) Binance API overloaded, 3) Firewall/VPN issues",
                    "WARNING"
                )
                self.ui_display.show_notification(
                    "Try: 1) Check your internet connection, 2) Wait a few minutes and retry, 3) Disable VPN if using one",
                    "INFO"
                )
            else:
                self.ui_display.show_notification(f"Paper trading error: {str(e)}", "ERROR")
            raise
    
    def _run_live_trading(self):
        """Run live trading mode with real execution."""
        logger.info("=" * 80)
        logger.info("LIVE TRADING MODE ACTIVATED")
        logger.info("[WARNING]  REAL MONEY AT RISK [WARNING]")
        logger.info("=" * 80)
        self.ui_display.show_notification("Starting LIVE trading mode...", "WARNING")
        self.ui_display.show_notification("[WARNING]  REAL MONEY AT RISK [WARNING]", "ERROR")
        
        # Validate API authentication
        if not self.order_executor.validate_authentication():
            raise ValueError("API authentication failed. Check your API keys and permissions.")
        
        # Validate API permissions
        if not self.order_executor.validate_permissions():
            raise ValueError("API permissions validation failed. Check your API key permissions.")
        
        # Get list of symbols to trade
        trading_symbols = self._get_trading_symbols()
        
        # Warn if portfolio management is enabled with multiple symbols
        if self.config.enable_portfolio_management and len(trading_symbols) > 1:
            self.ui_display.show_notification(
                f"[OK] Portfolio management enabled with {len(trading_symbols)} symbols: {', '.join(trading_symbols)}",
                "SUCCESS"
            )
            self.ui_display.show_notification(
                f"Portfolio risk limits: Max total risk {self.config.portfolio_max_total_risk:.0%}, "
                f"Max single allocation {self.config.portfolio_max_single_allocation:.0%}",
                "INFO"
            )
        else:
            self.ui_display.show_notification(
                f"Trading single symbol: {self.config.symbol}",
                "INFO"
            )
        
        try:
            # Configure leverage and margin type for all symbols
            self.ui_display.show_notification("Configuring leverage and margin...", "INFO")
            
            for symbol in trading_symbols:
                self.order_executor.set_leverage(symbol, self.config.leverage)
                self.order_executor.set_margin_type(symbol, "ISOLATED")
                logger.info(f"Configured leverage for {symbol}")
            
            # Get initial balance
            self.wallet_balance = self.order_executor.get_account_balance()
            self.ui_display.show_notification(
                f"Initial balance: ${self.wallet_balance:.2f}",
                "INFO"
            )
            
            # Fetch initial historical data for all symbols
            self.ui_display.show_notification(
                f"Fetching initial historical data for {len(trading_symbols)} symbol(s)...",
                "INFO"
            )
            
            self._fetch_multi_symbol_data(trading_symbols, days=7)
            
            # Verify data was fetched successfully
            for symbol in trading_symbols:
                buffer_5m = self.data_manager._symbol_buffers.get(symbol, {}).get('5m', [])
                buffer_4h = self.data_manager._symbol_buffers.get(symbol, {}).get('4h', [])
                buffer_15m = self.data_manager._symbol_buffers.get(symbol, {}).get('15m', [])
                buffer_1h = self.data_manager._symbol_buffers.get(symbol, {}).get('1h', [])
                logger.info(f"Data loaded for {symbol}: 5m={len(buffer_5m)}, 15m={len(buffer_15m)}, 1h={len(buffer_1h)}, 4h={len(buffer_4h)} candles")
            
            # Start WebSocket streams for all symbols
            self.ui_display.show_notification(
                f"Starting WebSocket streams for {len(trading_symbols)} symbol(s)...",
                "INFO"
            )
            
            for symbol in trading_symbols:
                self.data_manager.start_websocket_streams(symbol=symbol)
                logger.info(f"Started WebSocket for {symbol}")
            
            # Give WebSocket streams time to connect and receive initial data
            self.ui_display.show_notification(
                "Waiting for WebSocket connections to stabilize...",
                "INFO"
            )
            time.sleep(3)  # Wait 3 seconds for WebSocket to connect and receive data
            
            # Start keyboard listener for panic close
            self._start_keyboard_listener()
            
            # Run main event loop
            self._run_event_loop(simulate_execution=False)
        
        except Exception as e:
            self.logger.log_error(e, "Error during live trading")
            
            # Check if it's a network timeout error
            error_msg = str(e)
            if any(keyword in error_msg.lower() for keyword in ['timeout', 'timed out', 'connection']):
                self.ui_display.show_notification(
                    "Network timeout connecting to Binance API",
                    "ERROR"
                )
                self.ui_display.show_notification(
                    "Possible causes: 1) Slow internet connection, 2) Binance API overloaded, 3) Firewall/VPN issues",
                    "WARNING"
                )
                self.ui_display.show_notification(
                    "Try: 1) Check your internet connection, 2) Wait a few minutes and retry, 3) Disable VPN if using one",
                    "INFO"
                )
            else:
                self.ui_display.show_notification(f"Live trading error: {str(e)}", "ERROR")
            raise
    
    def _run_event_loop(self, simulate_execution: bool = False):
        """Main event loop for real-time trading.
        
        Args:
            simulate_execution: If True, simulate order execution (paper trading)
        """
        self.running = True
        self.ui_display.show_notification("Trading bot is now running", "SUCCESS")
        self.ui_display.show_notification("Press ESC to panic close all positions", "WARNING")
        
        last_update_time = time.time()
        update_interval = 1.0  # Update dashboard every 1 second
        last_correlation_update = 0
        correlation_update_interval = 3600  # Update correlations every hour
        
        # Get list of symbols to trade
        trading_symbols = self._get_trading_symbols()
        
        try:
            while self.running and not self._panic_triggered:
                current_time = time.time()
                
                # Update dashboard at regular intervals
                if current_time - last_update_time >= update_interval:
                    self._update_dashboard()
                    last_update_time = current_time
                
                # Update correlation matrix if portfolio management is enabled
                if self.portfolio_manager and current_time - last_correlation_update >= correlation_update_interval:
                    self._update_portfolio_correlations(trading_symbols)
                    last_correlation_update = current_time
                
                # Process each symbol
                for symbol in trading_symbols:
                    self._process_symbol(symbol, simulate_execution)
                
                # Rebalance portfolio if enabled
                if self.portfolio_manager:
                    self._rebalance_portfolio(trading_symbols, simulate_execution)
                
                # Sleep briefly to avoid busy-waiting
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            self.ui_display.show_notification("Keyboard interrupt received", "WARNING")
        
        except Exception as e:
            self.logger.log_error(e, "Error in main event loop")
            self.ui_display.show_notification(f"Event loop error: {str(e)}", "ERROR")
            raise
    
    def _update_portfolio_correlations(self, symbols: List[str]):
        """Update correlation matrix for portfolio management.
        
        Args:
            symbols: List of symbols to calculate correlations for
        """
        if not self.portfolio_manager:
            return
        
        try:
            # Collect price data for all symbols
            price_data = {}
            for symbol in symbols:
                # Get 30 days of 1h candles for correlation calculation
                candles = self.data_manager.get_latest_candles("1h", 720, symbol=symbol)  # 30 days
                
                if candles and len(candles) >= 30:
                    price_data[symbol] = candles
            
            # Build correlation matrix
            if len(price_data) >= 2:
                self.portfolio_manager.build_correlation_matrix(price_data)
                logger.info("Updated portfolio correlation matrix")
        
        except Exception as e:
            logger.error(f"Error updating portfolio correlations: {e}")
    
    def _process_symbol(self, symbol: str, simulate_execution: bool):
        """Process trading logic for a single symbol.
        
        Args:
            symbol: Symbol to process
            simulate_execution: If True, simulate order execution
        """
        try:
            # CRITICAL FIX: Fetch FRESH data with use_cache=FALSE to ensure latest market data
            # This prevents the bot from using stale cached data for signal detection
            candles_15m = self.data_manager.fetch_historical_data(days=2, timeframe="15m", symbol=symbol, use_cache=False)
            candles_1h = self.data_manager.fetch_historical_data(days=2, timeframe="1h", symbol=symbol, use_cache=False)
            
            # ALWAYS fetch additional timeframes if configured (regardless of feature manager state)
            # The feature manager controls whether the strategy USES the data, not whether we FETCH it
            candles_5m = None
            candles_4h = None
            
            logger.info(f"[{symbol}] CHECK: enable_multi_timeframe = {self.config.enable_multi_timeframe}")
            
            if self.config.enable_multi_timeframe:
                logger.info(f"[{symbol}] FETCHING 5m and 4h data...")
                candles_5m = self.data_manager.get_latest_candles("5m", 300, symbol=symbol)
                candles_4h = self.data_manager.get_latest_candles("4h", 50, symbol=symbol)
                logger.info(f"[{symbol}] FETCHED 5m={len(candles_5m) if candles_5m else 0}, 4h={len(candles_4h) if candles_4h else 0}")
            else:
                logger.warning(f"[{symbol}] Multi-timeframe is DISABLED in config!")
            
            # Check if we have sufficient data
            if len(candles_15m) < 50 or len(candles_1h) < 30:
                return
            
            # Update indicators (strategy will check feature_manager internally)
            self.strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
            
            # Get current price
            current_price = candles_15m[-1].close if candles_15m else 0.0
            
            # Store indicators for this symbol (for dashboard display)
            # This will be populated with signal value later after signal detection
            self._symbol_indicators[symbol] = {
                "adx": self.strategy.current_indicators.adx,
                "rvol": self.strategy.current_indicators.rvol,
                "atr": self.strategy.current_indicators.atr_15m,
                "signal": "NONE",  # Will be updated if signal is detected
                "timestamp": time.time()
            }
            
            # Check for active position
            active_position = self.risk_manager.get_active_position(symbol)
            
            if active_position:
                # Update portfolio manager position
                if self.portfolio_manager:
                    self.portfolio_manager.update_position(symbol, active_position)
                
                # Update stops
                atr = self.strategy.current_indicators.atr_15m
                self.risk_manager.update_stops(active_position, current_price, atr)
                
                # Calculate current profit percentage
                if active_position.side == "LONG":
                    profit_pct = (current_price - active_position.entry_price) / active_position.entry_price
                else:  # SHORT
                    profit_pct = (active_position.entry_price - current_price) / active_position.entry_price
                
                # PRIORITY 1: Check for scaled take profit levels (if enabled)
                if self.config.enable_scaled_take_profit:
                    partial_close_action = self.scaled_tp_manager.check_take_profit_levels(
                        active_position, 
                        current_price
                    )
                    
                    if partial_close_action:
                        # Log TP level hit
                        logger.info(
                            f"[{symbol}] TP{partial_close_action.tp_level} hit at ${current_price:.2f} "
                            f"(target: ${partial_close_action.target_price:.2f})"
                        )
                        
                        # Execute partial close (if not simulating)
                        if not simulate_execution:
                            result = self.scaled_tp_manager.execute_partial_close(
                                active_position,
                                partial_close_action
                            )
                            
                            if result.success:
                                # Update position after partial close
                                active_position.quantity -= result.filled_quantity
                                active_position.stop_loss = partial_close_action.new_stop_loss
                                
                                # Record partial exit
                                partial_exit = {
                                    "tp_level": partial_close_action.tp_level,
                                    "exit_time": int(time.time() * 1000),
                                    "exit_price": result.fill_price,
                                    "quantity_closed": result.filled_quantity,
                                    "profit": result.realized_profit,
                                    "profit_pct": partial_close_action.profit_pct,
                                    "new_stop_loss": partial_close_action.new_stop_loss
                                }
                                active_position.partial_exits.append(partial_exit)
                                
                                # Mark TP level as hit
                                if partial_close_action.tp_level not in active_position.tp_levels_hit:
                                    active_position.tp_levels_hit.append(partial_close_action.tp_level)
                                
                                # Update balance with realized profit
                                self.wallet_balance += result.realized_profit
                                
                                # Update portfolio manager PnL
                                if self.portfolio_manager:
                                    self.portfolio_manager.update_pnl(symbol, result.realized_profit)
                                
                                # Update tracking in scaled TP manager
                                self.scaled_tp_manager.update_tracking_after_partial_close(
                                    active_position,
                                    partial_close_action.tp_level,
                                    partial_close_action.new_stop_loss
                                )
                                
                                # Log partial close
                                self.logger.log_system_event(
                                    f"[{symbol}] Partial close executed: TP{partial_close_action.tp_level} "
                                    f"closed {result.filled_quantity:.4f} at ${result.fill_price:.2f}, "
                                    f"profit: ${result.realized_profit:.2f}, "
                                    f"remaining: {active_position.quantity:.4f}, "
                                    f"new SL: ${partial_close_action.new_stop_loss:.2f}"
                                )
                                
                                # Show notification
                                pnl_text = f"+${result.realized_profit:.2f}" if result.realized_profit >= 0 else f"${result.realized_profit:.2f}"
                                profit_pct_display = partial_close_action.profit_pct * 100
                                self.ui_display.show_notification(
                                    f"[{symbol}] 🎯 TP{partial_close_action.tp_level} HIT! "
                                    f"Closed {partial_close_action.close_pct*100:.0f}% @ ${result.fill_price:.2f} | "
                                    f"PnL: {pnl_text} ({profit_pct_display:.1f}%)",
                                    "SUCCESS"
                                )
                                
                                # Check if all TP levels hit (position fully closed)
                                if len(active_position.tp_levels_hit) >= len(self.config.scaled_tp_levels):
                                    # Position fully closed via scaled TP
                                    trade = self.risk_manager.close_position(
                                        active_position,
                                        current_price,
                                        "TAKE_PROFIT"
                                    )
                                    
                                    # Update portfolio manager
                                    if self.portfolio_manager:
                                        self.portfolio_manager.update_position(symbol, None)
                                    
                                    # Reset tracking
                                    self.scaled_tp_manager.reset_tracking(symbol)
                                    
                                    # Log trade
                                    self.logger.log_trade(trade)
                                    
                                    # Show notification
                                    total_pnl = sum(pe["profit"] for pe in active_position.partial_exits)
                                    self.ui_display.show_notification(
                                        f"[{symbol}] ✅ All TP levels hit! Total PnL: ${total_pnl:.2f}",
                                        "SUCCESS"
                                    )
                            else:
                                # Partial close failed, log error
                                self.logger.log_error(
                                    f"[{symbol}] Partial close failed: {result.error_message}"
                                )
                                self.ui_display.show_notification(
                                    f"[{symbol}] ⚠️ Partial close failed: {result.error_message}",
                                    "ERROR"
                                )
                        else:
                            # Simulating execution (paper trading)
                            # Update position after simulated partial close
                            active_position.quantity -= partial_close_action.quantity
                            active_position.stop_loss = partial_close_action.new_stop_loss
                            
                            # Calculate simulated profit
                            if active_position.side == "LONG":
                                simulated_profit = (current_price - active_position.entry_price) * partial_close_action.quantity
                            else:  # SHORT
                                simulated_profit = (active_position.entry_price - current_price) * partial_close_action.quantity
                            
                            # Record partial exit
                            partial_exit = {
                                "tp_level": partial_close_action.tp_level,
                                "exit_time": int(time.time() * 1000),
                                "exit_price": current_price,
                                "quantity_closed": partial_close_action.quantity,
                                "profit": simulated_profit,
                                "profit_pct": partial_close_action.profit_pct,
                                "new_stop_loss": partial_close_action.new_stop_loss
                            }
                            active_position.partial_exits.append(partial_exit)
                            
                            # Mark TP level as hit
                            if partial_close_action.tp_level not in active_position.tp_levels_hit:
                                active_position.tp_levels_hit.append(partial_close_action.tp_level)
                            
                            # Update balance with simulated profit
                            self.wallet_balance += simulated_profit
                            
                            # Update portfolio manager PnL
                            if self.portfolio_manager:
                                self.portfolio_manager.update_pnl(symbol, simulated_profit)
                            
                            # Update tracking in scaled TP manager
                            self.scaled_tp_manager.update_tracking_after_partial_close(
                                active_position,
                                partial_close_action.tp_level,
                                partial_close_action.new_stop_loss
                            )
                            
                            # Log partial close
                            self.logger.log_system_event(
                                f"[{symbol}] Simulated partial close: TP{partial_close_action.tp_level} "
                                f"closed {partial_close_action.quantity:.4f} at ${current_price:.2f}, "
                                f"profit: ${simulated_profit:.2f}, "
                                f"remaining: {active_position.quantity:.4f}, "
                                f"new SL: ${partial_close_action.new_stop_loss:.2f}"
                            )
                            
                            # Show notification
                            pnl_text = f"+${simulated_profit:.2f}" if simulated_profit >= 0 else f"${simulated_profit:.2f}"
                            profit_pct_display = partial_close_action.profit_pct * 100
                            self.ui_display.show_notification(
                                f"[{symbol}] 🎯 TP{partial_close_action.tp_level} HIT! "
                                f"Closed {partial_close_action.close_pct*100:.0f}% @ ${current_price:.2f} | "
                                f"PnL: {pnl_text} ({profit_pct_display:.1f}%)",
                                "SUCCESS"
                            )
                            
                            # Check if all TP levels hit (position fully closed)
                            if len(active_position.tp_levels_hit) >= len(self.config.scaled_tp_levels):
                                # Position fully closed via scaled TP
                                trade = self.risk_manager.close_position(
                                    active_position,
                                    current_price,
                                    "TAKE_PROFIT"
                                )
                                
                                # Update portfolio manager
                                if self.portfolio_manager:
                                    self.portfolio_manager.update_position(symbol, None)
                                
                                # Reset tracking
                                self.scaled_tp_manager.reset_tracking(symbol)
                                
                                # Log trade
                                self.logger.log_trade(trade)
                                
                                # Show notification
                                total_pnl = sum(pe["profit"] for pe in active_position.partial_exits)
                                self.ui_display.show_notification(
                                    f"[{symbol}] ✅ All TP levels hit! Total PnL: ${total_pnl:.2f}",
                                    "SUCCESS"
                                )
                        
                        # Skip regular TP check since we're using scaled TP
                        # Continue to stop loss check
                
                # PRIORITY 2: Check if regular take profit target is reached (only if scaled TP not enabled or not triggered)
                elif profit_pct >= self.config.take_profit_pct:
                    # Close position at take profit
                    trade = self.risk_manager.close_position(
                        active_position,
                        current_price,
                        "TAKE_PROFIT"
                    )
                    
                    # Execute close order (if not simulating)
                    if not simulate_execution:
                        side = "SELL" if active_position.side == "LONG" else "BUY"
                        self.order_executor.place_market_order(
                            symbol=symbol,
                            side=side,
                            quantity=active_position.quantity,
                            reduce_only=True
                        )
                    
                    # Update balance
                    self.wallet_balance += trade.pnl
                    
                    # Update portfolio manager PnL
                    if self.portfolio_manager:
                        self.portfolio_manager.update_pnl(symbol, trade.pnl)
                        self.portfolio_manager.update_position(symbol, None)
                    
                    # Reset scaled TP tracking if enabled
                    if self.config.enable_scaled_take_profit:
                        self.scaled_tp_manager.reset_tracking(symbol)
                    
                    # Log trade
                    self.logger.log_trade(trade)
                    
                    # Show notification
                    pnl_text = f"+${trade.pnl:.2f}" if trade.pnl >= 0 else f"${trade.pnl:.2f}"
                    profit_pct_display = profit_pct * 100
                    self.ui_display.show_notification(
                        f"[{symbol}] 🎯 TAKE PROFIT HIT! {trade.side} @ ${trade.exit_price:.2f} | PnL: {pnl_text} ({profit_pct_display:.2f}%)",
                        "SUCCESS"
                    )
                
                # PRIORITY 3: Check if stop was hit
                elif self.risk_manager.check_stop_hit(active_position, current_price):
                    # Close position
                    trade = self.risk_manager.close_position(
                        active_position,
                        current_price,
                        "TRAILING_STOP"
                    )
                    
                    # Execute close order (if not simulating)
                    if not simulate_execution:
                        side = "SELL" if active_position.side == "LONG" else "BUY"
                        self.order_executor.place_market_order(
                            symbol=symbol,
                            side=side,
                            quantity=active_position.quantity,
                            reduce_only=True
                        )
                    
                    # Update balance
                    self.wallet_balance += trade.pnl
                    
                    # Update portfolio manager PnL
                    if self.portfolio_manager:
                        self.portfolio_manager.update_pnl(symbol, trade.pnl)
                        self.portfolio_manager.update_position(symbol, None)
                    
                    # Reset scaled TP tracking if enabled
                    if self.config.enable_scaled_take_profit:
                        self.scaled_tp_manager.reset_tracking(symbol)
                    
                    # Log trade
                    self.logger.log_trade(trade)
                    
                    # Show notification
                    pnl_text = f"+${trade.pnl:.2f}" if trade.pnl >= 0 else f"${trade.pnl:.2f}"
                    self.ui_display.show_notification(
                        f"[{symbol}] Position closed: {trade.side} @ ${trade.exit_price:.2f} | PnL: {pnl_text}",
                        "SUCCESS" if trade.pnl >= 0 else "WARNING"
                    )
            
            else:
                # No active position, check for entry signals
                if self.risk_manager.is_signal_generation_enabled():
                    # DEBUG: Log current indicators BEFORE checking signals
                    ind = self.strategy.current_indicators
                    logger.info(f"[{symbol}] INDICATORS: ADX={ind.adx:.2f}, RVOL={ind.rvol:.2f}, SqzColor={ind.squeeze_color}, SqzVal={ind.squeeze_value:.4f}, Trend15m={ind.trend_15m}, Trend1h={ind.trend_1h}, PriceVsVWAP={ind.price_vs_vwap}")
                    
                    long_signal = self.strategy.check_long_entry(symbol)
                    short_signal = self.strategy.check_short_entry(symbol)
                    
                    # Update stored indicators with signal value
                    if symbol in self._symbol_indicators:
                        if long_signal:
                            self._symbol_indicators[symbol]["signal"] = "LONG"
                        elif short_signal:
                            self._symbol_indicators[symbol]["signal"] = "SHORT"
                        else:
                            self._symbol_indicators[symbol]["signal"] = "NONE"
                    
                    # DEBUG LOGGING
                    logger.info(f"[{symbol}] Signal check: LONG={long_signal is not None}, SHORT={short_signal is not None}")
                    if long_signal:
                        logger.info(f"[{symbol}] 🎯 LONG SIGNAL DETECTED! Price=${long_signal.price:.4f}")
                    if short_signal:
                        logger.info(f"[{symbol}] 🎯 SHORT SIGNAL DETECTED! Price=${short_signal.price:.4f}")
                    
                    signal = long_signal or short_signal
                    
                    if signal:
                        logger.info(f"[{symbol}] [OK] Signal exists, proceeding to open position...")
                        # Check portfolio risk limits if portfolio management is enabled
                        if self.portfolio_manager:
                            if not self.portfolio_manager.check_total_risk(self.wallet_balance):
                                logger.info(f"Skipping {symbol} signal - portfolio risk limit exceeded")
                                return
                        
                        # Open position
                        atr = self.strategy.current_indicators.atr_15m
                        logger.info(f"[{symbol}] Opening position: ATR=${atr:.4f}, Balance=${self.wallet_balance:.2f}")
                        position = self.risk_manager.open_position(
                            signal,
                            self.wallet_balance,
                            atr
                        )
                        logger.info(f"[{symbol}] [OK] Position created: {position.side} qty={position.quantity:.4f} @ ${position.entry_price:.4f}")
                        
                        # CRITICAL FIX: Check if portfolio manager allows this position
                        # If not allowed, remove it from risk manager immediately (before execution)
                        if self.portfolio_manager:
                            if not self.portfolio_manager.can_add_position(symbol, position, self.wallet_balance):
                                logger.info(f"[{symbol}] Skipping signal - would exceed portfolio risk limits")
                                # Remove position from risk manager's active positions
                                if symbol in self.risk_manager.active_positions:
                                    del self.risk_manager.active_positions[symbol]
                                logger.info(f"[{symbol}] Position removed from risk manager (not executed)")
                                return
                        
                        # Execute entry order (if not simulating)
                        logger.info(f"[{symbol}] Checking if should execute order (simulate={simulate_execution})...")
                        if not simulate_execution:
                            logger.info(f"[{symbol}] =" * 40)
                            logger.info(f"[{symbol}] EXECUTING REAL ORDER ON BINANCE")
                            logger.info(f"[{symbol}] Symbol: {symbol}")
                            logger.info(f"[{symbol}] Side: {position.side}")
                            logger.info(f"[{symbol}] Quantity: {position.quantity}")
                            logger.info(f"[{symbol}] Entry Price: {position.entry_price}")
                            logger.info(f"[{symbol}] =" * 40)
                            
                            # Validate margin availability
                            margin_required = (position.entry_price * position.quantity) / position.leverage
                            logger.info(f"[{symbol}] Margin required: ${margin_required:.2f}, Available: ${self.wallet_balance:.2f}")
                            
                            if self.order_executor.validate_margin_availability(
                                symbol,
                                margin_required
                            ):
                                logger.info(f"[{symbol}] [OK] Margin validated, placing order...")
                                side = "BUY" if position.side == "LONG" else "SELL"
                                self.order_executor.place_market_order(
                                    symbol=symbol,
                                    side=side,
                                    quantity=position.quantity
                                )
                                logger.info(f"[{symbol}] ✅ ORDER EXECUTED: {side} {position.quantity:.4f} @ market")
                            else:
                                # Insufficient margin, close position
                                self.risk_manager.close_position(
                                    position,
                                    current_price,
                                    "SIGNAL_EXIT"
                                )
                                self.ui_display.show_notification(
                                    f"[{symbol}] Insufficient margin for trade",
                                    "ERROR"
                                )
                                return
                        
                        # Update portfolio manager
                        if self.portfolio_manager:
                            self.portfolio_manager.update_position(symbol, position)
                        
                        # Show notification
                        self.ui_display.show_notification(
                            f"[{symbol}] Position opened: {position.side} @ ${position.entry_price:.2f}",
                            "SUCCESS"
                        )
        
        except Exception as e:
            logger.error(f"Error processing symbol {symbol}: {e}")
    
    def _rebalance_portfolio(self, symbols: List[str], simulate_execution: bool):
        """Rebalance portfolio allocations if needed.
        
        Args:
            symbols: List of symbols in portfolio
            simulate_execution: If True, simulate order execution
        """
        if not self.portfolio_manager:
            return
        
        try:
            # Collect signals for all symbols
            signals = {}
            for symbol in symbols:
                # Get latest candles
                candles_15m = self.data_manager.get_latest_candles("15m", 200, symbol=symbol)
                candles_1h = self.data_manager.get_latest_candles("1h", 100, symbol=symbol)
                
                if len(candles_15m) >= 50 and len(candles_1h) >= 30:
                    # Update indicators
                    self.strategy.update_indicators(candles_15m, candles_1h)
                    
                    # Check for signals
                    long_signal = self.strategy.check_long_entry(symbol)
                    short_signal = self.strategy.check_short_entry(symbol)
                    
                    signal = long_signal or short_signal
                    if signal:
                        signals[symbol] = signal
            
            # Rebalance if needed
            if signals:
                new_allocations = self.portfolio_manager.rebalance_portfolio(
                    signals,
                    self.wallet_balance
                )
                
                if new_allocations:
                    logger.info(f"Portfolio rebalanced: {new_allocations}")
        
        except Exception as e:
            logger.error(f"Error rebalancing portfolio: {e}")
    
    def _update_dashboard(self):
        """Update the terminal dashboard with current state."""
        try:
            # Get active positions and trades
            positions = self.risk_manager.get_all_active_positions()
            trades = self.risk_manager.get_closed_trades()
            
            # Get current indicators
            indicators = self.strategy.get_indicator_snapshot()
            
            # Get advanced features data
            advanced_features = self.strategy.get_advanced_features_data()
            
            # Log rate limiter stats periodically (every 10 updates)
            if not hasattr(self, '_dashboard_update_count'):
                self._dashboard_update_count = 0
            self._dashboard_update_count += 1
            
            if self._dashboard_update_count % 10 == 0:
                rate_stats = self.data_manager.rate_limiter.get_stats()
                logger.debug(
                    f"Rate limiter: {rate_stats['current_requests_per_minute']}/{rate_stats['max_requests_per_minute']} "
                    f"requests/min ({rate_stats['utilization_percent']:.1f}% utilization)"
                )
            
            # Save real-time state to binance_results.json for Streamlit dashboard
            self._save_realtime_state(positions, indicators)
            
            # Render dashboard
            dashboard = self.ui_display.render_dashboard(
                positions=positions,
                trades=trades,
                indicators=indicators,
                wallet_balance=self.wallet_balance,
                mode=self.config.run_mode,
                market_regime=advanced_features.get('market_regime'),
                ml_prediction=advanced_features.get('ml_prediction'),
                volume_profile=advanced_features.get('volume_profile'),
                adaptive_thresholds=advanced_features.get('adaptive_thresholds')
            )
            
            # Clear screen and print dashboard
            self.ui_display.clear_screen()
            self.ui_display.console.print(dashboard)
        
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
    
    def _save_realtime_state(self, positions: List, indicators: Dict):
        """Save real-time bot state to binance_results.json for Streamlit dashboard.
        
        Args:
            positions: List of active positions
            indicators: Current indicator values
        """
        try:
            import json
            from datetime import datetime
            
            # Calculate total PnL from closed trades
            closed_trades = self.risk_manager.get_closed_trades()
            total_pnl = sum(trade.pnl for trade in closed_trades)
            total_pnl_percent = (total_pnl / self.wallet_balance * 100) if self.wallet_balance > 0 else 0.0
            
            # Get current price from primary symbol
            current_price = 0.0
            if positions:
                # Use price from first position's symbol
                try:
                    candles = self.data_manager.get_latest_candles("15m", 1, symbol=positions[0].symbol)
                    if candles:
                        current_price = candles[-1].close
                except:
                    current_price = indicators.get('current_price', 0.0)
            else:
                current_price = indicators.get('current_price', 0.0)
            
            # Format positions for JSON with correct current prices
            positions_data = []
            for pos in positions:
                # Get current price for this specific symbol
                try:
                    symbol_candles = self.data_manager.get_latest_candles("15m", 1, symbol=pos.symbol)
                    symbol_price = symbol_candles[-1].close if symbol_candles else 0.0
                except:
                    symbol_price = 0.0
                
                positions_data.append({
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "entry_price": pos.entry_price,
                    "current_price": symbol_price,
                    "quantity": pos.quantity,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "stop_loss": pos.stop_loss,
                    "trailing_stop": pos.trailing_stop,
                    "entry_time": pos.entry_time.isoformat() if hasattr(pos.entry_time, 'isoformat') else str(pos.entry_time)
                })
            
            # Get list of all trading symbols (from portfolio or single symbol)
            trading_symbols = self._get_trading_symbols()
            
            # Collect per-symbol market data
            symbols_data = []
            for symbol in trading_symbols:
                try:
                    # Get latest candles for this symbol
                    symbol_candles = self.data_manager.get_latest_candles("15m", 1, symbol=symbol)
                    symbol_price = symbol_candles[-1].close if symbol_candles else 0.0
                    
                    # Get stored indicators for this symbol
                    if symbol in self._symbol_indicators:
                        stored = self._symbol_indicators[symbol]
                        symbol_adx = stored.get("adx", 0.0)
                        symbol_rvol = stored.get("rvol", 0.0)
                        symbol_atr = stored.get("atr", 0.0)
                        symbol_signal = stored.get("signal", "NONE")
                    else:
                        # Symbol not processed yet
                        symbol_adx = 0.0
                        symbol_rvol = 0.0
                        symbol_atr = 0.0
                        symbol_signal = "NONE"
                    
                    symbols_data.append({
                        "symbol": symbol,
                        "current_price": symbol_price,
                        "adx": symbol_adx,
                        "rvol": symbol_rvol,
                        "atr": symbol_atr,
                        "signal": symbol_signal
                    })
                except Exception as e:
                    logger.debug(f"Error getting data for {symbol}: {e}")
                    continue
            
            # Build state data with correct indicators
            state_data = {
                "timestamp": datetime.now().isoformat(),
                "bot_status": "running",
                "run_mode": self.config.run_mode,
                "balance": self.wallet_balance,
                "total_pnl": total_pnl,
                "total_pnl_percent": total_pnl_percent,
                "open_positions": positions_data,
                "current_price": current_price,
                "adx": indicators.get('adx_15m', indicators.get('adx', 0.0)),
                "rvol": indicators.get('rvol_15m', indicators.get('rvol', 0.0)),
                "atr": indicators.get('atr_15m', indicators.get('atr', 0.0)),
                "signal": indicators.get('signal', 'NONE'),
                "symbols_data": symbols_data,  # NEW: Per-symbol market data
                "total_trades": len(closed_trades),
                "winning_trades": sum(1 for t in closed_trades if t.pnl > 0),
                "losing_trades": sum(1 for t in closed_trades if t.pnl <= 0)
            }
            
            # Save to file
            with open(self.config.log_file, 'w') as f:
                json.dump(state_data, f, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving realtime state: {e}")
    
    def _start_keyboard_listener(self):
        """Start keyboard listener for panic close (ESC key).
        
        Only available on systems with display support. Silently skips on headless servers.
        """
        if not KEYBOARD_AVAILABLE:
            logger.info("Keyboard listener not available (headless mode - use API/signals for panic close)")
            return
        
        try:
            def on_press(key):
                try:
                    if key == keyboard.Key.esc:
                        self._trigger_panic_close()
                except Exception as e:
                    logger.error(f"Error in keyboard listener: {e}")
            
            self.keyboard_listener = keyboard.Listener(on_press=on_press)
            self.keyboard_listener.start()
            logger.info("Keyboard listener started (ESC for panic close)")
        except Exception as e:
            logger.warning(f"Could not start keyboard listener: {e}. Running in headless mode.")
    
    def _trigger_panic_close(self):
        """Trigger emergency panic close of all positions."""
        if self._panic_triggered:
            return  # Already triggered
        
        self._panic_triggered = True
        self.ui_display.show_notification("🚨 PANIC CLOSE TRIGGERED 🚨", "ERROR")
        
        try:
            # Get current price
            candles_15m = self.data_manager.get_latest_candles("15m", 1)
            current_price = candles_15m[-1].close if candles_15m else 0.0
            
            # Close all positions
            closed_trades = self.risk_manager.close_all_positions(current_price)
            
            # Execute close orders (if in LIVE mode)
            if self.config.run_mode == "LIVE":
                for trade in closed_trades:
                    side = "SELL" if trade.side == "LONG" else "BUY"
                    # Note: In production, we'd need to get the actual position quantity
                    # For now, we use the trade quantity
                    self.order_executor.place_market_order(
                        symbol=self.config.symbol,
                        side=side,
                        quantity=trade.quantity,
                        reduce_only=True
                    )
            
            # Calculate total PnL
            total_pnl = sum(trade.pnl for trade in closed_trades)
            
            # Update balance
            self.wallet_balance += total_pnl
            
            # Log all trades
            for trade in closed_trades:
                self.logger.log_trade(trade)
            
            # Show confirmation
            self.ui_display.show_panic_confirmation(len(closed_trades), total_pnl)
            
            # Stop the bot
            self.running = False
        
        except Exception as e:
            self.logger.log_error(e, "Error during panic close")
            self.ui_display.show_notification(f"Panic close error: {str(e)}", "ERROR")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    def _shutdown(self):
        """Perform graceful shutdown and cleanup."""
        self.logger.log_system_event("Initiating graceful shutdown")
        self.ui_display.show_notification("Shutting down...", "INFO")
        
        try:
            # Stop keyboard listener
            if self.keyboard_listener is not None:
                self.keyboard_listener.stop()
                logger.info("Keyboard listener stopped")
            
            # Stop WebSocket streams
            if self.config.run_mode in ["PAPER", "LIVE"]:
                self.data_manager.stop_websocket_streams()
                logger.info("WebSocket streams stopped")
            
            # Close any remaining positions (if not already closed by panic)
            if not self._panic_triggered:
                active_positions = self.risk_manager.get_all_active_positions()
                if active_positions:
                    self.ui_display.show_notification(
                        f"Closing {len(active_positions)} open position(s)...",
                        "WARNING"
                    )
                    
                    # Try to get current price, use entry price as fallback
                    try:
                        candles_15m = self.data_manager.get_latest_candles("15m", 1)
                        current_price = candles_15m[-1].close if candles_15m else 0.0
                    except:
                        current_price = 0.0
                    
                    # If we can't get current price, use position entry prices
                    if current_price <= 0 and active_positions:
                        # Close positions individually with their own prices
                        for pos in active_positions:
                            try:
                                symbol_candles = self.data_manager.get_latest_candles("15m", 1, symbol=pos.symbol)
                                pos_price = symbol_candles[-1].close if symbol_candles else pos.entry_price
                                trade = self.risk_manager.close_position(pos, pos_price, "PANIC")
                                if trade:
                                    self.logger.log_trade(trade)
                            except Exception as e:
                                logger.error(f"Error closing position {pos.symbol}: {e}")
                    else:
                        # Close all with same price
                        closed_trades = self.risk_manager.close_all_positions(current_price)
                        
                        # Log trades
                        for trade in closed_trades:
                            self.logger.log_trade(trade)
            
            # Save final performance metrics (if in PAPER or LIVE mode)
            if self.config.run_mode in ["PAPER", "LIVE"]:
                trades = self.risk_manager.get_closed_trades()
                if trades:
                    # Calculate metrics
                    total_trades = len(trades)
                    winning_trades = sum(1 for t in trades if t.pnl > 0)
                    losing_trades = sum(1 for t in trades if t.pnl <= 0)
                    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
                    total_pnl = sum(t.pnl for t in trades)
                    
                    metrics = PerformanceMetrics(
                        total_trades=total_trades,
                        winning_trades=winning_trades,
                        losing_trades=losing_trades,
                        win_rate=win_rate,
                        total_pnl=total_pnl
                    )
                    
                    self.logger.save_performance_metrics(metrics, self.config.log_file)
            
            self.logger.log_system_event("Shutdown complete")
            self.ui_display.show_notification("Shutdown complete", "SUCCESS")
        
        except Exception as e:
            self.logger.log_error(e, "Error during shutdown")
            logger.error(f"Shutdown error: {e}")


def main():
    """Main entry point for the trading bot."""
    try:
        # Load configuration
        config = Config.load_from_file()
        
        # Log applied defaults
        defaults = config.get_applied_defaults()
        if defaults:
            logger.info("Applied default configuration values:")
            for default in defaults:
                logger.info(f"  - {default}")
        
        # Create and start trading bot
        bot = TradingBot(config)
        bot.start()
    
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n❌ Configuration Error:\n{e}\n")
        sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("\n\n👋 Goodbye!\n")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal Error:\n{e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
