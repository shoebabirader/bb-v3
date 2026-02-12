"""Timeframe Coordinator for multi-timeframe analysis."""

from typing import List, Dict, Optional
from dataclasses import dataclass
from src.models import Candle
from src.indicators import IndicatorCalculator
from src.config import Config


@dataclass
class TimeframeData:
    """Data for a single timeframe analysis.
    
    Attributes:
        trend: Trend direction ("BULLISH", "BEARISH", "NEUTRAL")
        momentum: Momentum value (float)
        volatility: Volatility measure (ATR)
        volume_trend: Volume trend ("INCREASING", "DECREASING", "STABLE")
    """
    trend: str  # "BULLISH", "BEARISH", "NEUTRAL"
    momentum: float
    volatility: float
    volume_trend: str  # "INCREASING", "DECREASING", "STABLE"


@dataclass
class TimeframeAnalysis:
    """Complete multi-timeframe analysis result.
    
    Attributes:
        timeframe_5m: Analysis for 5-minute timeframe
        timeframe_15m: Analysis for 15-minute timeframe
        timeframe_1h: Analysis for 1-hour timeframe
        timeframe_4h: Analysis for 4-hour timeframe
        alignment_score: Number of aligned timeframes (0-4)
        confidence: Signal confidence (0.0-1.0)
        overall_direction: Overall trend direction ("BULLISH", "BEARISH", "NEUTRAL")
    """
    timeframe_5m: Optional[TimeframeData]
    timeframe_15m: Optional[TimeframeData]
    timeframe_1h: Optional[TimeframeData]
    timeframe_4h: Optional[TimeframeData]
    alignment_score: int  # 0-4
    confidence: float  # 0.0-1.0
    overall_direction: str  # "BULLISH", "BEARISH", "NEUTRAL"


