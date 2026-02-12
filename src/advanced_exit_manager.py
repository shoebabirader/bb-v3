"""Advanced exit management for sophisticated exit strategies."""

import time
import logging
from typing import Optional, Dict, Set
from src.config import Config
from src.models import Position

logger = logging.getLogger(__name__)


class AdvancedExitManager:
    """Manages sophisticated exit strategies including partial profits and dynamic stops.
    
    Responsible for:
    - Partial profit taking at multiple levels
    - Dynamic stop-loss management (breakeven, tightening)
    - Time-based exits
    - Regime-based exits
    """
    
    def __init__(self, config: Config):
        """Initialize AdvancedExitManager with configuration.
        
        Args:
            config: Configuration object containing exit parameters
        """
        self.config = config
        
        # Define exit levels (ATR multipliers)
        self.exit_levels = {
            'partial_1': config.exit_partial_1_atr_multiplier,  # 1.5x ATR
            'partial_2': config.exit_partial_2_atr_multiplier,  # 3.0x ATR
            'final': config.exit_final_atr_multiplier           # 5.0x ATR
        }
        
        # Define exit percentages
        self.exit_percentages = {
            'partial_1': config.exit_partial_1_percentage,  # 33%
            'partial_2': config.exit_partial_2_percentage   # 33%
        }
        
        # Track which exits have been triggered for each position
        # Key: position symbol, Value: set of triggered exit levels
        self._triggered_exits: Dict[str, Set[str]] = {}
    
    def check_partial_exits(
        self, 
        position: Position, 
        current_price: float, 
        atr: float
    ) -> Optional[float]:
        """Check if partial exit should be triggered and return percentage to close.
        
        Args:
            position: Position to check
            current_price: Current market price
            atr: Current Average True Range value
            
        Returns:
            Percentage to close (0.0-1.0) if exit triggered, None otherwise
        """
        # Initialize tracking for this position if not exists
        if position.symbol not in self._triggered_exits:
            self._triggered_exits[position.symbol] = set()
        
        triggered = self._triggered_exits[position.symbol]
        
        # Calculate current profit in ATR units
        if position.side == "LONG":
            profit_distance = current_price - position.entry_price
        else:  # SHORT
            profit_distance = position.entry_price - current_price
        
        # Convert to ATR units
        profit_atr = profit_distance / atr if atr > 0 else 0
        
        # Check each exit level in order
        # Check final exit (5x ATR)
        if profit_atr >= self.exit_levels['final'] and 'final' not in triggered:
            triggered.add('final')
            # Return remaining percentage (100% - already closed)
            already_closed = sum(
                self.exit_percentages[level] 
                for level in ['partial_1', 'partial_2'] 
                if level in triggered
            )
            remaining = 1.0 - already_closed
            logger.info(
                f"Final exit triggered for {position.symbol}: "
                f"profit={profit_atr:.2f}x ATR, closing {remaining*100:.0f}%"
            )
            return remaining
        
        # Check partial_2 (3x ATR)
        if profit_atr >= self.exit_levels['partial_2'] and 'partial_2' not in triggered:
            triggered.add('partial_2')
            percentage = self.exit_percentages['partial_2']
            logger.info(
                f"Partial exit 2 triggered for {position.symbol}: "
                f"profit={profit_atr:.2f}x ATR, closing {percentage*100:.0f}%"
            )
            return percentage
        
        # Check partial_1 (1.5x ATR)
        if profit_atr >= self.exit_levels['partial_1'] and 'partial_1' not in triggered:
            triggered.add('partial_1')
            percentage = self.exit_percentages['partial_1']
            logger.info(
                f"Partial exit 1 triggered for {position.symbol}: "
                f"profit={profit_atr:.2f}x ATR, closing {percentage*100:.0f}%"
            )
            return percentage
        
        return None
    
    def update_dynamic_stops(
        self, 
        position: Position, 
        current_price: float, 
        atr: float, 
        momentum_reversed: bool
    ) -> None:
        """Update stop-loss dynamically based on profit level and momentum.
        
        Moves stop to breakeven at 2x ATR profit.
        Tightens to 0.5x ATR on momentum reversal while in profit.
        
        Args:
            position: Position to update
            current_price: Current market price
            atr: Current Average True Range value
            momentum_reversed: Whether momentum has reversed
        """
        # Calculate current profit in ATR units
        if position.side == "LONG":
            profit_distance = current_price - position.entry_price
        else:  # SHORT
            profit_distance = position.entry_price - current_price
        
        profit_atr = profit_distance / atr if atr > 0 else 0
        
        # Move stop to breakeven at 2x ATR profit
        if profit_atr >= self.config.exit_breakeven_atr_multiplier:
            if position.side == "LONG":
                # For long, breakeven is entry price
                new_stop = position.entry_price
                # Only move stop up, never down
                if new_stop > position.trailing_stop:
                    old_stop = position.trailing_stop
                    position.trailing_stop = new_stop
                    logger.info(
                        f"Breakeven stop set for {position.symbol}: "
                        f"profit={profit_atr:.2f}x ATR, stop moved from {old_stop:.2f} to {new_stop:.2f}"
                    )
            else:  # SHORT
                # For short, breakeven is entry price
                new_stop = position.entry_price
                # Only move stop down, never up
                if new_stop < position.trailing_stop:
                    old_stop = position.trailing_stop
                    position.trailing_stop = new_stop
                    logger.info(
                        f"Breakeven stop set for {position.symbol}: "
                        f"profit={profit_atr:.2f}x ATR, stop moved from {old_stop:.2f} to {new_stop:.2f}"
                    )
        
        # Tighten stop to 0.5x ATR on momentum reversal while in profit
        if momentum_reversed and profit_atr > 0:
            tight_stop_distance = atr * self.config.exit_tight_stop_atr_multiplier
            
            if position.side == "LONG":
                new_stop = current_price - tight_stop_distance
                # Only move stop up, never down
                if new_stop > position.trailing_stop:
                    old_stop = position.trailing_stop
                    position.trailing_stop = new_stop
                    logger.info(
                        f"Stop tightened for {position.symbol} due to momentum reversal: "
                        f"stop moved from {old_stop:.2f} to {new_stop:.2f} ({self.config.exit_tight_stop_atr_multiplier}x ATR)"
                    )
            else:  # SHORT
                new_stop = current_price + tight_stop_distance
                # Only move stop down, never up
                if new_stop < position.trailing_stop:
                    old_stop = position.trailing_stop
                    position.trailing_stop = new_stop
                    logger.info(
                        f"Stop tightened for {position.symbol} due to momentum reversal: "
                        f"stop moved from {old_stop:.2f} to {new_stop:.2f} ({self.config.exit_tight_stop_atr_multiplier}x ATR)"
                    )
    
    def check_time_based_exit(self, position: Position) -> bool:
        """Check if position should be closed due to time limit.
        
        Closes position if open for more than configured max hold time (default 24 hours).
        
        Args:
            position: Position to check
            
        Returns:
            True if time limit exceeded, False otherwise
        """
        current_time = int(time.time() * 1000)  # milliseconds
        time_open_ms = current_time - position.entry_time
        time_open_hours = time_open_ms / (1000 * 3600)
        
        if time_open_hours >= self.config.exit_max_hold_time_hours:
            logger.info(
                f"Time-based exit triggered for {position.symbol}: "
                f"position held for {time_open_hours:.1f} hours (max: {self.config.exit_max_hold_time_hours})"
            )
            return True
        
        return False
    
    def check_regime_exit(
        self, 
        position: Position, 
        current_regime: str, 
        previous_regime: str
    ) -> bool:
        """Check if position should be closed due to regime change.
        
        Closes positions when regime changes from TRENDING to RANGING.
        
        Args:
            position: Position to check
            current_regime: Current market regime
            previous_regime: Previous market regime
            
        Returns:
            True if regime-based exit triggered, False otherwise
        """
        if not self.config.exit_regime_change_enabled:
            return False
        
        # Check if regime changed from trending to ranging
        trending_regimes = ["TRENDING_BULLISH", "TRENDING_BEARISH"]
        
        regime_changed_to_ranging = (
            previous_regime in trending_regimes and 
            current_regime == "RANGING"
        )
        
        if regime_changed_to_ranging:
            logger.info(
                f"Regime-based exit triggered for {position.symbol}: "
                f"regime changed from {previous_regime} to {current_regime}"
            )
        
        return regime_changed_to_ranging
    
    def reset_exit_tracking(self, symbol: str) -> None:
        """Reset exit tracking for a symbol (when position is closed).
        
        Args:
            symbol: Trading pair symbol
        """
        if symbol in self._triggered_exits:
            del self._triggered_exits[symbol]
    
    def get_triggered_exits(self, symbol: str) -> Set[str]:
        """Get set of triggered exit levels for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Set of triggered exit level names
        """
        return self._triggered_exits.get(symbol, set()).copy()
