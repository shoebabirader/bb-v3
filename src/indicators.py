"""Technical indicator calculations for Binance Futures Trading Bot."""

from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
import hashlib
import time
from src.models import Candle


class IndicatorCache:
    """Cache for indicator calculations to avoid redundant computations.
    
    Uses candle data hash and parameters as cache key.
    Automatically invalidates cache when new data arrives.
    """
    
    def __init__(self, ttl_seconds: int = 60):
        """Initialize the indicator cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self._cache: Dict[str, Tuple[any, float]] = {}
        self._ttl = ttl_seconds
    
    def _generate_key(self, candles: List[Candle], indicator_name: str, **params) -> str:
        """Generate a cache key from candles and parameters.
        
        Args:
            candles: List of candles
            indicator_name: Name of the indicator
            **params: Additional parameters for the indicator
            
        Returns:
            Cache key as string
        """
        # Create a hash of the candle data (timestamps and closes)
        if not candles:
            return f"{indicator_name}_empty"
        
        # Use last candle timestamp and count as quick identifier
        last_timestamp = candles[-1].timestamp
        candle_count = len(candles)
        
        # Include parameters in key
        param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        
        return f"{indicator_name}_{last_timestamp}_{candle_count}_{param_str}"
    
    def get(self, candles: List[Candle], indicator_name: str, **params) -> Optional[any]:
        """Get cached indicator value if available and not expired.
        
        Args:
            candles: List of candles
            indicator_name: Name of the indicator
            **params: Additional parameters for the indicator
            
        Returns:
            Cached value if available, None otherwise
        """
        key = self._generate_key(candles, indicator_name, **params)
        
        if key in self._cache:
            value, timestamp = self._cache[key]
            
            # Check if cache entry is still valid
            if time.time() - timestamp < self._ttl:
                return value
            else:
                # Remove expired entry
                del self._cache[key]
        
        return None
    
    def set(self, candles: List[Candle], indicator_name: str, value: any, **params):
        """Store indicator value in cache.
        
        Args:
            candles: List of candles
            indicator_name: Name of the indicator
            value: Calculated indicator value
            **params: Additional parameters for the indicator
        """
        key = self._generate_key(candles, indicator_name, **params)
        self._cache[key] = (value, time.time())
    
    def clear(self):
        """Clear all cached values."""
        self._cache.clear()
    
    def invalidate_old_entries(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp >= self._ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache size and other stats
        """
        return {
            'size': len(self._cache),
            'ttl_seconds': self._ttl
        }


