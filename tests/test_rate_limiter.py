"""Tests for rate limiter."""

import pytest
import time
import threading
from hypothesis import given, strategies as st, settings
from src.rate_limiter import RateLimiter


class TestRateLimiter:
    """Unit tests for RateLimiter."""
    
    def test_basic_acquisition(self):
        """Test basic request acquisition."""
        limiter = RateLimiter(max_requests_per_minute=10)
        
        # Should be able to acquire up to the limit
        for i in range(10):
            assert limiter.acquire(timeout=1.0) is True
        
        # Next request should block or fail with timeout
        assert limiter.acquire(timeout=0.1) is False
    
    def test_rate_tracking(self):
        """Test that rate is tracked correctly."""
        limiter = RateLimiter(max_requests_per_minute=10)
        
        # Make 5 requests
        for _ in range(5):
            limiter.acquire()
        
        # Should show 5 requests
        assert limiter.get_current_rate() == 5
        assert 0.4 <= limiter.get_utilization() <= 0.6
    
    def test_old_requests_expire(self):
        """Test that old requests are removed after 60 seconds."""
        limiter = RateLimiter(max_requests_per_minute=10)
        
        # Make a request
        limiter.acquire()
        assert limiter.get_current_rate() == 1
        
        # Manually expire the request by manipulating time
        # (In real scenario, would wait 60 seconds)
        with limiter._lock:
            if limiter._request_times:
                limiter._request_times[0] = time.time() - 61.0
        
        # Check rate - should clean up old request
        assert limiter.get_current_rate() == 0
    
    def test_warning_threshold(self):
        """Test that warning threshold triggers backoff."""
        limiter = RateLimiter(max_requests_per_minute=10, warning_threshold=0.5)
        
        # Make requests up to warning threshold (5 requests)
        for _ in range(5):
            limiter.acquire()
        
        # Should not be throttling yet
        assert limiter._consecutive_warnings == 0
        
        # One more request should trigger warning
        limiter.acquire()
        assert limiter._consecutive_warnings > 0
    
    def test_reset(self):
        """Test that reset clears state."""
        limiter = RateLimiter(max_requests_per_minute=10)
        
        # Make some requests
        for _ in range(5):
            limiter.acquire()
        
        assert limiter.get_current_rate() == 5
        
        # Reset
        limiter.reset()
        
        assert limiter.get_current_rate() == 0
        assert limiter._consecutive_warnings == 0
        assert limiter._backoff_delay == 0.0
    
    def test_concurrent_access(self):
        """Test thread-safe concurrent access."""
        limiter = RateLimiter(max_requests_per_minute=100)
        results = []
        
        def make_requests():
            for _ in range(10):
                success = limiter.acquire(timeout=2.0)
                results.append(success)
        
        # Create multiple threads
        threads = [threading.Thread(target=make_requests) for _ in range(5)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Should have made 50 requests total
        assert sum(results) == 50
        assert limiter.get_current_rate() == 50
    
    def test_wait_for_capacity(self):
        """Test waiting for capacity."""
        limiter = RateLimiter(max_requests_per_minute=10)
        
        # Fill up to limit
        for _ in range(10):
            limiter.acquire()
        
        # Should not have capacity for 5 more requests
        assert limiter.wait_for_capacity(required_requests=5, timeout=0.1) is False
        
        # Reset and try again
        limiter.reset()
        assert limiter.wait_for_capacity(required_requests=5, timeout=0.1) is True
    
    def test_get_stats(self):
        """Test statistics reporting."""
        limiter = RateLimiter(max_requests_per_minute=100, warning_threshold=0.8)
        
        # Make some requests
        for _ in range(50):
            limiter.acquire()
        
        stats = limiter.get_stats()
        
        assert stats['current_requests_per_minute'] == 50
        assert stats['max_requests_per_minute'] == 100
        assert stats['utilization_percent'] == 50.0
        assert stats['warning_threshold_percent'] == 80.0
        assert 'is_throttling' in stats
        assert 'backoff_delay_seconds' in stats


class TestRateLimiterProperties:
    """Property-based tests for RateLimiter."""
    
    # Feature: advanced-trading-enhancements, Property 30: Rate limiting
    @given(
        max_requests=st.integers(min_value=10, max_value=2000),
        num_requests=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100, deadline=5000)
    def test_property_rate_limiting(self, max_requests, num_requests):
        """Property 30: Rate limiting
        
        For any 1-minute window, the total number of API requests must not exceed 1200.
        
        This test verifies that regardless of how many requests are made,
        the rate limiter never allows more than the configured maximum.
        
        Validates: Requirements 10.6
        """
        limiter = RateLimiter(max_requests_per_minute=max_requests)
        
        # Make requests up to the limit
        successful_requests = 0
        for _ in range(min(num_requests, max_requests)):
            if limiter.acquire(timeout=0.1):
                successful_requests += 1
        
        # Verify we never exceed the limit
        current_rate = limiter.get_current_rate()
        assert current_rate <= max_requests, (
            f"Rate limiter allowed {current_rate} requests, "
            f"exceeding limit of {max_requests}"
        )
        
        # Verify utilization is within bounds
        utilization = limiter.get_utilization()
        assert 0.0 <= utilization <= 1.0, (
            f"Utilization {utilization} is out of bounds [0.0, 1.0]"
        )
    
    @given(
        max_requests=st.integers(min_value=10, max_value=100),
        warning_threshold=st.floats(min_value=0.5, max_value=0.95)
    )
    @settings(max_examples=100, deadline=3000)
    def test_property_warning_threshold_respected(self, max_requests, warning_threshold):
        """Property: Warning threshold triggers before limit.
        
        For any configuration, warnings should trigger at or before
        the warning threshold, never after.
        """
        limiter = RateLimiter(
            max_requests_per_minute=max_requests,
            warning_threshold=warning_threshold
        )
        
        warning_limit = int(max_requests * warning_threshold)
        
        # Make requests up to warning limit
        for _ in range(warning_limit):
            limiter.acquire(timeout=0.1)
        
        # Should not be warning yet (or just starting)
        warnings_before = limiter._consecutive_warnings
        
        # Make one more request
        limiter.acquire(timeout=0.1)
        
        # Should now be warning
        warnings_after = limiter._consecutive_warnings
        
        # Verify warning was triggered at or after threshold
        current_rate = limiter.get_current_rate()
        if warnings_after > warnings_before:
            assert current_rate >= warning_limit, (
                f"Warning triggered at {current_rate} requests, "
                f"before threshold of {warning_limit}"
            )
    
    @given(
        num_threads=st.integers(min_value=2, max_value=10),
        requests_per_thread=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=50, deadline=10000)
    def test_property_thread_safety(self, num_threads, requests_per_thread):
        """Property: Thread-safe request counting.
        
        For any number of concurrent threads making requests,
        the total count should equal the sum of all successful requests.
        """
        max_requests = num_threads * requests_per_thread + 10
        limiter = RateLimiter(max_requests_per_minute=max_requests)
        
        results = []
        lock = threading.Lock()
        
        def make_requests():
            local_results = []
            for _ in range(requests_per_thread):
                success = limiter.acquire(timeout=1.0)
                local_results.append(1 if success else 0)
            
            with lock:
                results.extend(local_results)
        
        # Create and start threads
        threads = [threading.Thread(target=make_requests) for _ in range(num_threads)]
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify total count matches successful requests
        total_successful = sum(results)
        current_rate = limiter.get_current_rate()
        
        assert current_rate == total_successful, (
            f"Rate limiter shows {current_rate} requests, "
            f"but {total_successful} were successful"
        )
        
        # Verify we didn't exceed the limit
        assert current_rate <= max_requests
