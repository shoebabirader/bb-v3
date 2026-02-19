"""Backtest engine for simulating trading strategy on historical data."""

import numpy as np
import logging
import time
from typing import List, Dict, Optional
from binance.client import Client
from src.config import Config
from src.models import Candle, Trade, PerformanceMetrics, Signal, Position
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Backtesting engine that simulates trading on historical data.
    
    Implements realistic trade execution with fees and slippage,
    tracks equity curve, and calculates comprehensive performance metrics.
    Supports multi-timeframe analysis and adaptive features.
    """
    
    def __init__(
        self, 
        config: Config, 
        strategy: StrategyEngine, 
        risk_mgr: RiskManager
    ):
        """Initialize BacktestEngine with strategy and risk manager.
        
        Args:
            config: Configuration object with backtest parameters
            strategy: StrategyEngine instance for signal generation
            risk_mgr: RiskManager instance for position management
        """
        self.config = config
        self.strategy = strategy
        self.risk_mgr = risk_mgr
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.initial_balance = 0.0
        self.current_balance = 0.0
        
        # Feature tracking for adaptive components
        self.feature_metrics = {
            'adaptive_thresholds': {
                'enabled': False,
                'adjustments': 0,
                'trades_influenced': 0
            },
            'volume_profile': {
                'enabled': False,
                'trades_at_key_levels': 0,
                'total_trades': 0
            },
            'ml_predictions': {
                'enabled': False,
                'high_confidence_trades': 0,
                'low_confidence_filtered': 0,
                'total_predictions': 0
            },
            'market_regime': {
                'enabled': False,
                'regime_changes': 0,
                'trades_by_regime': {}
            }
        }
    
    def run_backtest(
        self, 
        candles_15m: List[Candle],
        candles_1h: List[Candle],
        initial_balance: float = 10000.0,
        candles_5m: Optional[List[Candle]] = None,
        candles_4h: Optional[List[Candle]] = None
    ) -> Dict:
        """Execute backtest on historical data.
        
        Iterates through historical candles, generates signals, simulates
        trade execution with realistic fills, and tracks performance.
        Supports multi-timeframe analysis when 5m and 4h data is provided.
        
        Args:
            candles_15m: List of 15-minute historical candles
            candles_1h: List of 1-hour historical candles
            initial_balance: Starting wallet balance in USDT
            candles_5m: Optional list of 5-minute historical candles for multi-TF analysis
            candles_4h: Optional list of 4-hour historical candles for multi-TF analysis
            
        Returns:
            Dictionary containing performance metrics:
                - total_trades: int
                - winning_trades: int
                - losing_trades: int
                - win_rate: float
                - total_pnl: float
                - roi: float
                - max_drawdown: float
                - profit_factor: float
                - sharpe_ratio: float
                
        Raises:
            ValueError: If inputs are invalid
        """
        if initial_balance <= 0:
            raise ValueError(f"initial_balance must be positive, got {initial_balance}")
        
        if not candles_15m or not candles_1h:
            raise ValueError("Candle lists cannot be empty")
        
        # Initialize backtest state
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.equity_curve = [initial_balance]
        self.trades = []
        
        # Store multi-timeframe data for synchronized access
        self._candles_5m = candles_5m if candles_5m else []
        self._candles_4h = candles_4h if candles_4h else []
        
        # Build synchronized timeframe indices
        # This ensures all timeframes are properly aligned by timestamp
        timeframe_indices = self._build_timeframe_indices(
            candles_15m, candles_1h, self._candles_5m, self._candles_4h
        )
        
        # Build a sliding window of candles for indicator calculation
        min_candles_15m = 50  # Enough for all indicators
        min_candles_1h = 30
        min_candles_5m = 100 if self._candles_5m else 0
        min_candles_4h = 5 if self._candles_4h else 0  # Reduced to allow earlier 4h data
        
        # Iterate through 15m candles
        for i in range(min_candles_15m, len(candles_15m)):
            # Get current window of candles
            current_candles_15m = candles_15m[max(0, i - 200):i + 1]
            
            # Get corresponding 1h candles (approximate alignment)
            # Each 1h candle = 4 x 15m candles
            current_1h_index = min(i // 4, len(candles_1h) - 1)
            current_candles_1h = candles_1h[max(0, current_1h_index - 100):current_1h_index + 1]
            
            if len(current_candles_1h) < min_candles_1h:
                continue
            
            # Get synchronized 5m and 4h candles if available
            current_candles_5m = None
            current_candles_4h = None
            
            if self._candles_5m:
                # Get 5m candles synchronized to current 15m timestamp
                current_timestamp = candles_15m[i].timestamp
                idx_5m = timeframe_indices.get('5m', {}).get(current_timestamp)
                if idx_5m is not None and idx_5m >= min_candles_5m:
                    current_candles_5m = self._candles_5m[max(0, idx_5m - 300):idx_5m + 1]
            
            if self._candles_4h:
                # Get 4h candles synchronized to current 15m timestamp
                current_timestamp = candles_15m[i].timestamp
                idx_4h = timeframe_indices.get('4h', {}).get(current_timestamp)
                
                if idx_4h is not None and idx_4h >= min_candles_4h:
                    current_candles_4h = self._candles_4h[max(0, idx_4h - 50):idx_4h + 1]
            
            # Update indicators (pass multi-timeframe data if available)
            self.strategy.update_indicators(
                current_candles_15m, 
                current_candles_1h,
                current_candles_5m,
                current_candles_4h
            )
            
            # Simulate adaptive features if enabled
            self._simulate_adaptive_features(
                current_candles_15m,
                current_candles_1h,
                current_candles_5m,
                current_candles_4h
            )
            
            # Get current candle
            current_candle = candles_15m[i]
            current_price = current_candle.close
            
            # Check if we have an active position
            active_position = self.risk_mgr.get_active_position(self.config.symbol)
            
            if active_position:
                # Update stops and check for stop hit
                atr = self.strategy.current_indicators.atr_15m
                self.risk_mgr.update_stops(active_position, current_price, atr)
                
                # Calculate current profit percentage
                if active_position.side == "LONG":
                    profit_pct = (current_price - active_position.entry_price) / active_position.entry_price
                else:  # SHORT
                    profit_pct = (active_position.entry_price - current_price) / active_position.entry_price
                
                # Check if take profit target is reached
                take_profit_pct = self.config.take_profit_pct
                
                if profit_pct >= take_profit_pct:
                    logger.info(f"[BACKTEST] TAKE PROFIT HIT! {self.config.symbol} {active_position.side} at {profit_pct*100:.2f}%")
                    exit_price = self.simulate_trade_execution(
                        signal_type="EXIT",
                        candle=current_candle,
                        is_long=(active_position.side == "LONG")
                    )
                    
                    exit_price = self.apply_fees_and_slippage(
                        exit_price, 
                        "SELL" if active_position.side == "LONG" else "BUY"
                    )
                    
                    trade = self.risk_mgr.close_position(
                        active_position,
                        exit_price,
                        "TAKE_PROFIT"
                    )
                    
                    self.current_balance += trade.pnl
                    self.trades.append(trade)
                    active_position = None
                
                # Check if stop was hit during this candle
                elif self._check_stop_hit_in_candle(active_position, current_candle):
                    exit_price = self.simulate_trade_execution(
                        signal_type="EXIT",
                        candle=current_candle,
                        is_long=(active_position.side == "LONG")
                    )
                    
                    exit_price = self.apply_fees_and_slippage(
                        exit_price, 
                        "SELL" if active_position.side == "LONG" else "BUY"
                    )
                    
                    trade = self.risk_mgr.close_position(
                        active_position,
                        exit_price,
                        "TRAILING_STOP"
                    )
                    
                    self.current_balance += trade.pnl
                    self.trades.append(trade)
                    active_position = None
            else:
                # No active position, check for entry signals
                long_signal = self.strategy.check_long_entry()
                short_signal = self.strategy.check_short_entry()
                
                signal = long_signal or short_signal
                
                if signal:
                    # Simulate entry execution
                    entry_price = self.simulate_trade_execution(
                        signal_type=signal.type,
                        candle=current_candle,
                        is_long=(signal.type == "LONG_ENTRY")
                    )
                    
                    # Apply fees and slippage
                    entry_price = self.apply_fees_and_slippage(
                        entry_price,
                        "BUY" if signal.type == "LONG_ENTRY" else "SELL"
                    )
                    
                    # Update signal price with simulated execution price
                    signal.price = entry_price
                    
                    # Track feature influence on this trade
                    self._track_feature_influence(signal, current_price)
                    
                    # Open position
                    atr = self.strategy.current_indicators.atr_15m
                    position = self.risk_mgr.open_position(
                        signal,
                        self.current_balance,
                        atr
                    )
            
            # Track equity (balance + unrealized PnL)
            equity = self.current_balance
            if active_position:
                equity += active_position.unrealized_pnl
            self.equity_curve.append(equity)
        
        # Close any remaining open positions at the end
        active_position = self.risk_mgr.get_active_position(self.config.symbol)
        if active_position:
            final_candle = candles_15m[-1]
            exit_price = self.apply_fees_and_slippage(
                final_candle.close,
                "SELL" if active_position.side == "LONG" else "BUY"
            )
            trade = self.risk_mgr.close_position(
                active_position,
                exit_price,
                "SIGNAL_EXIT"
            )
            self.current_balance += trade.pnl
            self.trades.append(trade)
        
        # Calculate and return metrics
        return self.calculate_metrics()
    
    def simulate_trade_execution(
        self, 
        signal_type: str,
        candle: Candle,
        is_long: bool
    ) -> float:
        """Simulate order fill with realistic fill logic.
        
        For entries: Uses candle open price as approximation
        For exits: Uses a price within the candle's high/low range
        
        Args:
            signal_type: Type of signal ("LONG_ENTRY", "SHORT_ENTRY", "EXIT")
            candle: Current candle for fill simulation
            is_long: Whether this is a long position
            
        Returns:
            Simulated fill price
            
        Raises:
            ValueError: If inputs are invalid
        """
        if signal_type in ["LONG_ENTRY", "SHORT_ENTRY"]:
            # For entries, assume we get filled at the open of the next candle
            # In reality, this would be more sophisticated
            return candle.open
        
        elif signal_type == "EXIT":
            # For exits (stop-loss), simulate fill within candle range
            # For long positions, stop is hit on downside
            # For short positions, stop is hit on upside
            if is_long:
                # Long stop-loss: use a price between low and close
                # Assume we get filled closer to the low
                return candle.low + (candle.close - candle.low) * 0.3
            else:
                # Short stop-loss: use a price between close and high
                # Assume we get filled closer to the high
                return candle.close + (candle.high - candle.close) * 0.7
        
        else:
            raise ValueError(f"Invalid signal_type: {signal_type}")
    
    def apply_fees_and_slippage(self, price: float, side: str) -> float:
        """Apply trading fees and slippage to execution price.
        
        Fees and slippage are applied in the unfavorable direction:
        - For buys: increase the price (pay more)
        - For sells: decrease the price (receive less)
        
        Args:
            price: Base execution price
            side: Order side ("BUY" or "SELL")
            
        Returns:
            Adjusted price with fees and slippage applied
            
        Raises:
            ValueError: If inputs are invalid
        """
        if price <= 0:
            raise ValueError(f"price must be positive, got {price}")
        
        if side not in ["BUY", "SELL"]:
            raise ValueError(f"side must be 'BUY' or 'SELL', got {side}")
        
        # Calculate total cost (fee + slippage)
        total_cost = self.config.trading_fee + self.config.slippage
        
        if side == "BUY":
            # For buys, increase price (unfavorable)
            return price * (1 + total_cost)
        else:  # SELL
            # For sells, decrease price (unfavorable)
            return price * (1 - total_cost)
    
    def calculate_metrics(self) -> Dict:
        """Calculate performance metrics from trade history.
        
        Calculates comprehensive metrics including:
        - Win rate and trade counts
        - Total PnL and ROI
        - Maximum drawdown
        - Profit factor
        - Sharpe ratio
        - Average win/loss
        
        Returns:
            Dictionary containing all performance metrics
        """
        if not self.trades:
            # No trades executed
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'roi': 0.0,
                'max_drawdown': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'average_trade_duration': 0,
                'feature_metrics': self.feature_metrics
            }
        
        # Basic trade statistics
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        losing_trades = sum(1 for t in self.trades if t.pnl <= 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        # PnL calculations
        total_pnl = sum(t.pnl for t in self.trades)
        roi = (total_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0.0
        
        # Drawdown calculation
        max_drawdown = self._calculate_max_drawdown()
        
        # Profit factor (gross profit / gross loss)
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0
        
        # Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        # Win/Loss statistics
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        
        average_win = (sum(wins) / len(wins)) if wins else 0.0
        average_loss = (sum(losses) / len(losses)) if losses else 0.0
        largest_win = max(wins) if wins else 0.0
        largest_loss = min(losses) if losses else 0.0
        
        # Trade duration
        durations = [t.exit_time - t.entry_time for t in self.trades]
        average_trade_duration = int(sum(durations) / len(durations)) if durations else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'roi': roi,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'average_win': average_win,
            'average_loss': average_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'average_trade_duration': average_trade_duration,
            'feature_metrics': self.feature_metrics
        }
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from equity curve.
        
        Returns:
            Maximum drawdown in quote currency (USDT)
        """
        if not self.equity_curve:
            return 0.0
        
        max_drawdown = 0.0
        peak = self.equity_curve[0]
        
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            
            drawdown = peak - equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from trade returns.
        
        Sharpe ratio = (Mean return - Risk-free rate) / Std deviation of returns
        Assumes risk-free rate = 0 for simplicity
        
        Returns:
            Sharpe ratio (annualized approximation)
        """
        if len(self.trades) < 2:
            return 0.0
        
        # Calculate returns as percentage of balance at trade time
        returns = []
        for trade in self.trades:
            # Approximate balance at trade time
            trade_return = trade.pnl_percent / 100  # Convert to decimal
            returns.append(trade_return)
        
        if not returns:
            return 0.0
        
        # Calculate mean and std deviation
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Sharpe ratio (not annualized, just per-trade)
        sharpe = mean_return / std_return
        
        # Approximate annualization (assuming ~250 trading days)
        # This is a rough approximation
        sharpe_annualized = sharpe * np.sqrt(250)
        
        return sharpe_annualized
    
    def _check_stop_hit_in_candle(
        self, 
        position: Position, 
        candle: Candle
    ) -> bool:
        """Check if stop-loss was hit during this candle.
        
        Args:
            position: Active position to check
            candle: Current candle
            
        Returns:
            True if stop was hit, False otherwise
        """
        if position.side == "LONG":
            # For long positions, check if low touched the stop
            return candle.low <= position.trailing_stop
        else:  # SHORT
            # For short positions, check if high touched the stop
            return candle.high >= position.trailing_stop
    
    def get_equity_curve(self) -> List[float]:
        """Get the equity curve from the backtest.
        
        Returns:
            List of equity values throughout the backtest
        """
        return self.equity_curve.copy()
    
    def get_trades(self) -> List[Trade]:
        """Get all trades from the backtest.
        
        Returns:
            List of Trade objects
        """
        return self.trades.copy()
    
    def _build_timeframe_indices(
        self,
        candles_15m: List[Candle],
        candles_1h: List[Candle],
        candles_5m: List[Candle],
        candles_4h: List[Candle]
    ) -> Dict[str, Dict[int, int]]:
        """Build indices to synchronize all timeframes.
        
        Creates a mapping from 15m timestamps to the corresponding index
        in each timeframe's candle list. This ensures all timeframes are
        properly aligned during backtesting.
        
        Args:
            candles_15m: 15-minute candles (reference timeframe)
            candles_1h: 1-hour candles
            candles_5m: 5-minute candles
            candles_4h: 4-hour candles
            
        Returns:
            Dictionary mapping timeframe to {timestamp: index} mappings
        """
        indices = {
            '5m': {},
            '1h': {},
            '4h': {}
        }
        
        # Build index for 5m candles
        # For each 15m timestamp, find the most recent 5m candle
        if candles_5m:
            for ts_15m in [c.timestamp for c in candles_15m]:
                # Find the most recent 5m candle at or before this 15m timestamp
                for idx in range(len(candles_5m) - 1, -1, -1):
                    if candles_5m[idx].timestamp <= ts_15m:
                        indices['5m'][ts_15m] = idx
                        break
        
        # Build index for 1h candles
        # For each 15m timestamp, find the most recent 1h candle
        if candles_1h:
            for ts_15m in [c.timestamp for c in candles_15m]:
                # Find the most recent 1h candle at or before this 15m timestamp
                for idx in range(len(candles_1h) - 1, -1, -1):
                    if candles_1h[idx].timestamp <= ts_15m:
                        indices['1h'][ts_15m] = idx
                        break
        
        # Build index for 4h candles
        # For each 15m timestamp, find the most recent 4h candle
        if candles_4h:
            for ts_15m in [c.timestamp for c in candles_15m]:
                # Find the most recent 4h candle at or before this 15m timestamp
                for idx in range(len(candles_4h) - 1, -1, -1):
                    if candles_4h[idx].timestamp <= ts_15m:
                        indices['4h'][ts_15m] = idx
                        break
        
        return indices
    
    def fetch_multi_timeframe_data(
        self,
        days: int = 90,
        client: Optional[Client] = None
    ) -> Dict[str, List[Candle]]:
        """Fetch historical data for all timeframes needed for backtesting.
        
        This is a convenience method that fetches 5m, 15m, 1h, and 4h data
        for the specified number of days.
        
        Args:
            days: Number of days of historical data to fetch
            client: Binance API client (required for fetching data)
            
        Returns:
            Dictionary mapping timeframe to list of Candle objects
            
        Raises:
            ValueError: If client is not provided
        """
        if client is None:
            raise ValueError("Binance client required to fetch historical data")
        
        from src.data_manager import DataManager
        
        # Create temporary data manager for fetching
        data_mgr = DataManager(self.config, client)
        
        result = {}
        
        # Fetch each timeframe
        for timeframe in ['5m', '15m', '1h', '4h']:
            try:
                candles = data_mgr.fetch_historical_data(
                    days=days,
                    timeframe=timeframe,
                    use_cache=False
                )
                result[timeframe] = candles
                logger.info(f"Fetched {len(candles)} {timeframe} candles for backtesting")
            except Exception as e:
                logger.error(f"Failed to fetch {timeframe} data: {e}")
                result[timeframe] = []
        
        return result
    
    def _simulate_adaptive_features(
        self,
        current_candles_15m: List[Candle],
        current_candles_1h: List[Candle],
        current_candles_5m: Optional[List[Candle]],
        current_candles_4h: Optional[List[Candle]]
    ) -> None:
        """Simulate adaptive feature adjustments during backtest.
        
        This method checks if the strategy has adaptive components and
        simulates their behavior during backtesting.
        
        Args:
            current_candles_15m: Current 15m candle window
            current_candles_1h: Current 1h candle window
            current_candles_5m: Current 5m candle window (optional)
            current_candles_4h: Current 4h candle window (optional)
        """
        # Check for adaptive threshold manager
        if hasattr(self.strategy, 'adaptive_threshold_mgr') and self.strategy.adaptive_threshold_mgr:
            self.feature_metrics['adaptive_thresholds']['enabled'] = True
            
            # Simulate threshold updates (normally done every hour)
            # In backtest, we update based on available data
            try:
                old_thresholds = self.strategy.adaptive_threshold_mgr.get_current_thresholds()
                new_thresholds = self.strategy.adaptive_threshold_mgr.update_thresholds(current_candles_1h)
                
                # Track if thresholds changed
                if old_thresholds != new_thresholds:
                    self.feature_metrics['adaptive_thresholds']['adjustments'] += 1
            except Exception as e:
                logger.debug(f"Error simulating adaptive thresholds: {e}")
        
        # Check for volume profile analyzer
        if hasattr(self.strategy, 'volume_profile_analyzer') and self.strategy.volume_profile_analyzer:
            self.feature_metrics['volume_profile']['enabled'] = True
            
            # Simulate volume profile calculation (normally done every 4 hours)
            try:
                # Use 1h candles for volume profile (need ~7 days = 168 candles)
                if len(current_candles_1h) >= 168:
                    self.strategy.volume_profile_analyzer.calculate_volume_profile(
                        current_candles_1h[-168:]
                    )
            except Exception as e:
                logger.debug(f"Error simulating volume profile: {e}")
        
        # Check for ML predictor
        if hasattr(self.strategy, 'ml_predictor') and self.strategy.ml_predictor:
            self.feature_metrics['ml_predictions']['enabled'] = True
            
            # Simulate ML prediction
            try:
                if hasattr(self.strategy.ml_predictor, 'predict'):
                    # Use 1h candles for prediction
                    prediction = self.strategy.ml_predictor.predict(current_candles_1h)
                    self.feature_metrics['ml_predictions']['total_predictions'] += 1
                    
                    # Track high/low confidence predictions
                    if prediction > 0.7:
                        self.feature_metrics['ml_predictions']['high_confidence_trades'] += 1
                    elif prediction < 0.3:
                        self.feature_metrics['ml_predictions']['low_confidence_filtered'] += 1
            except Exception as e:
                logger.debug(f"Error simulating ML prediction: {e}")
        
        # Check for market regime detector
        if hasattr(self.strategy, 'market_regime_detector') and self.strategy.market_regime_detector:
            self.feature_metrics['market_regime']['enabled'] = True
            
            # Simulate regime detection
            try:
                old_regime = getattr(self.strategy.market_regime_detector, 'current_regime', None)
                new_regime = self.strategy.market_regime_detector.detect_regime(current_candles_1h)
                
                # Track regime changes
                if old_regime and old_regime != new_regime:
                    self.feature_metrics['market_regime']['regime_changes'] += 1
                
                # Initialize regime counter if needed
                if new_regime not in self.feature_metrics['market_regime']['trades_by_regime']:
                    self.feature_metrics['market_regime']['trades_by_regime'][new_regime] = 0
            except Exception as e:
                logger.debug(f"Error simulating market regime detection: {e}")
    
    def _track_feature_influence(
        self,
        signal: Signal,
        current_price: float
    ) -> None:
        """Track which features influenced the current trade.
        
        Args:
            signal: Trading signal that was generated
            current_price: Current market price
        """
        # Track volume profile influence
        if self.feature_metrics['volume_profile']['enabled']:
            try:
                if hasattr(self.strategy, 'volume_profile_analyzer') and self.strategy.volume_profile_analyzer:
                    if self.strategy.volume_profile_analyzer.is_near_key_level(current_price):
                        self.feature_metrics['volume_profile']['trades_at_key_levels'] += 1
                    self.feature_metrics['volume_profile']['total_trades'] += 1
            except Exception as e:
                logger.debug(f"Error tracking volume profile influence: {e}")
        
        # Track adaptive threshold influence
        if self.feature_metrics['adaptive_thresholds']['enabled']:
            self.feature_metrics['adaptive_thresholds']['trades_influenced'] += 1
        
        # Track market regime influence
        if self.feature_metrics['market_regime']['enabled']:
            try:
                if hasattr(self.strategy, 'market_regime_detector') and self.strategy.market_regime_detector:
                    regime = getattr(self.strategy.market_regime_detector, 'current_regime', 'UNKNOWN')
                    if regime in self.feature_metrics['market_regime']['trades_by_regime']:
                        self.feature_metrics['market_regime']['trades_by_regime'][regime] += 1
            except Exception as e:
                logger.debug(f"Error tracking market regime influence: {e}")
    
    def get_feature_metrics(self) -> Dict:
        """Get metrics about adaptive feature usage during backtest.
        
        Returns:
            Dictionary containing feature-specific metrics
        """
        return self.feature_metrics.copy()
    
    def run_ab_comparison(
        self,
        candles_15m: List[Candle],
        candles_1h: List[Candle],
        initial_balance: float = 10000.0,
        candles_5m: Optional[List[Candle]] = None,
        candles_4h: Optional[List[Candle]] = None
    ) -> Dict:
        """Run A/B comparison backtest with all features vs. baseline.
        
        Runs multiple backtests:
        1. Baseline (no advanced features)
        2. All features enabled
        3. Each feature individually disabled
        
        Args:
            candles_15m: List of 15-minute historical candles
            candles_1h: List of 1-hour historical candles
            initial_balance: Starting wallet balance in USDT
            candles_5m: Optional list of 5-minute historical candles
            candles_4h: Optional list of 4-hour historical candles
            
        Returns:
            Dictionary containing comparison results for each configuration
        """
        logger.info("Starting A/B comparison backtest...")
        
        results = {}
        
        # Store original feature states
        original_states = self._save_feature_states()
        
        # 1. Run baseline (all features disabled)
        logger.info("Running baseline backtest (all features disabled)...")
        self._disable_all_features()
        results['baseline'] = self.run_backtest(
            candles_15m, candles_1h, initial_balance, candles_5m, candles_4h
        )
        
        # 2. Run with all features enabled
        logger.info("Running backtest with all features enabled...")
        self._restore_feature_states(original_states)
        results['all_features'] = self.run_backtest(
            candles_15m, candles_1h, initial_balance, candles_5m, candles_4h
        )
        
        # 3. Run with each feature individually disabled
        feature_names = [
            'adaptive_threshold_mgr',
            'volume_profile_analyzer',
            'ml_predictor',
            'market_regime_detector',
            'timeframe_coordinator'
        ]
        
        for feature_name in feature_names:
            if hasattr(self.strategy, feature_name):
                logger.info(f"Running backtest without {feature_name}...")
                
                # Restore all features
                self._restore_feature_states(original_states)
                
                # Disable specific feature
                self._disable_feature(feature_name)
                
                # Run backtest
                results[f'without_{feature_name}'] = self.run_backtest(
                    candles_15m, candles_1h, initial_balance, candles_5m, candles_4h
                )
        
        # Restore original states
        self._restore_feature_states(original_states)
        
        # Generate comparison report
        comparison_report = self._generate_comparison_report(results)
        results['comparison_report'] = comparison_report
        
        logger.info("A/B comparison backtest completed")
        
        return results
    
    def _save_feature_states(self) -> Dict:
        """Save current state of all adaptive features.
        
        Returns:
            Dictionary mapping feature names to their current state
        """
        states = {}
        
        feature_names = [
            'adaptive_threshold_mgr',
            'volume_profile_analyzer',
            'ml_predictor',
            'market_regime_detector',
            'timeframe_coordinator'
        ]
        
        for feature_name in feature_names:
            if hasattr(self.strategy, feature_name):
                states[feature_name] = getattr(self.strategy, feature_name)
        
        return states
    
    def _restore_feature_states(self, states: Dict) -> None:
        """Restore saved feature states.
        
        Args:
            states: Dictionary mapping feature names to their saved state
        """
        for feature_name, state in states.items():
            if hasattr(self.strategy, feature_name):
                setattr(self.strategy, feature_name, state)
    
    def _disable_all_features(self) -> None:
        """Temporarily disable all adaptive features."""
        feature_names = [
            'adaptive_threshold_mgr',
            'volume_profile_analyzer',
            'ml_predictor',
            'market_regime_detector',
            'timeframe_coordinator'
        ]
        
        for feature_name in feature_names:
            self._disable_feature(feature_name)
    
    def _disable_feature(self, feature_name: str) -> None:
        """Temporarily disable a specific feature.
        
        Args:
            feature_name: Name of the feature to disable
        """
        if hasattr(self.strategy, feature_name):
            setattr(self.strategy, feature_name, None)
    
    def _generate_comparison_report(self, results: Dict) -> Dict:
        """Generate a comparison report from A/B test results.
        
        Args:
            results: Dictionary containing results from all backtest runs
            
        Returns:
            Dictionary containing comparison metrics and analysis
        """
        report = {
            'summary': {},
            'feature_contributions': {},
            'recommendations': []
        }
        
        # Get baseline metrics
        baseline = results.get('baseline', {})
        all_features = results.get('all_features', {})
        
        if not baseline or not all_features:
            return report
        
        # Calculate overall improvement
        report['summary'] = {
            'baseline_roi': baseline.get('roi', 0),
            'all_features_roi': all_features.get('roi', 0),
            'roi_improvement': all_features.get('roi', 0) - baseline.get('roi', 0),
            'baseline_win_rate': baseline.get('win_rate', 0),
            'all_features_win_rate': all_features.get('win_rate', 0),
            'win_rate_improvement': all_features.get('win_rate', 0) - baseline.get('win_rate', 0),
            'baseline_profit_factor': baseline.get('profit_factor', 0),
            'all_features_profit_factor': all_features.get('profit_factor', 0),
            'profit_factor_improvement': all_features.get('profit_factor', 0) - baseline.get('profit_factor', 0)
        }
        
        # Calculate individual feature contributions
        feature_names = [
            'adaptive_threshold_mgr',
            'volume_profile_analyzer',
            'ml_predictor',
            'market_regime_detector',
            'timeframe_coordinator'
        ]
        
        for feature_name in feature_names:
            without_key = f'without_{feature_name}'
            if without_key in results:
                without_feature = results[without_key]
                
                # Calculate contribution (difference when feature is removed)
                contribution = {
                    'roi_contribution': all_features.get('roi', 0) - without_feature.get('roi', 0),
                    'win_rate_contribution': all_features.get('win_rate', 0) - without_feature.get('win_rate', 0),
                    'profit_factor_contribution': all_features.get('profit_factor', 0) - without_feature.get('profit_factor', 0),
                    'trade_count_impact': all_features.get('total_trades', 0) - without_feature.get('total_trades', 0)
                }
                
                report['feature_contributions'][feature_name] = contribution
                
                # Generate recommendations
                if contribution['roi_contribution'] > 1.0:
                    report['recommendations'].append(
                        f"{feature_name} provides significant ROI improvement (+{contribution['roi_contribution']:.2f}%)"
                    )
                elif contribution['roi_contribution'] < -1.0:
                    report['recommendations'].append(
                        f"{feature_name} may be degrading performance ({contribution['roi_contribution']:.2f}%)"
                    )
        
        return report
