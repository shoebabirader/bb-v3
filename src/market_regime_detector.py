"""Market Regime Detector for Binance Futures Trading Bot.

Classifies market conditions into different regimes (trending, ranging, volatile)
and provides regime-specific trading parameters.
"""

from typing import List, Dict
from dataclasses import dataclass
from src.models import Candle
from src.indicators import IndicatorCalculator
from src.config import Config
import time


@dataclass
class RegimeParameters:
    """Parameters for trading in a specific market regime.
    
    Attributes:
        regime: Current regime classification
        stop_multiplier: ATR multiplier for stop-loss
        threshold_multiplier: Multiplier for indicator thresholds
        position_size_multiplier: Multiplier for position sizing
        strategy_type: Strategy to use in this regime
    """
    regime: str
    stop_multiplier: float
    threshold_multiplier: float
    position_size_multiplier: float
    strategy_type: str  # "TREND_FOLLOWING", "MEAN_REVERSION", "NONE"


class MarketRegimeDetector:
    """Detects and classifies market regimes for adaptive trading strategies.
    
    Classifies markets into:
    - TRENDING_BULLISH: Strong uptrend
    - TRENDING_BEARISH: Strong downtrend
    - RANGING: Sideways/consolidation
    - VOLATILE: High volatility, unpredictable
    - UNCERTAIN: Unclear conditions
    """
    
    def __init__(self, config: Config, indicator_calc: IndicatorCalculator):
        """Initialize the Market Regime Detector.
        
        Args:
            config: Configuration object with regime detection parameters
            indicator_calc: IndicatorCalculator instance for technical analysis
        """
        self.config = config
        self.indicator_calc = indicator_calc
        self.current_regime = "UNCERTAIN"
        self.regime_history: List[Dict] = []  # List of {timestamp, regime}
        self.last_update = 0
    
    def detect_regime(self, candles: List[Candle]) -> str:
        """Detect current market regime based on technical indicators.
        
        Uses ADX, ATR percentile, and Bollinger Band width to classify
        the market into one of five regimes.
        
        Args:
            candles: List of Candle objects (needs sufficient history)
            
        Returns:
            Regime classification string:
            - "TRENDING_BULLISH"
            - "TRENDING_BEARISH"
            - "RANGING"
            - "VOLATILE"
            - "UNCERTAIN"
        """
        if not candles or len(candles) < 30:
            return "UNCERTAIN"
        
        try:
            # Calculate required indicators
            adx = self.indicator_calc.calculate_adx(candles, self.config.adx_period)
            atr = self.indicator_calc.calculate_atr(candles, self.config.atr_period)
            vwap = self.indicator_calc.calculate_vwap(
                candles,
                candles[0].timestamp  # Use first candle as anchor
            )
            
            # Calculate ATR percentile (0-100)
            atr_percentile = self._calculate_atr_percentile(candles, atr)
            
            # Calculate Bollinger Band width
            bb_width = self._calculate_bb_width(candles)
            
            # Get current price
            current_price = candles[-1].close
            
            # Classify regime based on indicators
            regime = self._classify_regime(
                adx=adx,
                atr_percentile=atr_percentile,
                bb_width=bb_width,
                current_price=current_price,
                vwap=vwap
            )
            
            # Update regime history
            current_time = int(time.time())
            self.regime_history.append({
                'timestamp': current_time,
                'regime': regime
            })
            
            # Keep only recent history (last 24 hours)
            cutoff_time = current_time - (24 * 3600)
            self.regime_history = [
                entry for entry in self.regime_history
                if entry['timestamp'] > cutoff_time
            ]
            
            self.current_regime = regime
            self.last_update = current_time
            
            return regime
            
        except Exception as e:
            # On error, return UNCERTAIN and maintain previous regime
            return "UNCERTAIN"
    
    def _calculate_atr_percentile(self, candles: List[Candle], current_atr: float) -> float:
        """Calculate ATR percentile over lookback period.
        
        Args:
            candles: List of Candle objects
            current_atr: Current ATR value
            
        Returns:
            ATR percentile (0-100)
        """
        if not candles or current_atr == 0:
            return 50.0
        
        # Calculate ATR for each period in lookback
        atr_values = []
        window_size = self.config.atr_period + 1
        
        for i in range(window_size, len(candles) + 1):
            window = candles[i - window_size:i]
            atr = self.indicator_calc.calculate_atr(window, self.config.atr_period)
            if atr > 0:
                atr_values.append(atr)
        
        if not atr_values:
            return 50.0
        
        # Calculate percentile
        atr_values_sorted = sorted(atr_values)
        rank = sum(1 for atr in atr_values_sorted if atr <= current_atr)
        percentile = (rank / len(atr_values_sorted)) * 100.0
        
        return percentile
    
    def _calculate_bb_width(self, candles: List[Candle]) -> float:
        """Calculate Bollinger Band width as percentage of price.
        
        Args:
            candles: List of Candle objects
            
        Returns:
            BB width as percentage (0-100)
        """
        if len(candles) < 20:
            return 0.0
        
        # Get last 20 closes for BB calculation
        closes = [c.close for c in candles[-20:]]
        
        # Calculate mean and standard deviation
        mean = sum(closes) / len(closes)
        variance = sum((x - mean) ** 2 for x in closes) / len(closes)
        std_dev = variance ** 0.5
        
        # BB width = (upper - lower) / middle * 100
        # upper = mean + 2*std, lower = mean - 2*std
        # width = 4*std / mean * 100
        if mean == 0:
            return 0.0
        
        bb_width = (4 * std_dev / mean) * 100.0
        
        return bb_width
    
    def _classify_regime(
        self,
        adx: float,
        atr_percentile: float,
        bb_width: float,
        current_price: float,
        vwap: float
    ) -> str:
        """Classify market regime based on indicator values.
        
        Args:
            adx: Average Directional Index value
            atr_percentile: ATR percentile (0-100)
            bb_width: Bollinger Band width percentage
            current_price: Current market price
            vwap: Volume Weighted Average Price
            
        Returns:
            Regime classification string
        """
        # Check for VOLATILE regime first (highest priority)
        if atr_percentile > self.config.regime_volatile_atr_percentile:
            return "VOLATILE"
        
        # Check for TRENDING regimes
        if adx > self.config.regime_trending_adx_threshold:
            # Determine trend direction using price vs VWAP
            if current_price > vwap:
                return "TRENDING_BULLISH"
            else:
                return "TRENDING_BEARISH"
        
        # Check for RANGING regime
        if (adx < self.config.regime_ranging_adx_threshold and
            atr_percentile < self.config.regime_ranging_atr_percentile):
            return "RANGING"
        
        # Default to UNCERTAIN if no clear regime
        return "UNCERTAIN"
    
    def is_regime_stable(self) -> bool:
        """Check if current regime has been stable for required duration.
        
        Requires regime to be consistent for at least regime_stability_minutes
        before confirming a regime change.
        
        Returns:
            True if regime is stable, False otherwise
        """
        if not self.regime_history:
            return False
        
        # Calculate required stability duration in seconds
        required_duration = self.config.regime_stability_minutes * 60
        current_time = int(time.time())
        cutoff_time = current_time - required_duration
        
        # Get recent regime entries within stability window
        recent_regimes = [
            entry['regime'] for entry in self.regime_history
            if entry['timestamp'] > cutoff_time
        ]
        
        if not recent_regimes:
            return False
        
        # Check if all recent regimes match current regime
        return all(regime == self.current_regime for regime in recent_regimes)
    
    def get_regime_parameters(self, regime: str) -> RegimeParameters:
        """Get trading parameters for specified regime.
        
        Args:
            regime: Regime classification string
            
        Returns:
            RegimeParameters object with appropriate settings
        """
        if regime == "TRENDING_BULLISH" or regime == "TRENDING_BEARISH":
            return RegimeParameters(
                regime=regime,
                stop_multiplier=self.config.regime_trending_stop_multiplier,
                threshold_multiplier=1.0,
                position_size_multiplier=1.0,
                strategy_type="TREND_FOLLOWING"
            )
        
        elif regime == "RANGING":
            return RegimeParameters(
                regime=regime,
                stop_multiplier=self.config.regime_ranging_stop_multiplier,
                threshold_multiplier=1.0,
                position_size_multiplier=1.0,
                strategy_type="MEAN_REVERSION"
            )
        
        elif regime == "VOLATILE":
            return RegimeParameters(
                regime=regime,
                stop_multiplier=self.config.regime_trending_stop_multiplier,
                threshold_multiplier=1.0 + self.config.regime_volatile_threshold_increase,
                position_size_multiplier=self.config.regime_volatile_size_reduction,
                strategy_type="TREND_FOLLOWING"
            )
        
        else:  # UNCERTAIN
            return RegimeParameters(
                regime=regime,
                stop_multiplier=self.config.stop_loss_atr_multiplier,
                threshold_multiplier=1.0,
                position_size_multiplier=0.5,  # Reduce size in uncertain conditions
                strategy_type="NONE"
            )
