"""Strategy engine for signal generation in Binance Futures Trading Bot."""

from typing import List, Optional, Dict
from src.models import Candle, Signal, IndicatorState
from src.indicators import IndicatorCalculator
from src.config import Config
from src.adaptive_threshold_manager import AdaptiveThresholdManager
from src.timeframe_coordinator import TimeframeCoordinator
from src.volume_profile_analyzer import VolumeProfileAnalyzer
from src.market_regime_detector import MarketRegimeDetector
from src.ml_predictor import MLPredictor
from src.feature_manager import FeatureManager
import time
import logging

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Strategy engine that generates trading signals based on technical indicators.
    
    The engine calculates indicators on multiple timeframes (15m and 1h),
    determines trend direction, and generates LONG_ENTRY or SHORT_ENTRY signals
    when all conditions are met.
    """
    
    def __init__(self, config: Config):
        """Initialize the strategy engine.
        
        Args:
            config: Configuration object with indicator parameters
        """
        self.config = config
        self.indicator_calc = IndicatorCalculator()
        self.current_indicators = IndicatorState()
        self._previous_squeeze_color = "gray"
        
        # Initialize feature manager for error isolation
        self.feature_manager = FeatureManager(max_errors=3, error_window=300.0)
        
        # Initialize adaptive threshold manager if enabled
        self.adaptive_threshold_manager = None
        self._last_threshold_update = 0
        if config.enable_adaptive_thresholds:
            try:
                self.adaptive_threshold_manager = AdaptiveThresholdManager(config)
                self.feature_manager.register_feature("adaptive_thresholds", enabled=True)
                logger.info("Adaptive threshold manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize adaptive threshold manager: {e}")
                self.feature_manager.register_feature("adaptive_thresholds", enabled=False)
        
        # Initialize timeframe coordinator if enabled
        self.timeframe_coordinator = None
        if config.enable_multi_timeframe:
            try:
                self.timeframe_coordinator = TimeframeCoordinator(config, self.indicator_calc)
                # Register as critical feature - don't auto-disable on errors
                self.feature_manager.register_feature("multi_timeframe", enabled=True, auto_disable=False)
                logger.info("Timeframe coordinator initialized (critical feature - auto-disable OFF)")
            except Exception as e:
                logger.error(f"Failed to initialize timeframe coordinator: {e}")
                self.feature_manager.register_feature("multi_timeframe", enabled=False, auto_disable=False)
        
        # Initialize volume profile analyzer if enabled
        self.volume_profile_analyzer = None
        if config.enable_volume_profile:
            try:
                self.volume_profile_analyzer = VolumeProfileAnalyzer(config)
                self.feature_manager.register_feature("volume_profile", enabled=True)
                logger.info("Volume profile analyzer initialized")
            except Exception as e:
                logger.error(f"Failed to initialize volume profile analyzer: {e}")
                self.feature_manager.register_feature("volume_profile", enabled=False)
        
        # Initialize market regime detector if enabled
        self.market_regime_detector = None
        self.current_regime_params = None
        if config.enable_regime_detection:
            try:
                self.market_regime_detector = MarketRegimeDetector(config, self.indicator_calc)
                self.feature_manager.register_feature("regime_detection", enabled=True)
                logger.info("Market regime detector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize market regime detector: {e}")
                self.feature_manager.register_feature("regime_detection", enabled=False)
        
        # Initialize ML predictor if enabled
        self.ml_predictor = None
        self.ml_prediction = 0.5  # Neutral by default
        if config.enable_ml_prediction:
            try:
                self.ml_predictor = MLPredictor(config)
                self.feature_manager.register_feature("ml_prediction", enabled=True)
                logger.info("ML predictor initialized")
            except Exception as e:
                logger.error(f"Failed to initialize ML predictor: {e}")
                self.feature_manager.register_feature("ml_prediction", enabled=False)
        
    def update_indicators(
        self, 
        candles_15m: List[Candle], 
        candles_1h: List[Candle],
        candles_5m: Optional[List[Candle]] = None,
        candles_4h: Optional[List[Candle]] = None
    ) -> None:
        """Recalculate all indicators with latest candle data.
        
        Updates the current_indicators state with fresh calculations.
        Skips update if insufficient data is available.
        Implements graceful degradation for missing timeframe data.
        
        Args:
            candles_15m: List of 15-minute candles
            candles_1h: List of 1-hour candles
            candles_5m: Optional list of 5-minute candles (for multi-timeframe)
            candles_4h: Optional list of 4-hour candles (for multi-timeframe)
        """
        # Check if we have sufficient data
        if not self._has_sufficient_data(candles_15m, candles_1h):
            logger.warning("Insufficient data for indicator calculation")
            return
        
        # Update adaptive thresholds if enabled (every hour)
        if self.adaptive_threshold_manager and self.feature_manager.is_feature_enabled("adaptive_thresholds"):
            current_time = int(time.time())
            if current_time - self._last_threshold_update >= self.config.adaptive_threshold_update_interval:
                self.feature_manager.execute_feature(
                    "adaptive_thresholds",
                    self.adaptive_threshold_manager.update_thresholds,
                    candles_15m
                )
                self._last_threshold_update = current_time
        
        # Analyze all timeframes if multi-timeframe is enabled
        self.timeframe_analysis = None
        if self.timeframe_coordinator and self.feature_manager.is_feature_enabled("multi_timeframe"):
            # Check if we have all required timeframes
            if candles_5m and candles_4h and len(candles_5m) > 0 and len(candles_4h) > 0:
                # Only execute feature if data is available - this prevents errors from being counted
                # when data is simply not loaded yet (e.g., during startup)
                self.timeframe_analysis = self.feature_manager.execute_feature(
                    "multi_timeframe",
                    self.timeframe_coordinator.analyze_all_timeframes,
                    candles_5m, candles_15m, candles_1h, candles_4h,
                    default_value=None
                )
            else:
                # Data not available - log once but don't count as error
                if candles_5m is None or len(candles_5m) == 0:
                    logger.debug("Multi-timeframe: 5m data not available yet")
                if candles_4h is None or len(candles_4h) == 0:
                    logger.debug("Multi-timeframe: 4h data not available yet")
        
        # Update volume profile if enabled (every 4 hours by default)
        if self.volume_profile_analyzer and self.feature_manager.is_feature_enabled("volume_profile"):
            current_time_sec = int(time.time())
            if current_time_sec - self.volume_profile_analyzer.last_update >= self.config.volume_profile_update_interval:
                # Use 15m candles for volume profile (covers 7 days with enough granularity)
                profile = self.feature_manager.execute_feature(
                    "volume_profile",
                    self.volume_profile_analyzer.calculate_volume_profile,
                    candles_15m,
                    default_value=None
                )
                if profile is not None:
                    self.volume_profile_analyzer.current_profile = profile
                    self.volume_profile_analyzer.last_update = current_time_sec
                else:
                    logger.warning("Volume profile calculation failed, using previous profile")
        
        # Update market regime if enabled (every 15 minutes by default)
        if self.market_regime_detector and self.feature_manager.is_feature_enabled("regime_detection"):
            current_time_sec = int(time.time())
            if current_time_sec - self.market_regime_detector.last_update >= self.config.regime_update_interval:
                regime = self.feature_manager.execute_feature(
                    "regime_detection",
                    self.market_regime_detector.detect_regime,
                    candles_15m,
                    default_value="UNCERTAIN"
                )
                
                # Update regime history
                self.market_regime_detector.regime_history.append({
                    'timestamp': current_time_sec,
                    'regime': regime
                })
                
                # Only update current regime if stable
                if self.market_regime_detector.is_regime_stable():
                    self.market_regime_detector.current_regime = regime
                
                # Get regime-specific parameters
                self.current_regime_params = self.market_regime_detector.get_regime_parameters(
                    self.market_regime_detector.current_regime
                )
                
                self.market_regime_detector.last_update = current_time_sec
        
        # Get ML prediction if enabled
        if self.ml_predictor and self.ml_predictor.enabled and self.feature_manager.is_feature_enabled("ml_prediction"):
            self.ml_prediction = self.feature_manager.execute_feature(
                "ml_prediction",
                self.ml_predictor.predict,
                candles_15m,
                default_value=0.5  # Neutral
            )
            
            # Check if ML predictor should be disabled due to low accuracy
            if self.ml_predictor.should_disable():
                logger.warning("ML predictor disabled due to low accuracy")
                self.feature_manager.disable_feature("ml_prediction")
                self.ml_prediction = 0.5
        else:
            self.ml_prediction = 0.5  # Neutral
        
        # Get current price
        self.current_indicators.current_price = candles_15m[-1].close
        
        # Calculate weekly anchor time (most recent Monday 00:00 UTC)
        current_time = candles_15m[-1].timestamp
        # Simplified: use a fixed anchor for now (can be improved)
        # For production, calculate actual weekly open
        self.current_indicators.weekly_anchor_time = self._get_weekly_anchor(current_time)
        
        # Calculate VWAP for both timeframes
        self.current_indicators.vwap_15m = self.indicator_calc.calculate_vwap(
            candles_15m, 
            self.current_indicators.weekly_anchor_time
        )
        self.current_indicators.vwap_1h = self.indicator_calc.calculate_vwap(
            candles_1h, 
            self.current_indicators.weekly_anchor_time
        )
        
        # Calculate ATR for both timeframes
        self.current_indicators.atr_15m = self.indicator_calc.calculate_atr(
            candles_15m, 
            self.config.atr_period
        )
        self.current_indicators.atr_1h = self.indicator_calc.calculate_atr(
            candles_1h, 
            self.config.atr_period
        )
        
        # Calculate ADX on 15m timeframe
        self.current_indicators.adx = self.indicator_calc.calculate_adx(
            candles_15m, 
            self.config.adx_period
        )
        
        # Calculate RVOL on 15m timeframe
        self.current_indicators.rvol = self.indicator_calc.calculate_rvol(
            candles_15m, 
            self.config.rvol_period
        )
        
        # Calculate Squeeze Momentum on 15m timeframe
        squeeze_result = self.indicator_calc.calculate_squeeze_momentum(candles_15m)
        self.current_indicators.squeeze_value = squeeze_result['value']
        self.current_indicators.is_squeezed = squeeze_result['is_squeezed']
        self.current_indicators.previous_squeeze_color = self._previous_squeeze_color
        self.current_indicators.squeeze_color = squeeze_result['color']
        
        # Update previous squeeze color for next iteration
        self._previous_squeeze_color = squeeze_result['color']
        
        # Determine trends
        self.current_indicators.trend_15m = self.indicator_calc.determine_trend(
            candles_15m, 
            self.current_indicators.vwap_15m
        )
        self.current_indicators.trend_1h = self.indicator_calc.determine_trend(
            candles_1h, 
            self.current_indicators.vwap_1h
        )
        
        # Determine price vs VWAP
        if self.current_indicators.current_price > self.current_indicators.vwap_15m:
            self.current_indicators.price_vs_vwap = "ABOVE"
        else:
            self.current_indicators.price_vs_vwap = "BELOW"
    
    def check_long_entry(self, symbol: Optional[str] = None) -> Optional[Signal]:
        """Check if long entry conditions are met.
        
        Long entry conditions:
        1. 15m price > VWAP
        2. 15m trend is BULLISH (added for confirmation)
        
        Args:
            symbol: Trading pair symbol (optional, defaults to config.symbol)
        3. 1h trend is BULLISH
        4. Squeeze momentum > 0 (positive momentum confirms bullish)
        5. ADX > threshold (strong trend)
        6. RVOL > threshold (high volume)
        7. Multi-timeframe confirmation (if enabled)
        8. Regime-appropriate conditions (if enabled)
        9. ML prediction confirmation (if enabled)
        
        Returns:
            Signal object if all conditions met, None otherwise
        """
        # Check ML prediction first if enabled
        if self.ml_predictor and self.ml_predictor.enabled:
            # If ML shows low confidence for bullish (<0.3), skip entry
            if self.ml_prediction < self.config.ml_low_confidence_threshold:
                return None
        
        # Check regime conditions first if enabled
        if self.market_regime_detector and self.current_regime_params:
            # Don't trade in UNCERTAIN regime
            if self.current_regime_params.strategy_type == "NONE":
                return None
            
            # For ranging regime, we might want mean reversion instead of trend following
            # For now, we'll still allow trend following but with tighter parameters
        
        # Check multi-timeframe alignment first if enabled
        if self.timeframe_coordinator and self.timeframe_analysis:
            # Require minimum alignment (default 3 out of 4 timeframes)
            if self.timeframe_analysis.alignment_score < self.config.min_timeframe_alignment:
                return None
            
            # Check if overall direction is bullish
            if self.timeframe_analysis.overall_direction != "BULLISH":
                return None
        
        # Get current thresholds (adaptive or static)
        adx_threshold = self.config.adx_threshold
        rvol_threshold = self.config.rvol_threshold
        
        if self.adaptive_threshold_manager:
            thresholds = self.adaptive_threshold_manager.get_current_thresholds()
            adx_threshold = thresholds['adx']
            rvol_threshold = thresholds['rvol']
        
        # Apply regime-specific threshold multiplier if enabled
        if self.current_regime_params:
            adx_threshold *= self.current_regime_params.threshold_multiplier
            rvol_threshold *= self.current_regime_params.threshold_multiplier
        
        # Check all conditions - now requires BOTH 15m and 1h trends to be bullish
        # AND squeeze momentum to be positive with green color (increasing momentum)
        conditions_met = (
            self.current_indicators.price_vs_vwap == "ABOVE" and
            self.current_indicators.trend_15m == "BULLISH" and  # Added 15m trend check
            self.current_indicators.trend_1h == "BULLISH" and
            self.current_indicators.squeeze_value > 0 and  # Added momentum check
            self.current_indicators.squeeze_color == "green" and  # Require green (increasing positive momentum)
            self.current_indicators.adx > adx_threshold and
            self.current_indicators.rvol > rvol_threshold
        )
        
        if not conditions_met:
            return None
        
        # Create signal with indicator snapshot
        signal = Signal(
            type="LONG_ENTRY",
            timestamp=int(time.time() * 1000),
            price=self.current_indicators.current_price,
            indicators=self.get_indicator_snapshot(),
            symbol=symbol if symbol is not None else self.config.symbol
        )
        
        # Add confidence from timeframe analysis if available
        if self.timeframe_analysis:
            signal.confidence = self.timeframe_analysis.confidence
        
        # Adjust confidence based on ML prediction if enabled
        if self.ml_predictor and self.ml_predictor.enabled:
            # If ML shows high confidence (>0.7), boost signal confidence
            if self.ml_prediction > self.config.ml_high_confidence_threshold:
                signal.confidence = min(1.0, signal.confidence * 1.2)
        
        return signal
    
    def check_short_entry(self, symbol: Optional[str] = None) -> Optional[Signal]:
        """Check if short entry conditions are met.
        
        Short entry conditions:
        1. 15m price < VWAP
        2. 15m trend is BEARISH (added for confirmation)
        
        Args:
            symbol: Trading pair symbol (optional, defaults to config.symbol)
        3. 1h trend is BEARISH
        4. Squeeze momentum < 0 (negative momentum confirms bearish)
        5. ADX > threshold (strong trend)
        6. RVOL > threshold (high volume)
        7. Multi-timeframe confirmation (if enabled)
        8. Regime-appropriate conditions (if enabled)
        9. ML prediction confirmation (if enabled)
        
        Returns:
            Signal object if all conditions met, None otherwise
        """
        # Check ML prediction first if enabled
        if self.ml_predictor and self.ml_predictor.enabled:
            # If ML shows high confidence for bullish (>0.7), skip short entry
            if self.ml_prediction > (1.0 - self.config.ml_low_confidence_threshold):
                return None
        
        # Check regime conditions first if enabled
        if self.market_regime_detector and self.current_regime_params:
            # Don't trade in UNCERTAIN regime
            if self.current_regime_params.strategy_type == "NONE":
                return None
            
            # For ranging regime, we might want mean reversion instead of trend following
            # For now, we'll still allow trend following but with tighter parameters
        
        # Check multi-timeframe alignment first if enabled
        if self.timeframe_coordinator and self.timeframe_analysis:
            # Require minimum alignment (default 3 out of 4 timeframes)
            if self.timeframe_analysis.alignment_score < self.config.min_timeframe_alignment:
                return None
            
            # Check if overall direction is bearish
            if self.timeframe_analysis.overall_direction != "BEARISH":
                return None
        
        # Get current thresholds (adaptive or static)
        adx_threshold = self.config.adx_threshold
        rvol_threshold = self.config.rvol_threshold
        
        if self.adaptive_threshold_manager:
            thresholds = self.adaptive_threshold_manager.get_current_thresholds()
            adx_threshold = thresholds['adx']
            rvol_threshold = thresholds['rvol']
        
        # Apply regime-specific threshold multiplier if enabled
        if self.current_regime_params:
            adx_threshold *= self.current_regime_params.threshold_multiplier
            rvol_threshold *= self.current_regime_params.threshold_multiplier
        
        # Check all conditions - now requires BOTH 15m and 1h trends to be bearish
        # AND squeeze momentum to be negative with maroon color (decreasing momentum)
        conditions_met = (
            self.current_indicators.price_vs_vwap == "BELOW" and
            self.current_indicators.trend_15m == "BEARISH" and  # Added 15m trend check
            self.current_indicators.trend_1h == "BEARISH" and
            self.current_indicators.squeeze_value < 0 and  # Added momentum check
            self.current_indicators.squeeze_color == "maroon" and  # Require maroon (decreasing negative momentum)
            self.current_indicators.adx > adx_threshold and
            self.current_indicators.rvol > rvol_threshold
        )
        
        if not conditions_met:
            return None
        
        # Create signal with indicator snapshot
        signal = Signal(
            type="SHORT_ENTRY",
            timestamp=int(time.time() * 1000),
            price=self.current_indicators.current_price,
            indicators=self.get_indicator_snapshot(),
            symbol=symbol if symbol is not None else self.config.symbol
        )
        
        # Add confidence from timeframe analysis if available
        if self.timeframe_analysis:
            signal.confidence = self.timeframe_analysis.confidence
        
        # Adjust confidence based on ML prediction if enabled
        if self.ml_predictor and self.ml_predictor.enabled:
            # If ML shows high confidence for bearish (<0.3), boost signal confidence
            if self.ml_prediction < (1.0 - self.config.ml_high_confidence_threshold):
                signal.confidence = min(1.0, signal.confidence * 1.2)
        
        return signal
    
    def get_indicator_snapshot(self) -> Dict[str, float]:
        """Return current indicator values for logging and display.
        
        Returns:
            Dictionary containing all current indicator values
        """
        return {
            'vwap_15m': self.current_indicators.vwap_15m,
            'vwap_1h': self.current_indicators.vwap_1h,
            'atr_15m': self.current_indicators.atr_15m,
            'atr_1h': self.current_indicators.atr_1h,
            'adx': self.current_indicators.adx,
            'rvol': self.current_indicators.rvol,
            'squeeze_value': self.current_indicators.squeeze_value,
            'squeeze_color': self.current_indicators.squeeze_color,
            'is_squeezed': float(self.current_indicators.is_squeezed),
            'trend_15m': self.current_indicators.trend_15m,
            'trend_1h': self.current_indicators.trend_1h,
            'current_price': self.current_indicators.current_price,
            'price_vs_vwap': self.current_indicators.price_vs_vwap
        }
    
    def get_advanced_features_data(self) -> dict:
        """Return advanced features data for UI display.
        
        Returns:
            Dictionary containing:
                - market_regime: Current market regime (if enabled)
                - ml_prediction: ML prediction probability (if enabled)
                - volume_profile: Dict with POC, VAH, VAL (if enabled)
                - adaptive_thresholds: Dict with ADX and RVOL thresholds (if enabled)
        """
        data = {}
        
        # Market regime
        if self.market_regime_detector and self.feature_manager.is_feature_enabled("regime_detection"):
            data['market_regime'] = self.market_regime_detector.current_regime
        
        # ML prediction
        if self.ml_predictor and self.ml_predictor.enabled and self.feature_manager.is_feature_enabled("ml_prediction"):
            data['ml_prediction'] = self.ml_prediction
        
        # Volume profile
        if self.volume_profile_analyzer and self.feature_manager.is_feature_enabled("volume_profile"):
            if self.volume_profile_analyzer.current_profile:
                data['volume_profile'] = {
                    'poc': self.volume_profile_analyzer.current_profile.poc,
                    'vah': self.volume_profile_analyzer.current_profile.vah,
                    'val': self.volume_profile_analyzer.current_profile.val
                }
        
        # Adaptive thresholds
        if self.adaptive_threshold_manager and self.feature_manager.is_feature_enabled("adaptive_thresholds"):
            thresholds = self.adaptive_threshold_manager.get_current_thresholds()
            data['adaptive_thresholds'] = {
                'adx': thresholds['adx'],
                'rvol': thresholds['rvol']
            }
        
        return data
    
    def get_volume_profile_size_adjustment(self) -> float:
        """Get position size adjustment based on volume profile.
        
        Returns:
            Size multiplier (0.5 for low volume areas, 1.0 otherwise)
        """
        if not self.volume_profile_analyzer or not self.volume_profile_analyzer.current_profile:
            return 1.0
        
        current_price = self.current_indicators.current_price
        if current_price == 0:
            return 1.0
        
        # Check if price is near key levels (POC, VAH, VAL)
        if self.volume_profile_analyzer.is_near_key_level(current_price):
            # Near key levels - good for entries
            return 1.0
        
        # Check if we're in a low volume area
        volume_at_price = self.volume_profile_analyzer.get_volume_at_price(current_price)
        
        if self.volume_profile_analyzer.current_profile.total_volume > 0:
            # Calculate volume percentile at current price
            sorted_volumes = sorted(self.volume_profile_analyzer.current_profile.volumes, reverse=True)
            if sorted_volumes:
                median_volume = sorted_volumes[len(sorted_volumes) // 2]
                
                # If volume at current price is below median, reduce size
                if volume_at_price < median_volume:
                    return self.config.volume_profile_low_volume_size_reduction
        
        return 1.0
    
    def _has_sufficient_data(
        self, 
        candles_15m: List[Candle], 
        candles_1h: List[Candle]
    ) -> bool:
        """Check if there is sufficient data to calculate indicators.
        
        Args:
            candles_15m: List of 15-minute candles
            candles_1h: List of 1-hour candles
            
        Returns:
            True if sufficient data available, False otherwise
        """
        # Need enough data for all indicators
        # ATR and ADX need at least 2 * period candles
        min_15m_candles = max(
            2 * self.config.atr_period,
            2 * self.config.adx_period,
            self.config.rvol_period + 1,
            20  # For squeeze momentum (BB period)
        )
        
        min_1h_candles = max(
            2 * self.config.atr_period,
            3  # For trend determination
        )
        
        return (
            len(candles_15m) >= min_15m_candles and
            len(candles_1h) >= min_1h_candles
        )
    
    def _get_weekly_anchor(self, timestamp_ms: int) -> int:
        """Calculate the most recent weekly anchor time (Monday 00:00 UTC).
        
        Args:
            timestamp_ms: Current timestamp in milliseconds
            
        Returns:
            Timestamp of most recent Monday 00:00 UTC in milliseconds
        """
        # Convert to seconds
        timestamp_s = timestamp_ms // 1000
        
        # Get day of week (0 = Monday, 6 = Sunday)
        import datetime
        dt = datetime.datetime.utcfromtimestamp(timestamp_s)
        days_since_monday = dt.weekday()
        
        # Calculate Monday 00:00 UTC
        monday_dt = dt - datetime.timedelta(
            days=days_since_monday,
            hours=dt.hour,
            minutes=dt.minute,
            seconds=dt.second,
            microseconds=dt.microsecond
        )
        
        # Convert back to milliseconds
        return int(monday_dt.timestamp() * 1000)
