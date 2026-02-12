"""Portfolio management for multi-symbol trading."""

import time
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np

from src.config import Config
from src.models import Position, Signal, Candle

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PortfolioMetrics:
    """Portfolio-level performance metrics.
    
    Attributes:
        total_value: Total portfolio value in quote currency
        total_pnl: Total profit/loss across all symbols
        per_symbol_pnl: PnL breakdown by symbol
        correlation_matrix: Correlation coefficients between symbols
        total_risk: Total portfolio risk as percentage
        diversification_ratio: Measure of portfolio diversification
    """
    total_value: float
    total_pnl: float
    per_symbol_pnl: Dict[str, float]
    correlation_matrix: Dict[Tuple[str, str], float]
    total_risk: float
    diversification_ratio: float


class PortfolioManager:
    """Manages positions across multiple trading symbols.
    
    Handles:
    - Capital allocation across symbols based on signal confidence
    - Correlation-aware position sizing
    - Portfolio-level risk management
    - Rebalancing and diversification
    """
    
    def __init__(self, config: Config):
        """Initialize PortfolioManager.
        
        Args:
            config: Configuration object containing portfolio parameters
        """
        self.config = config
        self.symbols = config.portfolio_symbols[:config.portfolio_max_symbols]
        self.positions: Dict[str, Optional[Position]] = {symbol: None for symbol in self.symbols}
        self.correlation_matrix: Dict[Tuple[str, str], float] = {}
        self.last_rebalance = 0
        self.per_symbol_pnl: Dict[str, float] = {symbol: 0.0 for symbol in self.symbols}
        
        # Historical price data for correlation calculation
        self._price_history: Dict[str, List[float]] = {symbol: [] for symbol in self.symbols}
        
        logger.info(f"PortfolioManager initialized with {len(self.symbols)} symbols: {self.symbols}")
    
    def calculate_correlation(self, symbol1: str, symbol2: str, price_data: Dict[str, List[Candle]]) -> float:
        """Calculate rolling 30-day correlation between two symbols.
        
        Uses Pearson correlation coefficient on daily returns.
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol
            price_data: Dictionary mapping symbols to list of candles
            
        Returns:
            Correlation coefficient between -1.0 and 1.0
            Returns 0.0 if insufficient data or calculation fails
        """
        try:
            # Get price data for both symbols
            if symbol1 not in price_data or symbol2 not in price_data:
                logger.warning(f"Missing price data for correlation calculation: {symbol1}, {symbol2}")
                return 0.0
            
            candles1 = price_data[symbol1]
            candles2 = price_data[symbol2]
            
            # Need at least 30 data points for meaningful correlation
            if len(candles1) < 30 or len(candles2) < 30:
                logger.debug(f"Insufficient data for correlation: {symbol1}={len(candles1)}, {symbol2}={len(candles2)}")
                return 0.0
            
            # Extract closing prices (use last 30 days)
            prices1 = [c.close for c in candles1[-30:]]
            prices2 = [c.close for c in candles2[-30:]]
            
            # Ensure same length
            min_len = min(len(prices1), len(prices2))
            prices1 = prices1[-min_len:]
            prices2 = prices2[-min_len:]
            
            # Calculate returns
            returns1 = np.diff(prices1) / prices1[:-1]
            returns2 = np.diff(prices2) / prices2[:-1]
            
            # Calculate correlation
            if len(returns1) < 2 or len(returns2) < 2:
                return 0.0
            
            correlation = np.corrcoef(returns1, returns2)[0, 1]
            
            # Handle NaN (can occur with zero variance)
            if np.isnan(correlation):
                return 0.0
            
            return float(correlation)
            
        except Exception as e:
            logger.error(f"Error calculating correlation between {symbol1} and {symbol2}: {e}")
            return 0.0
    
    def build_correlation_matrix(self, price_data: Dict[str, List[Candle]]) -> None:
        """Build correlation matrix for all symbol pairs.
        
        Args:
            price_data: Dictionary mapping symbols to list of candles
        """
        self.correlation_matrix.clear()
        
        for i, symbol1 in enumerate(self.symbols):
            for symbol2 in self.symbols[i+1:]:
                correlation = self.calculate_correlation(symbol1, symbol2, price_data)
                self.correlation_matrix[(symbol1, symbol2)] = correlation
                self.correlation_matrix[(symbol2, symbol1)] = correlation  # Symmetric
        
        logger.debug(f"Built correlation matrix with {len(self.correlation_matrix)} entries")
    
    def calculate_allocation(
        self, 
        signals: Dict[str, Signal], 
        wallet_balance: float
    ) -> Dict[str, float]:
        """Calculate capital allocation for each symbol.
        
        Allocates based on:
        - Signal confidence (higher confidence = more allocation)
        - Correlation limits (correlated symbols get reduced combined exposure)
        - Single symbol maximum (40%)
        - Total portfolio risk limit
        
        Args:
            signals: Dictionary mapping symbols to their signals
            wallet_balance: Total available capital
            
        Returns:
            Dictionary mapping symbols to allocated capital amounts
        """
        allocations: Dict[str, float] = {symbol: 0.0 for symbol in self.symbols}
        
        # Filter signals by confidence (only allocate to signals with confidence > 0)
        valid_signals = {
            symbol: signal for symbol, signal in signals.items() 
            if symbol in self.symbols and hasattr(signal, 'indicators') and 
            signal.indicators.get('confidence', 0.0) > 0.0
        }
        
        if not valid_signals:
            logger.debug("No valid signals for allocation")
            return allocations
        
        # Start with base allocation proportional to confidence
        total_confidence = sum(
            signal.indicators.get('confidence', 0.5) 
            for signal in valid_signals.values()
        )
        
        for symbol, signal in valid_signals.items():
            confidence = signal.indicators.get('confidence', 0.5)
            
            # Base allocation proportional to confidence
            base_allocation = (confidence / total_confidence) * wallet_balance
            
            # Apply single symbol maximum (40%)
            max_single = wallet_balance * self.config.portfolio_max_single_allocation
            allocation = min(base_allocation, max_single)
            
            allocations[symbol] = allocation
        
        # Apply correlation limits
        allocations = self._apply_correlation_limits(allocations, wallet_balance)
        
        # Ensure total allocation doesn't exceed wallet balance
        total_allocated = sum(allocations.values())
        if total_allocated > wallet_balance:
            scale_factor = wallet_balance / total_allocated
            allocations = {symbol: amount * scale_factor for symbol, amount in allocations.items()}
        
        logger.info(f"Calculated allocations: {allocations}")
        return allocations
    
    def _apply_correlation_limits(
        self, 
        allocations: Dict[str, float], 
        wallet_balance: float
    ) -> Dict[str, float]:
        """Apply correlation-based exposure limits.
        
        If two symbols have correlation >0.7, their combined allocation
        must not exceed 50% of total capital.
        
        Args:
            allocations: Current allocations
            wallet_balance: Total available capital
            
        Returns:
            Adjusted allocations respecting correlation limits
        """
        max_correlated_exposure = wallet_balance * self.config.portfolio_correlation_max_exposure
        
        # Keep applying limits until all constraints are satisfied
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            adjusted = False
            
            # Check all symbol pairs
            for symbol1 in self.symbols:
                for symbol2 in self.symbols:
                    if symbol1 >= symbol2:  # Avoid duplicate checks
                        continue
                    
                    # Skip if either allocation is zero
                    if allocations[symbol1] == 0.0 or allocations[symbol2] == 0.0:
                        continue
                    
                    # Get correlation
                    correlation = self.correlation_matrix.get((symbol1, symbol2), 0.0)
                    
                    # If highly correlated, limit combined exposure
                    if abs(correlation) > self.config.portfolio_correlation_threshold:
                        combined_allocation = allocations[symbol1] + allocations[symbol2]
                        
                        if combined_allocation > max_correlated_exposure:
                            # Scale down proportionally
                            scale_factor = max_correlated_exposure / combined_allocation
                            allocations[symbol1] *= scale_factor
                            allocations[symbol2] *= scale_factor
                            adjusted = True
                            
                            logger.info(
                                f"Reduced correlated exposure for {symbol1}/{symbol2} "
                                f"(correlation={correlation:.2f}, combined={combined_allocation:.2f}, "
                                f"max={max_correlated_exposure:.2f})"
                            )
            
            # If no adjustments were made, we're done
            if not adjusted:
                break
            
            iteration += 1
        
        return allocations
    
    def get_correlated_exposure(self, symbol: str) -> float:
        """Get total exposure to symbols correlated with given symbol.
        
        Args:
            symbol: Symbol to check correlations for
            
        Returns:
            Total exposure (as fraction of portfolio) to correlated symbols
        """
        total_exposure = 0.0
        
        for other_symbol in self.symbols:
            if other_symbol == symbol:
                continue
            
            correlation = self.correlation_matrix.get((symbol, other_symbol), 0.0)
            
            if abs(correlation) > self.config.portfolio_correlation_threshold:
                # Get position value for correlated symbol
                position = self.positions.get(other_symbol)
                if position:
                    position_value = position.quantity * position.entry_price
                    total_exposure += position_value
        
        return total_exposure
    
    def rebalance_portfolio(
        self, 
        signals: Dict[str, Signal], 
        wallet_balance: float
    ) -> Dict[str, float]:
        """Rebalance portfolio allocations every 6 hours.
        
        Args:
            signals: Current signals for all symbols
            wallet_balance: Total available capital
            
        Returns:
            New allocation targets for each symbol
        """
        current_time = time.time()
        
        # Check if rebalance interval has passed
        if current_time - self.last_rebalance < self.config.portfolio_rebalance_interval:
            logger.debug("Rebalance interval not reached")
            return {}
        
        logger.info("Rebalancing portfolio...")
        
        # Calculate new allocations
        new_allocations = self.calculate_allocation(signals, wallet_balance)
        
        # Update last rebalance time
        self.last_rebalance = current_time
        
        return new_allocations
    
    def get_portfolio_metrics(self, wallet_balance: float) -> PortfolioMetrics:
        """Calculate portfolio-level performance metrics.
        
        Args:
            wallet_balance: Current wallet balance
            
        Returns:
            PortfolioMetrics object with current portfolio statistics
        """
        # Calculate total portfolio value (balance + unrealized PnL)
        total_unrealized_pnl = sum(
            pos.unrealized_pnl for pos in self.positions.values() if pos is not None
        )
        total_value = wallet_balance + total_unrealized_pnl
        
        # Calculate total PnL (realized + unrealized)
        total_pnl = sum(self.per_symbol_pnl.values()) + total_unrealized_pnl
        
        # Calculate total risk (sum of position risks)
        total_risk = 0.0
        for position in self.positions.values():
            if position is not None:
                # Risk is the potential loss from stop-loss
                position_value = position.quantity * position.entry_price
                stop_distance = abs(position.entry_price - position.stop_loss)
                position_risk = (stop_distance / position.entry_price) * position_value
                total_risk += position_risk
        
        # Express as percentage of wallet balance
        total_risk_pct = (total_risk / wallet_balance) if wallet_balance > 0 else 0.0
        
        # Calculate diversification ratio
        # Number of active positions / max possible positions
        active_positions = sum(1 for pos in self.positions.values() if pos is not None)
        diversification_ratio = active_positions / len(self.symbols) if self.symbols else 0.0
        
        return PortfolioMetrics(
            total_value=total_value,
            total_pnl=total_pnl,
            per_symbol_pnl=self.per_symbol_pnl.copy(),
            correlation_matrix=self.correlation_matrix.copy(),
            total_risk=total_risk_pct,
            diversification_ratio=diversification_ratio
        )
    
    def update_position(self, symbol: str, position: Optional[Position]) -> None:
        """Update position for a symbol.
        
        Args:
            symbol: Symbol to update
            position: New position (None if closed)
        """
        if symbol in self.positions:
            self.positions[symbol] = position
    
    def can_add_position(self, symbol: str, position: Position, wallet_balance: float) -> bool:
        """Check if a position can be added without exceeding risk limits.
        
        Args:
            symbol: Symbol for the position
            position: Position to potentially add
            wallet_balance: Current wallet balance
            
        Returns:
            True if position can be added, False if it would exceed risk limits
        """
        # Temporarily add the position
        old_position = self.positions.get(symbol)
        self.positions[symbol] = position
        
        # Check if total risk is within limits
        risk_ok = self.check_total_risk(wallet_balance)
        
        # Restore old position
        self.positions[symbol] = old_position
        
        return risk_ok
    
    def update_pnl(self, symbol: str, pnl: float) -> None:
        """Update realized PnL for a symbol.
        
        Args:
            symbol: Symbol to update
            pnl: Realized profit/loss to add
        """
        if symbol in self.per_symbol_pnl:
            self.per_symbol_pnl[symbol] += pnl
    
    def check_total_risk(self, wallet_balance: float) -> bool:
        """Check if total portfolio risk is within limits.
        
        Args:
            wallet_balance: Current wallet balance
            
        Returns:
            True if risk is within limits, False otherwise
        """
        metrics = self.get_portfolio_metrics(wallet_balance)
        
        if metrics.total_risk > self.config.portfolio_max_total_risk:
            logger.warning(
                f"Portfolio risk {metrics.total_risk:.2%} exceeds maximum "
                f"{self.config.portfolio_max_total_risk:.2%}"
            )
            return False
        
        return True
