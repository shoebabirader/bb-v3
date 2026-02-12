"""Volume Profile Analyzer for identifying key support/resistance levels."""

from typing import List, Optional, Callable
import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from src.models import Candle, VolumeProfile
from src.config import Config
from src.logger import TradingLogger


class VolumeProfileAnalyzer:
    """Analyzes volume distribution at price levels to identify key support/resistance.
    
    The volume profile shows where trading activity has occurred over a lookback period.
    Key levels include:
    - POC (Point of Control): Price level with highest volume
    - VAH/VAL (Value Area High/Low): Bounds containing 70% of volume
    
    These levels act as magnets for price and high-probability trade zones.
    """
    
    def __init__(self, config: Config):
        """Initialize the Volume Profile Analyzer.
        
        Args:
            config: Configuration object with volume profile parameters
        """
        self.config = config
        self.logger = TradingLogger()
        self.current_profile: Optional[VolumeProfile] = None
        self.last_update: int = 0
        
        # Thread pool for async calculations
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="volume_profile")
        self._calculation_future: Optional[Future] = None
        self._lock = threading.Lock()
        
        self.logger.log_system_event(
            f"VolumeProfileAnalyzer initialized: lookback_days={config.volume_profile_lookback_days}, "
            f"update_interval={config.volume_profile_update_interval}, "
            f"bin_size={config.volume_profile_bin_size}, "
            f"value_area_pct={config.volume_profile_value_area_pct}",
            "INFO"
        )
    
    def calculate_volume_profile(self, candles: List[Candle]) -> VolumeProfile:
        """Calculate volume profile for the given candles.
        
        Creates price bins and aggregates volume at each price level.
        Identifies POC and Value Area (VAH/VAL).
        
        Args:
            candles: List of candles for lookback period (typically 7 days)
            
        Returns:
            VolumeProfile object with calculated levels
        """
        if not candles:
            self.logger.log_system_event("No candles provided for volume profile calculation", "WARNING")
            return VolumeProfile(
                price_levels=[],
                volumes=[],
                poc=0.0,
                vah=0.0,
                val=0.0,
                total_volume=0.0,
                timestamp=int(time.time() * 1000)
            )
        
        # Find price range
        all_highs = [c.high for c in candles]
        all_lows = [c.low for c in candles]
        min_price = min(all_lows)
        max_price = max(all_highs)
        
        # Calculate bin size based on config (0.1% increments)
        bin_size_pct = self.config.volume_profile_bin_size
        price_range = max_price - min_price
        
        # Create price bins
        num_bins = max(1, int(price_range / (min_price * bin_size_pct)))
        bin_width = price_range / num_bins if num_bins > 0 else price_range
        
        # Initialize bins
        price_levels = []
        volumes = []
        
        for i in range(num_bins):
            bin_low = min_price + (i * bin_width)
            bin_high = bin_low + bin_width
            bin_center = (bin_low + bin_high) / 2
            price_levels.append(bin_center)
            volumes.append(0.0)
        
        # Aggregate volume into bins
        for candle in candles:
            # Distribute candle volume across bins it touches
            candle_low = candle.low
            candle_high = candle.high
            candle_volume = candle.volume
            
            # Find which bins this candle touches
            for i, price_level in enumerate(price_levels):
                bin_low = price_level - (bin_width / 2)
                bin_high = price_level + (bin_width / 2)
                
                # Check if candle overlaps with this bin
                if candle_high >= bin_low and candle_low <= bin_high:
                    # Calculate overlap percentage
                    overlap_low = max(candle_low, bin_low)
                    overlap_high = min(candle_high, bin_high)
                    overlap_range = overlap_high - overlap_low
                    candle_range = candle_high - candle_low
                    
                    if candle_range > 0:
                        overlap_pct = overlap_range / candle_range
                    else:
                        # Single price point - assign to nearest bin
                        overlap_pct = 1.0 if i == 0 else 0.0
                    
                    volumes[i] += candle_volume * overlap_pct
        
        total_volume = sum(volumes)
        
        # Create initial profile
        profile = VolumeProfile(
            price_levels=price_levels,
            volumes=volumes,
            poc=0.0,
            vah=0.0,
            val=0.0,
            total_volume=total_volume,
            timestamp=int(time.time() * 1000)
        )
        
        # Identify POC
        profile.poc = self.identify_poc(profile)
        
        # Identify Value Area
        profile.val, profile.vah = self.identify_value_area(profile)
        
        # Update current profile and timestamp
        self.current_profile = profile
        self.last_update = profile.timestamp
        
        self.logger.log_system_event(
            f"Volume profile calculated: num_candles={len(candles)}, num_bins={len(price_levels)}, "
            f"total_volume={total_volume:.2f}, poc={profile.poc:.2f}, "
            f"vah={profile.vah:.2f}, val={profile.val:.2f}",
            "INFO"
        )
        
        return profile
    
    def identify_poc(self, profile: VolumeProfile) -> float:
        """Identify Point of Control (price level with maximum volume).
        
        Args:
            profile: VolumeProfile object
            
        Returns:
            Price level with highest volume
        """
        if not profile.price_levels or not profile.volumes:
            return 0.0
        
        # Find index of maximum volume
        max_volume_idx = 0
        max_volume = profile.volumes[0]
        
        for i, volume in enumerate(profile.volumes):
            if volume > max_volume:
                max_volume = volume
                max_volume_idx = i
        
        return profile.price_levels[max_volume_idx]
    
    def identify_value_area(self, profile: VolumeProfile) -> tuple[float, float]:
        """Identify Value Area High and Low (70% of volume).
        
        The Value Area contains 70% of the total volume, centered around POC.
        
        Args:
            profile: VolumeProfile object
            
        Returns:
            Tuple of (VAL, VAH) - lower and upper bounds of value area
        """
        if not profile.price_levels or not profile.volumes or profile.total_volume == 0:
            return (0.0, 0.0)
        
        # Find POC index
        poc_idx = 0
        for i, price in enumerate(profile.price_levels):
            if abs(price - profile.poc) < 0.01:  # Use small tolerance for float comparison
                poc_idx = i
                break
        
        # Target volume for value area (70% of total)
        target_volume = profile.total_volume * self.config.volume_profile_value_area_pct
        
        # Start from POC and expand outward
        current_volume = profile.volumes[poc_idx]
        lower_idx = poc_idx
        upper_idx = poc_idx
        
        # Expand value area until we reach target volume
        while current_volume < target_volume:
            # Check which direction has more volume
            can_expand_lower = lower_idx > 0
            can_expand_upper = upper_idx < len(profile.volumes) - 1
            
            if not can_expand_lower and not can_expand_upper:
                # No more volume to add - we've included all bins
                break
            
            lower_volume = profile.volumes[lower_idx - 1] if can_expand_lower else 0
            upper_volume = profile.volumes[upper_idx + 1] if can_expand_upper else 0
            
            # Expand in direction with more volume
            if can_expand_lower and can_expand_upper:
                # Both directions available - choose the one with more volume
                if lower_volume >= upper_volume:
                    lower_idx -= 1
                    current_volume += profile.volumes[lower_idx]
                else:
                    upper_idx += 1
                    current_volume += profile.volumes[upper_idx]
            elif can_expand_lower:
                # Only lower direction available
                lower_idx -= 1
                current_volume += profile.volumes[lower_idx]
            elif can_expand_upper:
                # Only upper direction available
                upper_idx += 1
                current_volume += profile.volumes[upper_idx]
        
        val = profile.price_levels[lower_idx]
        vah = profile.price_levels[upper_idx]
        
        return (val, vah)
    
    def is_near_key_level(self, price: float, threshold: Optional[float] = None) -> bool:
        """Check if price is near a key level (POC, VAH, or VAL).
        
        Args:
            price: Current price to check
            threshold: Distance threshold as percentage (default: from config)
            
        Returns:
            True if price is within threshold of any key level
        """
        if self.current_profile is None:
            return False
        
        if threshold is None:
            threshold = self.config.volume_profile_key_level_threshold
        
        # Check distance to each key level
        key_levels = [
            self.current_profile.poc,
            self.current_profile.vah,
            self.current_profile.val
        ]
        
        for level in key_levels:
            if level == 0.0:
                continue
            
            # Calculate percentage distance
            distance_pct = abs(price - level) / level
            
            if distance_pct <= threshold:
                return True
        
        return False
    
    def get_volume_at_price(self, price: float) -> float:
        """Get volume at a specific price level.
        
        Finds the nearest price bin and returns its volume.
        
        Args:
            price: Price level to query
            
        Returns:
            Volume at that price level, or 0.0 if no profile available
        """
        if self.current_profile is None or not self.current_profile.price_levels:
            return 0.0
        
        # Find nearest price level
        min_distance = float('inf')
        nearest_idx = 0
        
        for i, price_level in enumerate(self.current_profile.price_levels):
            distance = abs(price - price_level)
            if distance < min_distance:
                min_distance = distance
                nearest_idx = i
        
        return self.current_profile.volumes[nearest_idx]
    
    def calculate_volume_profile_async(
        self, 
        candles: List[Candle], 
        callback: Optional[Callable[[VolumeProfile], None]] = None
    ) -> Future:
        """Calculate volume profile asynchronously in a background thread.
        
        This method submits the calculation to a thread pool and returns immediately,
        ensuring the main event loop is not blocked.
        
        Args:
            candles: List of candles for lookback period
            callback: Optional callback function to call when calculation completes
            
        Returns:
            Future object that can be used to check status or get result
        """
        def _calculate_and_callback():
            try:
                profile = self.calculate_volume_profile(candles)
                if callback:
                    callback(profile)
                return profile
            except Exception as e:
                self.logger.log_system_event(
                    f"Error in async volume profile calculation: {e}",
                    "ERROR"
                )
                raise
        
        # Cancel any pending calculation
        if self._calculation_future and not self._calculation_future.done():
            self._calculation_future.cancel()
        
        # Submit new calculation
        self._calculation_future = self._executor.submit(_calculate_and_callback)
        
        self.logger.log_system_event(
            "Volume profile calculation submitted to background thread",
            "DEBUG"
        )
        
        return self._calculation_future
    
    def is_calculation_in_progress(self) -> bool:
        """Check if an async calculation is currently in progress.
        
        Returns:
            True if calculation is running, False otherwise
        """
        return (
            self._calculation_future is not None 
            and not self._calculation_future.done()
        )
    
    def get_calculation_result(self, timeout: Optional[float] = None) -> Optional[VolumeProfile]:
        """Get the result of the most recent async calculation.
        
        Args:
            timeout: Maximum time to wait in seconds (None = don't wait)
            
        Returns:
            VolumeProfile if calculation is complete, None otherwise
        """
        if self._calculation_future is None:
            return None
        
        try:
            if timeout is not None:
                return self._calculation_future.result(timeout=timeout)
            elif self._calculation_future.done():
                return self._calculation_future.result()
            else:
                return None
        except Exception as e:
            self.logger.log_system_event(
                f"Error getting async calculation result: {e}",
                "ERROR"
            )
            return None
    
    def shutdown(self):
        """Shutdown the thread pool executor.
        
        Should be called when the analyzer is no longer needed.
        """
        if self._calculation_future and not self._calculation_future.done():
            self._calculation_future.cancel()
        
        self._executor.shutdown(wait=True)
        self.logger.log_system_event("VolumeProfileAnalyzer shutdown complete", "INFO")