class TimeframeCoordinator:
    """Coordinates analysis across multiple timeframes.
    
    Analyzes 5m, 15m, 1h, and 4h timeframes to generate confidence-weighted
    trading signals based on timeframe alignment.
    """
    
    def __init__(self, config: Config, indicator_calc: IndicatorCalculator):
        """Initialize TimeframeCoordinator.
        
        Args:
            config: Configuration object
            indicator_calc: IndicatorCalculator instance for technical analysis
        """
        self.config = config
        self.indicator_calc = indicator_calc
        self.timeframes = ['5m', '15m', '1h', '4h']
        
        # Timeframe weights from config (4h=40%, 1h=30%, 15m=20%, 5m=10%)
        self.weights = config.timeframe_weights
    
    def analyze_all_timeframes(
        self,
        candles_5m: List[Candle],
        candles_15m: List[Candle],
        candles_1h: List[Candle],
        candles_4h: List[Candle]
    ) -> TimeframeAnalysis:
        """Analyze all timeframes and return consolidated analysis.
        
        Args:
            candles_5m: List of 5-minute candles
            candles_15m: List of 15-minute candles
            candles_1h: List of 1-hour candles
            candles_4h: List of 4-hour candles
            
        Returns:
            TimeframeAnalysis with complete multi-timeframe analysis
        """
        # Analyze each timeframe
        tf_5m = self._analyze_timeframe(candles_5m, "5m") if candles_5m else None
        tf_15m = self._analyze_timeframe(candles_15m, "15m") if candles_15m else None
        tf_1h = self._analyze_timeframe(candles_1h, "1h") if candles_1h else None
        tf_4h = self._analyze_timeframe(candles_4h, "4h") if candles_4h else None
        
        # Create analysis object
        analysis = TimeframeAnalysis(
            timeframe_5m=tf_5m,
            timeframe_15m=tf_15m,
            timeframe_1h=tf_1h,
            timeframe_4h=tf_4h,
            alignment_score=0,
            confidence=0.0,
            overall_direction="NEUTRAL"
        )
        
        # Calculate alignment and confidence
        analysis.alignment_score = self.check_timeframe_alignment(analysis)
        analysis.confidence = self.calculate_signal_confidence(analysis)
        analysis.overall_direction = self._determine_overall_direction(analysis)
        
        return analysis
    
    def _analyze_timeframe(self, candles: List[Candle], timeframe: str) -> TimeframeData:
        """Analyze a single timeframe.
        
        Args:
            candles: List of candles for this timeframe
            timeframe: Timeframe identifier (e.g., "5m", "1h")
            
        Returns:
            TimeframeData with analysis results
        """
        if not candles or len(candles) < 20:
            return TimeframeData(
                trend="NEUTRAL",
                momentum=0.0,
                volatility=0.0,
                volume_trend="STABLE"
            )
        
        # Calculate indicators
        vwap = self.indicator_calc.calculate_vwap(candles, candles[0].timestamp)
        atr = self.indicator_calc.calculate_atr(candles)
        
        # Determine trend
        trend = self.indicator_calc.determine_trend(candles, vwap)
        
        # Calculate momentum (simple price change over last 10 candles)
        if len(candles) >= 10:
            momentum = (candles[-1].close - candles[-10].close) / candles[-10].close
        else:
            momentum = 0.0
        
        # Determine volume trend
        volume_trend = self._calculate_volume_trend(candles)
        
        return TimeframeData(
            trend=trend,
            momentum=momentum,
            volatility=atr,
            volume_trend=volume_trend
        )
    
    def _calculate_volume_trend(self, candles: List[Candle]) -> str:
        """Calculate volume trend for a timeframe.
        
        Args:
            candles: List of candles
            
        Returns:
            Volume trend: "INCREASING", "DECREASING", or "STABLE"
        """
        if len(candles) < 10:
            return "STABLE"
        
        # Compare recent volume to earlier volume
        recent_avg = sum(c.volume for c in candles[-5:]) / 5
        earlier_avg = sum(c.volume for c in candles[-10:-5]) / 5
        
        if earlier_avg == 0:
            return "STABLE"
        
        change = (recent_avg - earlier_avg) / earlier_avg
        
        if change > 0.2:  # 20% increase
            return "INCREASING"
        elif change < -0.2:  # 20% decrease
            return "DECREASING"
        else:
            return "STABLE"
    
    def check_timeframe_alignment(self, analysis: TimeframeAnalysis) -> int:
        """Check how many timeframes are aligned.
        
        Args:
            analysis: TimeframeAnalysis object
            
        Returns:
            Number of aligned timeframes (0-4)
        """
        timeframes = [
            analysis.timeframe_5m,
            analysis.timeframe_15m,
            analysis.timeframe_1h,
            analysis.timeframe_4h
        ]
        
        # Filter out None values
        valid_timeframes = [tf for tf in timeframes if tf is not None]
        
        if not valid_timeframes:
            return 0
        
        # Count how many timeframes agree on trend direction
        # We need a dominant trend direction
        bullish_count = sum(1 for tf in valid_timeframes if tf.trend == "BULLISH")
        bearish_count = sum(1 for tf in valid_timeframes if tf.trend == "BEARISH")
        
        # Return the count of the dominant direction
        return max(bullish_count, bearish_count)
    
    def calculate_signal_confidence(self, analysis: TimeframeAnalysis) -> float:
        """Calculate signal confidence based on timeframe alignment.
        
        Args:
            analysis: TimeframeAnalysis object
            
        Returns:
            Confidence value (0.0-1.0)
        """
        alignment = analysis.alignment_score
        
        # Confidence based on alignment:
        # 4 aligned = 1.0 (high confidence)
        # 3 aligned = 0.7 (medium confidence)
        # <3 aligned = 0.0 (no signal)
        if alignment >= 4:
            return 1.0
        elif alignment == 3:
            return 0.7
        else:
            return 0.0
    
    def _determine_overall_direction(self, analysis: TimeframeAnalysis) -> str:
        """Determine overall trend direction using weighted voting.
        
        Args:
            analysis: TimeframeAnalysis object
            
        Returns:
            Overall direction: "BULLISH", "BEARISH", or "NEUTRAL"
        """
        timeframes = {
            '5m': analysis.timeframe_5m,
            '15m': analysis.timeframe_15m,
            '1h': analysis.timeframe_1h,
            '4h': analysis.timeframe_4h
        }
        
        bullish_weight = 0.0
        bearish_weight = 0.0
        
        for tf_name, tf_data in timeframes.items():
            if tf_data is None:
                continue
            
            weight = self.weights.get(tf_name, 0.0)
            
            if tf_data.trend == "BULLISH":
                bullish_weight += weight
            elif tf_data.trend == "BEARISH":
                bearish_weight += weight
        
        # Determine overall direction based on weighted votes
        if bullish_weight > bearish_weight and bullish_weight > 0.5:
            return "BULLISH"
        elif bearish_weight > bullish_weight and bearish_weight > 0.5:
            return "BEARISH"
        else:
            return "NEUTRAL"
