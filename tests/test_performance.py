"""Performance tests for advanced trading enhancements."""

import pytest
import time
import psutil
import os
from unittest.mock import Mock, MagicMock
from src.ml_predictor import MLPredictor
from src.volume_profile_analyzer import VolumeProfileAnalyzer
from src.config import Config
from src.models import Candle


class TestPerformance:
    """Performance tests for advanced features.
    
    Tests verify that components meet performance requirements:
    - ML prediction latency < 100ms
    - Memory usage < 500MB
    - Async operations don't block
    """
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = Config()
        config.ml_enabled = True
        config.ml_model_path = "test_model.pkl"
        config.volume_profile_lookback_days = 7
        config.volume_profile_update_interval = 14400
        config.volume_profile_bin_size = 0.001
        config.volume_profile_value_area_pct = 0.7
        config.volume_profile_key_level_threshold = 0.005
        return config
    
    @pytest.fixture
    def sample_candles(self):
        """Create sample candle data for testing."""
        candles = []
        base_time = int(time.time() * 1000)
        base_price = 50000.0
        
        for i in range(1000):
            timestamp = base_time - (1000 - i) * 15 * 60 * 1000  # 15-minute candles
            price = base_price + (i % 100) * 10
            
            candle = Candle(
                timestamp=timestamp,
                open=price,
                high=price + 50,
                low=price - 50,
                close=price + (i % 2) * 20 - 10,
                volume=1000000.0 + (i % 50) * 10000
            )
            candles.append(candle)
        
        return candles
    
    def test_ml_prediction_latency(self, config, sample_candles):
        """Test ML prediction latency < 100ms.
        
        Validates: Requirements 10.3
        """
        predictor = MLPredictor(config)
        
        # Mock the model to avoid actual ML computation
        predictor.model = Mock()
        predictor.model.predict_proba = Mock(return_value=[[0.3, 0.7]])
        predictor.feature_scaler = Mock()
        predictor.feature_scaler.transform = Mock(return_value=[[0.5] * 20])
        
        # Measure prediction time
        start_time = time.time()
        result = predictor.predict(sample_candles[-100:])
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Should complete in under 100ms
        assert latency_ms < 100, (
            f"ML prediction took {latency_ms:.2f}ms, exceeding 100ms requirement"
        )
        
        # Verify result is valid
        assert 0.0 <= result <= 1.0
    
    def test_ml_prediction_latency_multiple_runs(self, config, sample_candles):
        """Test ML prediction latency over multiple runs.
        
        Validates: Requirements 10.3
        """
        predictor = MLPredictor(config)
        
        # Mock the model
        predictor.model = Mock()
        predictor.model.predict_proba = Mock(return_value=[[0.3, 0.7]])
        predictor.feature_scaler = Mock()
        predictor.feature_scaler.transform = Mock(return_value=[[0.5] * 20])
        
        # Run multiple predictions and measure average latency
        latencies = []
        num_runs = 50
        
        for _ in range(num_runs):
            start_time = time.time()
            predictor.predict(sample_candles[-100:])
            end_time = time.time()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        # Average should be well under 100ms
        assert avg_latency < 100, (
            f"Average ML prediction latency {avg_latency:.2f}ms exceeds 100ms"
        )
        
        # Even max should be under 100ms
        assert max_latency < 100, (
            f"Max ML prediction latency {max_latency:.2f}ms exceeds 100ms"
        )
    
    def test_memory_usage_estimate(self, config, sample_candles):
        """Test memory usage stays under 500MB.
        
        This is a basic estimate test. Real memory usage would be measured
        in integration tests with all components running.
        
        Validates: Requirements 10.4
        """
        # Get current process
        process = psutil.Process(os.getpid())
        
        # Measure initial memory
        initial_memory_mb = process.memory_info().rss / (1024 * 1024)
        
        # Create multiple components
        predictors = []
        analyzers = []
        
        for _ in range(5):  # Simulate 5 symbols
            predictor = MLPredictor(config)
            predictor.model = Mock()
            predictors.append(predictor)
            
            analyzer = VolumeProfileAnalyzer(config)
            analyzers.append(analyzer)
        
        # Calculate volume profiles (memory intensive)
        for analyzer in analyzers:
            analyzer.calculate_volume_profile(sample_candles)
        
        # Measure final memory
        final_memory_mb = process.memory_info().rss / (1024 * 1024)
        memory_increase_mb = final_memory_mb - initial_memory_mb
        
        # Memory increase should be reasonable (< 100MB for this test)
        # In production with full data, total should stay < 500MB
        assert memory_increase_mb < 100, (
            f"Memory increased by {memory_increase_mb:.2f}MB, "
            f"which may indicate memory leak or excessive usage"
        )
    
    def test_async_volume_profile_calculation(self, config, sample_candles):
        """Test async volume profile calculation doesn't block.
        
        Validates: Requirements 10.2
        """
        analyzer = VolumeProfileAnalyzer(config)
        
        # Start async calculation
        start_time = time.time()
        future = analyzer.calculate_volume_profile_async(sample_candles)
        submission_time = time.time()
        
        # Submission should be nearly instant (< 10ms)
        submission_latency_ms = (submission_time - start_time) * 1000
        assert submission_latency_ms < 10, (
            f"Async submission took {submission_latency_ms:.2f}ms, "
            f"indicating it may be blocking"
        )
        
        # Wait for result (calculation may complete very quickly)
        result = analyzer.get_calculation_result(timeout=5.0)
        
        # Should complete successfully
        assert result is not None
        assert result.poc > 0
        assert result.vah > 0
        assert result.val > 0
        
        # Verify the future completed
        assert future.done()
        
        # Cleanup
        analyzer.shutdown()
    
    def test_async_operations_concurrent(self, config, sample_candles):
        """Test multiple async operations can run concurrently.
        
        Validates: Requirements 10.2
        """
        analyzers = []
        futures = []
        
        # Start multiple async calculations
        start_time = time.time()
        
        for _ in range(3):
            analyzer = VolumeProfileAnalyzer(config)
            future = analyzer.calculate_volume_profile_async(sample_candles)
            analyzers.append(analyzer)
            futures.append(future)
        
        submission_time = time.time()
        
        # All submissions should be fast
        total_submission_time_ms = (submission_time - start_time) * 1000
        assert total_submission_time_ms < 50, (
            f"Submitting 3 async calculations took {total_submission_time_ms:.2f}ms"
        )
        
        # Wait for all to complete
        results = []
        for analyzer in analyzers:
            result = analyzer.get_calculation_result(timeout=5.0)
            results.append(result)
        
        # All should complete successfully
        assert all(r is not None for r in results)
        assert all(r.poc > 0 for r in results)
        
        # Cleanup
        for analyzer in analyzers:
            analyzer.shutdown()
    
    def test_indicator_caching_performance(self):
        """Test that indicator caching improves performance.
        
        Validates: Requirements 10.7
        """
        from src.indicators import IndicatorCalculator
        
        # Create sample candles
        candles = []
        base_time = int(time.time() * 1000)
        for i in range(100):
            candle = Candle(
                timestamp=base_time + i * 60000,
                open=50000.0 + i,
                high=50100.0 + i,
                low=49900.0 + i,
                close=50050.0 + i,
                volume=1000000.0
            )
            candles.append(candle)
        
        # Measure without caching
        IndicatorCalculator.disable_caching()
        
        start_time = time.time()
        for _ in range(100):
            IndicatorCalculator.calculate_atr(candles, period=14)
        no_cache_time = time.time() - start_time
        
        # Measure with caching
        IndicatorCalculator.enable_caching(ttl_seconds=60)
        
        start_time = time.time()
        for _ in range(100):
            IndicatorCalculator.calculate_atr(candles, period=14)
        cache_time = time.time() - start_time
        
        # Caching should be significantly faster (at least 2x)
        speedup = no_cache_time / cache_time if cache_time > 0 else float('inf')
        
        assert speedup > 2.0, (
            f"Caching only provided {speedup:.2f}x speedup, expected > 2x"
        )
        
        # Cleanup
        IndicatorCalculator.disable_caching()
    
    def test_data_cleanup_performance(self):
        """Test that data cleanup runs efficiently.
        
        Validates: Requirements 10.8
        """
        from src.data_manager import DataManager
        from collections import deque
        
        config = Config()
        config.symbol = "BTCUSDT"
        
        # Create data manager without client (for testing)
        manager = DataManager(config, client=None)
        
        # Fill buffers with old data
        base_time = int(time.time() * 1000)
        old_time = base_time - (30 * 24 * 60 * 60 * 1000)  # 30 days ago
        
        for i in range(500):
            candle = Candle(
                timestamp=old_time + i * 15 * 60 * 1000,
                open=50000.0,
                high=50100.0,
                low=49900.0,
                close=50050.0,
                volume=1000000.0
            )
            manager.candles_15m.append(candle)
            manager.candles_1h.append(candle)
        
        # Measure cleanup time
        start_time = time.time()
        removed_counts = manager.cleanup_old_data(lookback_days=7)
        cleanup_time = time.time() - start_time
        
        # Cleanup should be fast (< 100ms)
        cleanup_time_ms = cleanup_time * 1000
        assert cleanup_time_ms < 100, (
            f"Data cleanup took {cleanup_time_ms:.2f}ms, exceeding 100ms"
        )
        
        # Should have removed old data
        assert sum(removed_counts.values()) > 0
        
        # Buffers should be smaller now
        assert len(manager.candles_15m) < 500
        assert len(manager.candles_1h) < 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
