"""Risk management and position tracking for Binance Futures Trading Bot."""

import time
import logging
from typing import Dict, List, Optional
from src.config import Config
from src.models import Position, Trade, Signal
from src.position_sizer import PositionSizer
from src.advanced_exit_manager import AdvancedExitManager
from src.portfolio_manager import PortfolioManager
from src.feature_manager import FeatureManager

# Configure logging
logger = logging.getLogger(__name__)


class RiskManager:
    """Manages open positions, stop-loss levels, and risk controls.
    
    Responsible for:
    - Opening positions with calculated size and stops
    - Updating trailing stops as price moves favorably
    - Detecting stop-loss triggers
    - Closing positions and generating trade records
    - Emergency panic close functionality
    - Advanced exit management (partial exits, time-based, regime-based)
    - Portfolio-level risk management across multiple symbols
    """
    
    def __init__(self, config: Config, position_sizer: PositionSizer):
        """Initialize RiskManager with configuration and position sizer.
        
        Args:
            config: Configuration object containing risk parameters
            position_sizer: PositionSizer instance for calculating sizes and stops
        """
        self.config = config
        self.position_sizer = position_sizer
        self.active_positions: Dict[str, Position] = {}
        self.closed_trades: List[Trade] = []
        self._signal_generation_enabled = True
        
        # Initialize feature manager for error isolation
        self.feature_manager = FeatureManager(max_errors=3, error_window=300.0)
        
        # Initialize AdvancedExitManager if enabled
        self.advanced_exit_manager: Optional[AdvancedExitManager] = None
        if config.enable_advanced_exits:
            try:
                self.advanced_exit_manager = AdvancedExitManager(config)
                self.feature_manager.register_feature("advanced_exits", enabled=True)
                logger.info("AdvancedExitManager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize AdvancedExitManager: {e}")
                self.feature_manager.register_feature("advanced_exits", enabled=False)
        
        # Initialize PortfolioManager if enabled
        self.portfolio_manager: Optional[PortfolioManager] = None
        if config.enable_portfolio_management:
            try:
                self.portfolio_manager = PortfolioManager(config)
                self.feature_manager.register_feature("portfolio_management", enabled=True)
                logger.info("PortfolioManager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize PortfolioManager: {e}")
                self.feature_manager.register_feature("portfolio_management", enabled=False)
        
        # Track current regime for regime-based exits
        self.current_regime: str = "UNCERTAIN"
        self.previous_regime: str = "UNCERTAIN"
    
    def open_position(
        self, 
        signal: Signal, 
        wallet_balance: float, 
        atr: float
    ) -> Position:
        """Create new position with calculated size and stops.
        
        Calculates position size based on 1% risk rule, sets initial stop-loss
        at 2x ATR, and initializes trailing stop at the same level.
        
        If PortfolioManager is enabled, checks portfolio-level risk limits before
        opening the position.
        
        Args:
            signal: Entry signal containing type, price, and timestamp
            wallet_balance: Current wallet balance in quote currency (USDT)
            atr: Current Average True Range value
            
        Returns:
            Position object with all parameters set
            
        Raises:
            ValueError: If signal type is invalid or inputs are invalid
            RuntimeError: If portfolio risk limits would be exceeded
        """
        # Validate signal type
        if signal.type not in ["LONG_ENTRY", "SHORT_ENTRY"]:
            raise ValueError(f"Invalid signal type for opening position: {signal.type}")
        
        # Determine position side
        side = "LONG" if signal.type == "LONG_ENTRY" else "SHORT"
        
        # Calculate position size and stops
        sizing_result = self.position_sizer.calculate_position_size(
            wallet_balance=wallet_balance,
            entry_price=signal.price,
            atr=atr
        )
        
        # Calculate initial stop-loss price based on position side
        if side == "LONG":
            # For long positions, stop is below entry
            stop_loss_price = signal.price - sizing_result['stop_loss_distance']
        else:
            # For short positions, stop is above entry
            stop_loss_price = signal.price + sizing_result['stop_loss_distance']
        
        # Create position object
        position = Position(
            symbol=signal.symbol if signal.symbol is not None else self.config.symbol,
            side=side,
            entry_price=signal.price,
            quantity=sizing_result['quantity'],
            leverage=self.config.leverage,
            stop_loss=stop_loss_price,
            trailing_stop=stop_loss_price,  # Initially same as stop_loss
            entry_time=signal.timestamp,
            unrealized_pnl=0.0
        )
        
        # Check portfolio risk limits if PortfolioManager is enabled
        if self.portfolio_manager and self.feature_manager.is_feature_enabled("portfolio_management"):
            can_add = self.feature_manager.execute_feature(
                "portfolio_management",
                self.portfolio_manager.can_add_position,
                position.symbol, position, wallet_balance,
                default_value=True
            )
            
            if not can_add:
                raise RuntimeError(
                    f"Cannot open position for {position.symbol}: "
                    f"would exceed portfolio risk limits"
                )
            
            # Update portfolio manager with new position
            self.feature_manager.execute_feature(
                "portfolio_management",
                self.portfolio_manager.update_position,
                position.symbol, position
            )
            logger.info(f"Portfolio updated with new position: {position.symbol}")
        
        # Store position in active positions
        self.active_positions[position.symbol] = position
        
        logger.info(
            f"Position opened: {position.symbol} {position.side} "
            f"qty={position.quantity:.4f} at {position.entry_price:.2f}, "
            f"stop={stop_loss_price:.2f}"
        )
        
        return position
    
    def update_stops(self, position: Position, current_price: float, atr: float, momentum_reversed: bool = False) -> None:
        """Update trailing stop-loss if price moves favorably.
        
        Only tightens stops, never widens them. For long positions, moves stop up.
        For short positions, moves stop down.
        
        If AdvancedExitManager is enabled, also updates dynamic stops based on
        profit levels and momentum.
        
        Args:
            position: Position to update
            current_price: Current market price
            atr: Current Average True Range value
            momentum_reversed: Whether momentum has reversed (for advanced exits)
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Calculate new trailing stop using position sizer
        new_trailing_stop = self.position_sizer.calculate_trailing_stop(
            position=position,
            current_price=current_price,
            atr=atr
        )
        
        # Update position's trailing stop
        position.trailing_stop = new_trailing_stop
        
        # Update unrealized PnL
        if position.side == "LONG":
            position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
        else:  # SHORT
            position.unrealized_pnl = (position.entry_price - current_price) * position.quantity
        
        # Apply advanced exit management if enabled
        if self.advanced_exit_manager and self.feature_manager.is_feature_enabled("advanced_exits"):
            self.feature_manager.execute_feature(
                "advanced_exits",
                self.advanced_exit_manager.update_dynamic_stops,
                position=position,
                current_price=current_price,
                atr=atr,
                momentum_reversed=momentum_reversed
            )
    
    def check_stop_hit(self, position: Position, current_price: float) -> bool:
        """Check if stop-loss or trailing stop is hit.
        
        For long positions: stop is hit if price <= trailing_stop
        For short positions: stop is hit if price >= trailing_stop
        
        Args:
            position: Position to check
            current_price: Current market price
            
        Returns:
            True if stop is hit, False otherwise
            
        Raises:
            ValueError: If position side is invalid
        """
        if position.side == "LONG":
            # For long positions, stop is hit if price drops to or below stop
            return current_price <= position.trailing_stop
        elif position.side == "SHORT":
            # For short positions, stop is hit if price rises to or above stop
            return current_price >= position.trailing_stop
        else:
            raise ValueError(f"Invalid position side: {position.side}")
    
    def check_partial_exit(self, position: Position, current_price: float, atr: float) -> Optional[float]:
        """Check if partial exit should be triggered.
        
        Uses AdvancedExitManager if enabled to check for partial profit taking.
        
        Args:
            position: Position to check
            current_price: Current market price
            atr: Current Average True Range value
            
        Returns:
            Percentage to close (0.0-1.0) if partial exit triggered, None otherwise
        """
        if not self.advanced_exit_manager or not self.feature_manager.is_feature_enabled("advanced_exits"):
            return None
        
        return self.feature_manager.execute_feature(
            "advanced_exits",
            self.advanced_exit_manager.check_partial_exits,
            position=position,
            current_price=current_price,
            atr=atr,
            default_value=None
        )
    
    def check_time_based_exit(self, position: Position) -> bool:
        """Check if position should be closed due to time limit.
        
        Uses AdvancedExitManager if enabled.
        
        Args:
            position: Position to check
            
        Returns:
            True if time limit exceeded, False otherwise
        """
        if not self.advanced_exit_manager or not self.feature_manager.is_feature_enabled("advanced_exits"):
            return False
        
        return self.feature_manager.execute_feature(
            "advanced_exits",
            self.advanced_exit_manager.check_time_based_exit,
            position,
            default_value=False
        )
    
    def check_regime_exit(self, position: Position) -> bool:
        """Check if position should be closed due to regime change.
        
        Uses AdvancedExitManager if enabled.
        
        Args:
            position: Position to check
            
        Returns:
            True if regime-based exit triggered, False otherwise
        """
        if not self.advanced_exit_manager or not self.feature_manager.is_feature_enabled("advanced_exits"):
            return False
        
        return self.feature_manager.execute_feature(
            "advanced_exits",
            self.advanced_exit_manager.check_regime_exit,
            position=position,
            current_regime=self.current_regime,
            previous_regime=self.previous_regime,
            default_value=False
        )
    
    def update_regime(self, new_regime: str) -> None:
        """Update current market regime.
        
        Tracks regime changes for regime-based exits.
        
        Args:
            new_regime: New market regime
        """
        self.previous_regime = self.current_regime
        self.current_regime = new_regime
        
        if self.previous_regime != self.current_regime:
            logger.info(f"Regime changed: {self.previous_regime} -> {self.current_regime}")
    
    def execute_partial_exit(
        self, 
        position: Position, 
        exit_price: float, 
        percentage: float
    ) -> Trade:
        """Execute partial exit of a position.
        
        Reduces position size by the specified percentage and creates a trade record.
        
        Args:
            position: Position to partially close
            exit_price: Price at which to close
            percentage: Percentage to close (0.0-1.0)
            
        Returns:
            Trade object for the partial exit
            
        Raises:
            ValueError: If percentage is invalid
        """
        if not 0.0 < percentage <= 1.0:
            raise ValueError(f"Invalid percentage: {percentage}. Must be between 0 and 1")
        
        # Calculate quantity to close
        close_quantity = position.quantity * percentage
        
        # Calculate PnL for closed portion
        if position.side == "LONG":
            pnl = (exit_price - position.entry_price) * close_quantity
        else:  # SHORT
            pnl = (position.entry_price - exit_price) * close_quantity
        
        # Calculate PnL percentage
        position_value = position.entry_price * close_quantity
        pnl_percent = (pnl / position_value) * 100 if position_value > 0 else 0.0
        
        # Create trade record
        exit_time = int(time.time() * 1000)
        trade = Trade(
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=close_quantity,
            pnl=pnl,
            pnl_percent=pnl_percent,
            entry_time=position.entry_time,
            exit_time=exit_time,
            exit_reason=f"PARTIAL_EXIT_{int(percentage * 100)}%"
        )
        
        # Store trade
        self.closed_trades.append(trade)
        
        # Reduce position size
        position.quantity -= close_quantity
        
        # Update unrealized PnL
        if position.side == "LONG":
            position.unrealized_pnl = (exit_price - position.entry_price) * position.quantity
        else:
            position.unrealized_pnl = (position.entry_price - exit_price) * position.quantity
        
        logger.info(
            f"Partial exit executed: {position.symbol} {position.side} "
            f"{percentage*100:.0f}% at {exit_price:.2f}, PnL: {pnl:.2f} ({pnl_percent:.2f}%)"
        )
        
        return trade
    
    def close_position(
        self, 
        position: Position, 
        exit_price: float, 
        reason: str
    ) -> Trade:
        """Close position and return trade record.
        
        Calculates final PnL and creates a Trade object with all details.
        Removes position from active positions and updates portfolio manager.
        
        Args:
            position: Position to close
            exit_price: Price at which position is closed
            reason: Exit reason ("STOP_LOSS", "TRAILING_STOP", "SIGNAL_EXIT", "PANIC", "TIME_BASED", "REGIME_CHANGE")
            
        Returns:
            Trade object with complete trade details
            
        Raises:
            ValueError: If exit reason is invalid or inputs are invalid
        """
        # Validate exit reason
        valid_reasons = ["STOP_LOSS", "TRAILING_STOP", "SIGNAL_EXIT", "PANIC", "TIME_BASED", "REGIME_CHANGE"]
        if reason not in valid_reasons:
            raise ValueError(f"Invalid exit reason: {reason}. Must be one of: {', '.join(valid_reasons)}")
        
        # Validate exit price
        if exit_price <= 0:
            raise ValueError(f"exit_price must be positive, got {exit_price}")
        
        # Calculate PnL
        if position.side == "LONG":
            # For long: profit when exit > entry
            pnl = (exit_price - position.entry_price) * position.quantity
        else:  # SHORT
            # For short: profit when entry > exit
            pnl = (position.entry_price - exit_price) * position.quantity
        
        # Calculate PnL percentage
        position_value = position.entry_price * position.quantity
        pnl_percent = (pnl / position_value) * 100 if position_value > 0 else 0.0
        
        # Get current timestamp
        exit_time = int(time.time() * 1000)  # milliseconds
        
        # Create trade record
        trade = Trade(
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            pnl=pnl,
            pnl_percent=pnl_percent,
            entry_time=position.entry_time,
            exit_time=exit_time,
            exit_reason=reason
        )
        
        # Store trade in closed trades
        self.closed_trades.append(trade)
        
        # Update portfolio manager if enabled
        if self.portfolio_manager and self.feature_manager.is_feature_enabled("portfolio_management"):
            self.feature_manager.execute_feature(
                "portfolio_management",
                self.portfolio_manager.update_position,
                position.symbol, None
            )
            self.feature_manager.execute_feature(
                "portfolio_management",
                self.portfolio_manager.update_pnl,
                position.symbol, pnl
            )
            logger.debug(f"Portfolio updated: {position.symbol} position closed, PnL: {pnl:.2f}")
        
        # Remove position from active positions
        if position.symbol in self.active_positions:
            del self.active_positions[position.symbol]
        
        # Reset exit tracking in AdvancedExitManager
        if self.advanced_exit_manager and self.feature_manager.is_feature_enabled("advanced_exits"):
            self.feature_manager.execute_feature(
                "advanced_exits",
                self.advanced_exit_manager.reset_exit_tracking,
                position.symbol
            )
        
        logger.info(
            f"Position closed: {position.symbol} {position.side} at {exit_price:.2f}, "
            f"PnL: {pnl:.2f} ({pnl_percent:.2f}%), Reason: {reason}"
        )
        
        return trade
    
    def close_all_positions(self, current_price: float) -> List[Trade]:
        """Emergency close all positions (panic button).
        
        Closes all active positions at current market price with "PANIC" reason.
        Disables signal generation after panic close.
        
        Args:
            current_price: Current market price for closing positions
            
        Returns:
            List of Trade objects for all closed positions
            
        Raises:
            ValueError: If current_price is invalid
        """
        if current_price <= 0:
            raise ValueError(f"current_price must be positive, got {current_price}")
        
        trades = []
        
        # Close all active positions
        # Create a copy of keys to avoid modifying dict during iteration
        symbols = list(self.active_positions.keys())
        
        for symbol in symbols:
            position = self.active_positions[symbol]
            trade = self.close_position(
                position=position,
                exit_price=current_price,
                reason="PANIC"
            )
            trades.append(trade)
        
        # Disable signal generation
        self._signal_generation_enabled = False
        
        return trades
    
    def is_signal_generation_enabled(self) -> bool:
        """Check if signal generation is enabled.
        
        Returns:
            True if signal generation is enabled, False if disabled (e.g., after panic close)
        """
        return self._signal_generation_enabled
    
    def get_active_position(self, symbol: str) -> Optional[Position]:
        """Get active position for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Position object if exists, None otherwise
        """
        return self.active_positions.get(symbol)
    
    def has_active_position(self, symbol: str) -> bool:
        """Check if there's an active position for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            True if position exists, False otherwise
        """
        return symbol in self.active_positions
    
    def get_all_active_positions(self) -> List[Position]:
        """Get all active positions.
        
        Returns:
            List of all active Position objects
        """
        return list(self.active_positions.values())
    
    def get_closed_trades(self) -> List[Trade]:
        """Get all closed trades.
        
        Returns:
            List of all closed Trade objects
        """
        return self.closed_trades.copy()

    def get_portfolio_metrics(self, wallet_balance: float):
        """Get portfolio-level metrics.
        
        Args:
            wallet_balance: Current wallet balance
            
        Returns:
            PortfolioMetrics object if portfolio management enabled, None otherwise
        """
        if not self.portfolio_manager or not self.feature_manager.is_feature_enabled("portfolio_management"):
            return None
        
        return self.feature_manager.execute_feature(
            "portfolio_management",
            self.portfolio_manager.get_portfolio_metrics,
            wallet_balance,
            default_value=None
        )
    
    def can_open_position_for_symbol(self, symbol: str, wallet_balance: float) -> bool:
        """Check if a position can be opened for a symbol.
        
        Checks portfolio-level risk limits if portfolio management is enabled.
        
        Args:
            symbol: Symbol to check
            wallet_balance: Current wallet balance
            
        Returns:
            True if position can be opened, False otherwise
        """
        # If portfolio management not enabled, always allow
        if not self.portfolio_manager or not self.feature_manager.is_feature_enabled("portfolio_management"):
            return True
        
        # Check if symbol is in portfolio
        if symbol not in self.portfolio_manager.symbols:
            logger.warning(f"Symbol {symbol} not in portfolio symbols")
            return False
        
        # Check if already have a position for this symbol
        if self.has_active_position(symbol):
            logger.debug(f"Already have active position for {symbol}")
            return False
        
        # Check total risk limits
        return self.feature_manager.execute_feature(
            "portfolio_management",
            self.portfolio_manager.check_total_risk,
            wallet_balance,
            default_value=True
        )
    
    def get_managed_symbols(self) -> List[str]:
        """Get list of symbols managed by portfolio manager.
        
        Returns:
            List of symbols if portfolio management enabled, otherwise [config.symbol]
        """
        if self.portfolio_manager:
            return self.portfolio_manager.symbols
        return [self.config.symbol]
