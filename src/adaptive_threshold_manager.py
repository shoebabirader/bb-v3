"""Adaptive Threshold Manager for dynamic indicator threshold adjustment.

This module provides the AdaptiveThresholdManager class which dynamically adjusts
indicator thresholds (ADX, RVOL) based on current market volatility conditions.
"""

import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from src.config import Config
from src.models import Candle
from src.indicators import IndicatorCalculator
from src.logger import get_logger


@dataclass
class ThresholdHistory:
    """Historical record of threshold adjustments.
    
    Attributes:
        timestamp: Unix timestamp when adjustment was made
        volatility_percentile: Volatility percentile that triggered adjustment
        adx_threshold: ADX threshold value after adjustment
        rvol_threshold: RVOL threshold value after adjustment
        reason: Human-readable reason for the adjustment
    """
    timestamp: int
    volatility_percentile: float
    adx_threshold: float
    rvol_threshold: float
    reason: str


class AdaptiveThresholdManager:
    """Manages dynamic adjustment of indicator thresholds based on market volatility.
    
    The manager calculates market volatility using ATR percentiles and adjusts
    ADX and RVOL thresholds accordingly. Higher volatility leads to higher thresholds
    to filter out noise, while lower volatility leads to lower thresholds to capture
    more opportunities.
    
    Attributes:
        config: Configuration object with threshold parameters
        current_thresholds: Current threshold values for ADX and RVOL
        volatility_percentile: Current volatility percentile (0-100)
        threshold_history: List of historical threshold adjustments
        last_update_time: Timestamp of last threshold update
    """
    
    def __init__(self, config: Config):
        """Initialize the Adaptive Threshold Manager.
        
        Args:
            config: Configuration object containing threshold parameters
        """
        self.config = config
        self.logger = get_logger()
        
        # Initialize current thresholds with base values from config
        self.current_thresholds: Dict[str, float] = {
            'adx': config.adx_threshold,
            'rvol': config.rvol_threshold
        }
        
        # Initialize volatility tracking
        self.volatility_percentile: float = 50.0  # Start at median
        
        # Initialize threshold history tracking
        self.threshold_history: List[ThresholdHistory] = []
        
        # Track last update time
        self.last_update_time: int = 0
        
        self.logger.log_system_event(
            f"AdaptiveThresholdManager initialized with base thresholds: "
            f"ADX={config.adx_threshold}, RVOL={config.rvol_threshold}"
        )
    
    def get_current_thresholds(self) -> Dict[str, float]:
        """Get current threshold values.
        
        Returns:
            Dictionary with current 'adx' and 'rvol' threshold values
        """
        return self.current_thresholds.copy()
    
    def should_update(self, current_time: int) -> bool:
        """Check if thresholds should be updated based on time interval.
        
        Args:
            current_time: Current Unix timestamp in seconds
            
        Returns:
            True if update interval has elapsed, False otherwise
        """
        if self.last_update_time == 0:
            return True
        
        elapsed = current_time - self.last_update_time
        return elapsed >= self.config.adaptive_threshold_update_interval
    
    def update_thresholds(self, candles: List[Candle]) -> Dict[str, float]:
        """Calculate volatility and adjust thresholds accordingly.
        
        This is the main method that should be called periodically (every hour)
        to update thresholds based on current market conditions.
        
        Args:
            candles: List of historical candles for volatility calculation
            
        Returns:
            Dictionary with updated 'adx' and 'rvol' threshold values
        """
        current_time = int(time.time())
        
        # Check if we should update
        if not self.should_update(current_time):
            return self.current_thresholds.copy()
        
        # Calculate current volatility percentile
        self.volatility_percentile = self.calculate_volatility_percentile(candles)
        
        # Calculate threshold multiplier based on volatility
        multiplier = self._calculate_threshold_multiplier(self.volatility_percentile)
        
        # Store old thresholds for logging
        old_adx = self.current_thresholds['adx']
        old_rvol = self.current_thresholds['rvol']
        
        # Apply multiplier to base thresholds
        new_adx = self.config.adx_threshold * multiplier
        new_rvol = self.config.rvol_threshold * multiplier
        
        # Enforce min/max bounds
        new_adx = max(self.config.adaptive_threshold_min_adx, 
                     min(new_adx, self.config.adaptive_threshold_max_adx))
        new_rvol = max(self.config.adaptive_threshold_min_rvol,
                      min(new_rvol, self.config.adaptive_threshold_max_rvol))
        
        # Update current thresholds
        self.current_thresholds['adx'] = new_adx
        self.current_thresholds['rvol'] = new_rvol
        
        # Create reason string
        reason = self._generate_adjustment_reason(
            self.volatility_percentile, 
            multiplier,
            old_adx,
            old_rvol,
            new_adx,
            new_rvol
        )
        
        # Log the adjustment
        self.logger.log_system_event(
            f"Threshold adjustment: {reason}",
            level="INFO"
        )
        
        # Add to history
        history_entry = ThresholdHistory(
            timestamp=current_time,
            volatility_percentile=self.volatility_percentile,
            adx_threshold=new_adx,
            rvol_threshold=new_rvol,
            reason=reason
        )
        self.threshold_history.append(history_entry)
        
        # Update last update time
        self.last_update_time = current_time
        
        return self.current_thresholds.copy()
    
    def calculate_volatility_percentile(self, candles: List[Candle]) -> float:
        """Calculate 24-hour ATR percentile from 30-day historical data.
        
        This method calculates the current 24-hour ATR and compares it to
        the distribution of 24-hour ATR values over the past 30 days to
        determine the percentile.
        
        Args:
            candles: List of candles (should contain at least 30 days of data)
            
        Returns:
            Volatility percentile (0-100), or 50.0 if insufficient data
        """
        # Need at least 30 days of hourly data for proper calculation
        # 30 days * 24 hours = 720 candles minimum
        min_candles_needed = self.config.adaptive_threshold_lookback_days * 24
        
        if len(candles) < min_candles_needed:
            self.logger.log_system_event(
                f"Insufficient data for volatility calculation: "
                f"need {min_candles_needed} candles, have {len(candles)}. "
                f"Using default percentile of 50.0",
                level="WARNING"
            )
            return 50.0
        
        # Calculate 24-hour ATR for each day in the lookback period
        atr_values = []
        
        # Use 24-candle windows (24 hours) to calculate ATR
        window_size = 24
        
        for i in range(len(candles) - window_size):
            window = candles[i:i + window_size + 1]  # +1 for ATR calculation
            atr = IndicatorCalculator.calculate_atr(window, period=14)
            if atr > 0:
                atr_values.append(atr)
        
        if len(atr_values) < 2:
            self.logger.log_system_event(
                "Insufficient valid ATR values for percentile calculation. "
                "Using default percentile of 50.0",
                level="WARNING"
            )
            return 50.0
        
        # Get current 24-hour ATR (most recent window)
        current_window = candles[-window_size - 1:]
        current_atr = IndicatorCalculator.calculate_atr(current_window, period=14)
        
        if current_atr == 0:
            return 50.0
        
        # Calculate percentile: how many historical ATR values are below current ATR
        below_count = sum(1 for atr in atr_values if atr < current_atr)
        percentile = (below_count / len(atr_values)) * 100.0
        
        return percentile
    
    def _calculate_threshold_multiplier(self, volatility_percentile: float) -> float:
        """Map volatility percentile to threshold multiplier.
        
        Percentile ranges:
        - 0-20: multiplier = 0.7 (lower thresholds for low volatility)
        - 20-40: multiplier = 0.85
        - 40-60: multiplier = 1.0 (baseline)
        - 60-80: multiplier = 1.15
        - 80-100: multiplier = 1.3 (higher thresholds for high volatility)
        
        Args:
            volatility_percentile: Volatility percentile (0-100)
            
        Returns:
            Threshold multiplier
        """
        if volatility_percentile < 20:
            return 0.7
        elif volatility_percentile < 40:
            return 0.85
        elif volatility_percentile < 60:
            return 1.0
        elif volatility_percentile < 80:
            return 1.15
        else:
            return 1.3
    
    def _generate_adjustment_reason(
        self,
        volatility_percentile: float,
        multiplier: float,
        old_adx: float,
        old_rvol: float,
        new_adx: float,
        new_rvol: float
    ) -> str:
        """Generate human-readable reason for threshold adjustment.
        
        Args:
            volatility_percentile: Current volatility percentile
            multiplier: Applied threshold multiplier
            old_adx: Previous ADX threshold
            old_rvol: Previous RVOL threshold
            new_adx: New ADX threshold
            new_rvol: New RVOL threshold
            
        Returns:
            Formatted reason string
        """
        # Determine volatility level description
        if volatility_percentile < 20:
            vol_desc = "very low"
        elif volatility_percentile < 40:
            vol_desc = "low"
        elif volatility_percentile < 60:
            vol_desc = "moderate"
        elif volatility_percentile < 80:
            vol_desc = "high"
        else:
            vol_desc = "very high"
        
        reason = (
            f"Volatility percentile: {volatility_percentile:.1f} ({vol_desc}), "
            f"Multiplier: {multiplier:.2f}, "
            f"ADX: {old_adx:.2f} -> {new_adx:.2f}, "
            f"RVOL: {old_rvol:.2f} -> {new_rvol:.2f}"
        )
        
        return reason
    
    def get_threshold_history(self, limit: Optional[int] = None) -> List[ThresholdHistory]:
        """Get historical threshold adjustments.
        
        Args:
            limit: Maximum number of history entries to return (most recent first)
            
        Returns:
            List of ThresholdHistory entries
        """
        if limit is None:
            return self.threshold_history.copy()
        else:
            return self.threshold_history[-limit:]
