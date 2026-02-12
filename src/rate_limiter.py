"""Rate limiter for API requests to stay within Binance limits."""

import time
import threading
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter to ensure API requests stay within allowed limits.
    
    Tracks requests per minute and implements exponential backoff when
    approaching limits. Binance allows 1200 requests per minute.
    """
    
    def __init__(self, max_requests_per_minute: int = 1200, warning_threshold: float = 0.8):
        """Initialize the rate limiter.
        
        Args:
            max_requests_per_minute: Maximum allowed requests per minute
            warning_threshold: Threshold (0-1) at which to start warning/throttling
        """
        self.max_requests = max_requests_per_minute
        self.warning_threshold = warning_threshold
        self.warning_limit = int(max_requests_per_minute * warning_threshold)
        
        # Track request timestamps (in seconds)
        self._request_times: deque = deque()
        self._lock = threading.Lock()
        
        # Backoff state
        self._backoff_delay = 0.0
        self._consecutive_warnings = 0
        
        logger.info(
            f"RateLimiter initialized: max={max_requests_per_minute}/min, "
            f"warning_threshold={warning_threshold * 100}%"
        )
    
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make an API request.
        
        This method blocks if necessary to stay within rate limits.
        Implements exponential backoff when approaching limits.
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait indefinitely)
            
        Returns:
            True if permission granted, False if timeout exceeded
        """
        start_time = time.time()
        
        while True:
            with self._lock:
                # Clean up old request times (older than 1 minute)
                current_time = time.time()
                cutoff_time = current_time - 60.0
                
                while self._request_times and self._request_times[0] < cutoff_time:
                    self._request_times.popleft()
                
                # Check current request count
                current_count = len(self._request_times)
                
                # If under limit, allow request
                if current_count < self.max_requests:
                    # Record this request
                    self._request_times.append(current_time)
                    
                    # Check if we're approaching the warning threshold
                    if current_count >= self.warning_limit:
                        self._consecutive_warnings += 1
                        logger.warning(
                            f"Rate limit warning: {current_count}/{self.max_requests} "
                            f"requests in last minute ({current_count/self.max_requests*100:.1f}%)"
                        )
                        
                        # Calculate backoff delay (exponential)
                        self._backoff_delay = min(2.0 ** (self._consecutive_warnings - 1), 10.0)
                    else:
                        # Reset backoff if we're back under warning threshold
                        if self._consecutive_warnings > 0:
                            logger.info("Rate limit back to normal levels")
                        self._consecutive_warnings = 0
                        self._backoff_delay = 0.0
                    
                    return True
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.error(f"Rate limiter timeout after {elapsed:.2f}s")
                    return False
            
            # Calculate wait time
            if self._backoff_delay > 0:
                wait_time = self._backoff_delay
                logger.debug(f"Applying backoff delay: {wait_time:.2f}s")
            else:
                # Wait until oldest request expires (plus small buffer)
                if self._request_times:
                    oldest_request = self._request_times[0]
                    wait_time = max(0.1, (oldest_request + 60.0) - time.time() + 0.1)
                else:
                    wait_time = 0.1
            
            # Sleep outside the lock
            time.sleep(wait_time)
    
    def get_current_rate(self) -> int:
        """Get the current number of requests in the last minute.
        
        Returns:
            Number of requests in the last 60 seconds
        """
        with self._lock:
            # Clean up old request times
            current_time = time.time()
            cutoff_time = current_time - 60.0
            
            while self._request_times and self._request_times[0] < cutoff_time:
                self._request_times.popleft()
            
            return len(self._request_times)
    
    def get_utilization(self) -> float:
        """Get the current rate limit utilization as a percentage.
        
        Returns:
            Utilization percentage (0.0 to 1.0)
        """
        current_rate = self.get_current_rate()
        return current_rate / self.max_requests
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics.
        
        Returns:
            Dictionary with current stats
        """
        current_rate = self.get_current_rate()
        utilization = current_rate / self.max_requests
        
        return {
            'current_requests_per_minute': current_rate,
            'max_requests_per_minute': self.max_requests,
            'utilization_percent': utilization * 100,
            'warning_threshold_percent': self.warning_threshold * 100,
            'is_throttling': self._backoff_delay > 0,
            'backoff_delay_seconds': self._backoff_delay,
            'consecutive_warnings': self._consecutive_warnings
        }
    
    def reset(self):
        """Reset the rate limiter state.
        
        Clears all tracked requests and backoff state.
        """
        with self._lock:
            self._request_times.clear()
            self._backoff_delay = 0.0
            self._consecutive_warnings = 0
            logger.info("Rate limiter reset")
    
    def wait_for_capacity(self, required_requests: int = 1, timeout: Optional[float] = None) -> bool:
        """Wait until there's capacity for the specified number of requests.
        
        Args:
            required_requests: Number of requests that need capacity
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if capacity available, False if timeout
        """
        start_time = time.time()
        
        while True:
            current_rate = self.get_current_rate()
            available_capacity = self.max_requests - current_rate
            
            if available_capacity >= required_requests:
                return True
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False
            
            # Wait a bit and check again
            time.sleep(0.5)