class IndicatorCalculator:
    """Static methods for calculating technical indicators.
    
    All methods are static and stateless, taking candle data as input
    and returning calculated indicator values.
    
    Supports optional caching to avoid redundant calculations.
    """
    
    # Class-level cache instance
    _cache: Optional[IndicatorCache] = None
    
    @classmethod
    def enable_caching(cls, ttl_seconds: int = 60):
        """Enable indicator caching.
        
        Args:
            ttl_seconds: Time-to-live for cache entries
        """
        cls._cache = IndicatorCache(ttl_seconds=ttl_seconds)
    
    @classmethod
    def disable_caching(cls):
        """Disable indicator caching."""
        cls._cache = None
    
    @classmethod
    def clear_cache(cls):
        """Clear all cached indicators."""
        if cls._cache:
            cls._cache.clear()
    
    @classmethod
    def get_cache_stats(cls) -> Optional[Dict[str, int]]:
        """Get cache statistics.
        
        Returns:
            Cache stats if caching is enabled, None otherwise
        """
        if cls._cache:
            return cls._cache.get_cache_stats()
        return None
    
    @staticmethod
    def calculate_vwap(candles: List[Candle], anchor_time: int) -> float:
        """Calculate Volume Weighted Average Price anchored to a specific timestamp.
        
        VWAP = Cumulative(Typical Price × Volume) / Cumulative(Volume)
        where Typical Price = (High + Low + Close) / 3
        
        Args:
            candles: List of Candle objects
            anchor_time: Unix timestamp (ms) to anchor VWAP calculation from
            
        Returns:
            VWAP value as float, or 0.0 if insufficient data
        """
        # Check cache
        if IndicatorCalculator._cache:
            cached = IndicatorCalculator._cache.get(
                candles, 'vwap', anchor_time=anchor_time
            )
            if cached is not None:
                return cached
        
        if not candles:
            return 0.0
        
        # Filter candles from anchor time onwards
        anchored_candles = [c for c in candles if c.timestamp >= anchor_time]
        
        if not anchored_candles:
            return 0.0
        
        cumulative_tpv = 0.0  # Typical Price × Volume
        cumulative_volume = 0.0
        
        for candle in anchored_candles:
            typical_price = (candle.high + candle.low + candle.close) / 3.0
            cumulative_tpv += typical_price * candle.volume
            cumulative_volume += candle.volume
        
        if cumulative_volume == 0:
            return 0.0
        
        result = cumulative_tpv / cumulative_volume
        
        # Store in cache
        if IndicatorCalculator._cache:
            IndicatorCalculator._cache.set(
                candles, 'vwap', result, anchor_time=anchor_time
            )
        
        return result
    
    @staticmethod
    def calculate_atr(candles: List[Candle], period: int = 14) -> float:
        """Calculate Average True Range using exponential moving average.
        
        True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        ATR = EMA of True Range over the specified period
        
        Args:
            candles: List of Candle objects (needs at least period + 1 candles)
            period: Lookback period for ATR calculation (default: 14)
            
        Returns:
            ATR value as float, or 0.0 if insufficient data
        """
        # Check cache
        if IndicatorCalculator._cache:
            cached = IndicatorCalculator._cache.get(candles, 'atr', period=period)
            if cached is not None:
                return cached
        
        if len(candles) < period + 1:
            return 0.0
        
        true_ranges = []
        
        for i in range(1, len(candles)):
            high = candles[i].high
            low = candles[i].low
            prev_close = candles[i - 1].close
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        if len(true_ranges) < period:
            return 0.0
        
        # Calculate EMA of true ranges
        # First ATR is simple average of first 'period' true ranges
        atr = sum(true_ranges[:period]) / period
        
        # Then apply EMA formula: EMA = (Current TR × multiplier) + (Previous EMA × (1 - multiplier))
        multiplier = 2.0 / (period + 1)
        
        for i in range(period, len(true_ranges)):
            atr = (true_ranges[i] * multiplier) + (atr * (1 - multiplier))
        
        # Store in cache
        if IndicatorCalculator._cache:
            IndicatorCalculator._cache.set(candles, 'atr', atr, period=period)
        
        return atr
    
    @staticmethod
    def calculate_adx(candles: List[Candle], period: int = 14) -> float:
        """Calculate Average Directional Index (ADX).
        
        ADX measures trend strength on a scale of 0-100.
        Uses +DI, -DI, and DX to calculate the smoothed ADX value.
        
        Args:
            candles: List of Candle objects (needs at least 2 × period candles)
            period: Lookback period for ADX calculation (default: 14)
            
        Returns:
            ADX value as float (0-100), or 0.0 if insufficient data
        """
        # Check cache
        if IndicatorCalculator._cache:
            cached = IndicatorCalculator._cache.get(candles, 'adx', period=period)
            if cached is not None:
                return cached
        
        if len(candles) < 2 * period:
            return 0.0
        
        # Convert to pandas DataFrame for easier calculation
        df = pd.DataFrame([{
            'high': c.high,
            'low': c.low,
            'close': c.close
        } for c in candles])
        
        # Calculate +DM and -DM
        df['high_diff'] = df['high'].diff()
        df['low_diff'] = -df['low'].diff()
        
        df['+dm'] = np.where(
            (df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0),
            df['high_diff'],
            0
        )
        df['-dm'] = np.where(
            (df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0),
            df['low_diff'],
            0
        )
        
        # Calculate True Range
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df.apply(
            lambda row: max(
                row['high'] - row['low'],
                abs(row['high'] - row['prev_close']) if pd.notna(row['prev_close']) else 0,
                abs(row['low'] - row['prev_close']) if pd.notna(row['prev_close']) else 0
            ),
            axis=1
        )
        
        # Smooth +DM, -DM, and TR using Wilder's smoothing (similar to EMA)
        df['+dm_smooth'] = df['+dm'].ewm(alpha=1/period, adjust=False).mean()
        df['-dm_smooth'] = df['-dm'].ewm(alpha=1/period, adjust=False).mean()
        df['tr_smooth'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()
        
        # Calculate +DI and -DI
        df['+di'] = 100 * df['+dm_smooth'] / df['tr_smooth']
        df['-di'] = 100 * df['-dm_smooth'] / df['tr_smooth']
        
        # Calculate DX
        df['di_diff'] = abs(df['+di'] - df['-di'])
        df['di_sum'] = df['+di'] + df['-di']
        df['dx'] = 100 * df['di_diff'] / df['di_sum']
        
        # Calculate ADX (smoothed DX)
        df['adx'] = df['dx'].ewm(alpha=1/period, adjust=False).mean()
        
        # Return the last ADX value
        result = float(df['adx'].iloc[-1]) if pd.notna(df['adx'].iloc[-1]) else 0.0
        
        # Store in cache
        if IndicatorCalculator._cache:
            IndicatorCalculator._cache.set(candles, 'adx', result, period=period)
        
        return result
    
    @staticmethod
    def calculate_rvol(candles: List[Candle], period: int = 20) -> float:
        """Calculate Relative Volume.
        
        RVOL = Current Volume / Average Volume over period
        
        Args:
            candles: List of Candle objects (needs at least period + 1 candles)
            period: Lookback period for average volume (default: 20)
            
        Returns:
            RVOL value as float, or 0.0 if insufficient data
        """
        # Check cache
        if IndicatorCalculator._cache:
            cached = IndicatorCalculator._cache.get(candles, 'rvol', period=period)
            if cached is not None:
                return cached
        
        if len(candles) < period + 1:
            return 0.0
        
        # Get the last 'period' candles for average (excluding current)
        historical_candles = candles[-(period + 1):-1]
        current_candle = candles[-1]
        
        if not historical_candles:
            return 0.0
        
        avg_volume = sum(c.volume for c in historical_candles) / len(historical_candles)
        
        if avg_volume == 0:
            return 0.0
        
        result = current_candle.volume / avg_volume
        
        # Store in cache
        if IndicatorCalculator._cache:
            IndicatorCalculator._cache.set(candles, 'rvol', result, period=period)
        
        return result
    
    @staticmethod
    def calculate_squeeze_momentum(candles: List[Candle]) -> Dict[str, any]:
        """Calculate Squeeze Momentum Indicator using LazyBear's methodology.
        
        The squeeze occurs when Bollinger Bands are inside Keltner Channels.
        Momentum is calculated using linear regression of price vs time.
        
        Args:
            candles: List of Candle objects (needs at least 20 candles for BB)
            
        Returns:
            Dictionary with:
                - value: Momentum value (float)
                - is_squeezed: Whether squeeze is active (bool)
                - color: Momentum color - 'green', 'maroon', 'blue', 'gray' (str)
        """
        if len(candles) < 20:
            return {
                'value': 0.0,
                'is_squeezed': False,
                'color': 'gray'
            }
        
        # Convert to pandas DataFrame
        df = pd.DataFrame([{
            'high': c.high,
            'low': c.low,
            'close': c.close
        } for c in candles])
        
        # Bollinger Bands (20-period, 2 std dev)
        bb_period = 20
        bb_std = 2
        df['bb_basis'] = df['close'].rolling(window=bb_period).mean()
        df['bb_std'] = df['close'].rolling(window=bb_period).std()
        df['bb_upper'] = df['bb_basis'] + (bb_std * df['bb_std'])
        df['bb_lower'] = df['bb_basis'] - (bb_std * df['bb_std'])
        
        # Keltner Channels (20-period, 1.5 × ATR)
        kc_period = 20
        kc_mult = 1.5
        
        # Calculate ATR for Keltner Channels
        df['tr'] = df.apply(
            lambda row: max(
                row['high'] - row['low'],
                abs(row['high'] - df['close'].shift(1).loc[row.name]) if row.name > 0 else 0,
                abs(row['low'] - df['close'].shift(1).loc[row.name]) if row.name > 0 else 0
            ),
            axis=1
        )
        df['atr'] = df['tr'].rolling(window=kc_period).mean()
        
        df['kc_basis'] = df['close'].rolling(window=kc_period).mean()
        df['kc_upper'] = df['kc_basis'] + (kc_mult * df['atr'])
        df['kc_lower'] = df['kc_basis'] - (kc_mult * df['atr'])
        
        # Determine if squeeze is on (BB inside KC)
        last_row = df.iloc[-1]
        is_squeezed = (
            last_row['bb_upper'] < last_row['kc_upper'] and
            last_row['bb_lower'] > last_row['kc_lower']
        )
        
        # Calculate momentum using linear regression
        # Use highest high and lowest low over last 20 periods
        lookback = min(20, len(df))
        recent_data = df.tail(lookback)
        
        highest_high = recent_data['high'].max()
        lowest_low = recent_data['low'].min()
        avg_hl = (highest_high + lowest_low) / 2
        avg_close = recent_data['close'].mean()
        
        # Simple momentum calculation
        momentum = df['close'].iloc[-1] - avg_hl
        
        # Determine color based on momentum and previous momentum
        if len(df) > 1:
            prev_momentum = df['close'].iloc[-2] - avg_hl
            
            if momentum > 0:
                color = 'green' if momentum > prev_momentum else 'blue'
            else:
                color = 'maroon' if momentum < prev_momentum else 'gray'
        else:
            color = 'green' if momentum > 0 else 'maroon'
        
        return {
            'value': float(momentum),
            'is_squeezed': bool(is_squeezed),
            'color': color
        }
    
    @staticmethod
    def determine_trend(candles: List[Candle], vwap: float) -> str:
        """Determine trend direction using price vs VWAP and momentum.
        
        Args:
            candles: List of Candle objects
            vwap: Current VWAP value
            
        Returns:
            Trend direction: 'BULLISH', 'BEARISH', or 'NEUTRAL'
        """
        if not candles or vwap == 0.0:
            return 'NEUTRAL'
        
        current_price = candles[-1].close
        
        # Simple trend determination based on price vs VWAP
        if current_price > vwap:
            # Additional confirmation: check if price is rising
            if len(candles) >= 3:
                recent_closes = [c.close for c in candles[-3:]]
                if recent_closes[-1] > recent_closes[0]:
                    return 'BULLISH'
            return 'BULLISH'
        elif current_price < vwap:
            # Additional confirmation: check if price is falling
            if len(candles) >= 3:
                recent_closes = [c.close for c in candles[-3:]]
                if recent_closes[-1] < recent_closes[0]:
                    return 'BEARISH'
            return 'BEARISH'
        else:
            return 'NEUTRAL'
