"""Tests for FeatureManager - error isolation and fault tolerance."""

import pytest
from hypothesis import given, strategies as st, settings
from src.feature_manager import FeatureManager, FeatureStatus


class TestFeatureManager:
    """Test suite for FeatureManager."""
    
    def test_register_feature(self):
        """Test feature registration."""
        manager = FeatureManager()
        manager.register_feature("test_feature", enabled=True)
        
        assert manager.is_feature_enabled("test_feature")
        assert "test_feature" in manager.features
    
    def test_execute_feature_success(self):
        """Test successful feature execution."""
        manager = FeatureManager()
        manager.register_feature("test_feature", enabled=True)
        
        def test_func(x, y):
            return x + y
        
        result = manager.execute_feature("test_feature", test_func, 2, 3)
        assert result == 5
        
        status = manager.get_feature_status("test_feature")
        assert status.total_calls == 1
        assert status.successful_calls == 1
    
    def test_execute_feature_error_handling(self):
        """Test feature error handling."""
        manager = FeatureManager(max_errors=2, error_window=300.0)
        manager.register_feature("test_feature", enabled=True)
        
        def failing_func():
            raise ValueError("Test error")
        
        # First error
        result = manager.execute_feature("test_feature", failing_func, default_value="default")
        assert result == "default"
        assert manager.is_feature_enabled("test_feature")
        
        # Second error - should still be enabled
        result = manager.execute_feature("test_feature", failing_func, default_value="default")
        assert result == "default"
        assert not manager.is_feature_enabled("test_feature")  # Disabled after 2 errors
    
    def test_feature_disabled_returns_default(self):
        """Test that disabled features return default value."""
        manager = FeatureManager()
        manager.register_feature("test_feature", enabled=False)
        
        def test_func():
            return "success"
        
        result = manager.execute_feature("test_feature", test_func, default_value="default")
        assert result == "default"
    
    def test_enable_disable_feature(self):
        """Test manual enable/disable of features."""
        manager = FeatureManager()
        manager.register_feature("test_feature", enabled=True)
        
        assert manager.is_feature_enabled("test_feature")
        
        manager.disable_feature("test_feature")
        assert not manager.is_feature_enabled("test_feature")
        
        manager.enable_feature("test_feature")
        assert manager.is_feature_enabled("test_feature")
    
    def test_get_enabled_disabled_features(self):
        """Test getting lists of enabled/disabled features."""
        manager = FeatureManager()
        manager.register_feature("feature1", enabled=True)
        manager.register_feature("feature2", enabled=False)
        manager.register_feature("feature3", enabled=True)
        
        enabled = manager.get_enabled_features()
        disabled = manager.get_disabled_features()
        
        assert "feature1" in enabled
        assert "feature3" in enabled
        assert "feature2" in disabled


class TestFeatureIndependenceProperty:
    """Property-based tests for feature independence.
    
    **Property 26: Feature independence**
    **Validates: Requirements 8.5**
    """
    
    @settings(max_examples=100)
    @given(
        num_features=st.integers(min_value=2, max_value=10),
        failing_feature_index=st.integers(min_value=0, max_value=9)
    )
    def test_feature_independence_property(self, num_features, failing_feature_index):
        """
        Property: For any set of features, when one feature fails repeatedly,
        other features must continue to operate normally.
        
        Feature: advanced-trading-enhancements, Property 26: Feature independence
        Validates: Requirements 8.5
        """
        # Ensure failing_feature_index is within bounds
        failing_feature_index = failing_feature_index % num_features
        
        manager = FeatureManager(max_errors=3, error_window=300.0)
        
        # Register multiple features
        feature_names = [f"feature_{i}" for i in range(num_features)]
        for name in feature_names:
            manager.register_feature(name, enabled=True)
        
        # Define functions for each feature
        def success_func(x):
            return x * 2
        
        def failing_func(x):
            raise ValueError("Simulated failure")
        
        # Execute all features successfully first
        for name in feature_names:
            result = manager.execute_feature(name, success_func, 5, default_value=0)
            assert result == 10
        
        # Now make one feature fail repeatedly (4 times to exceed max_errors=3)
        failing_feature = feature_names[failing_feature_index]
        for _ in range(4):
            result = manager.execute_feature(failing_feature, failing_func, 5, default_value=0)
            assert result == 0  # Should return default value
        
        # Verify the failing feature is disabled
        assert not manager.is_feature_enabled(failing_feature)
        
        # Verify all other features are still enabled and functional
        for i, name in enumerate(feature_names):
            if i != failing_feature_index:
                # Feature should still be enabled
                assert manager.is_feature_enabled(name), \
                    f"Feature {name} should still be enabled after {failing_feature} failed"
                
                # Feature should still execute successfully
                result = manager.execute_feature(name, success_func, 7, default_value=0)
                assert result == 14, \
                    f"Feature {name} should still execute successfully after {failing_feature} failed"
    
    @settings(max_examples=100)
    @given(
        num_features=st.integers(min_value=3, max_value=8),
        num_failing=st.integers(min_value=1, max_value=5)
    )
    def test_multiple_feature_failures_independence(self, num_features, num_failing):
        """
        Property: For any set of features, when multiple features fail,
        the remaining features must continue to operate normally.
        
        Feature: advanced-trading-enhancements, Property 26: Feature independence
        Validates: Requirements 8.5
        """
        # Ensure num_failing doesn't exceed num_features - 1 (keep at least one working)
        num_failing = min(num_failing, num_features - 1)
        
        manager = FeatureManager(max_errors=2, error_window=300.0)
        
        # Register features
        feature_names = [f"feature_{i}" for i in range(num_features)]
        for name in feature_names:
            manager.register_feature(name, enabled=True)
        
        # Define functions
        def success_func():
            return "success"
        
        def failing_func():
            raise RuntimeError("Failure")
        
        # Make first num_failing features fail
        failing_features = feature_names[:num_failing]
        working_features = feature_names[num_failing:]
        
        # Fail the designated features
        for name in failing_features:
            for _ in range(3):  # Exceed max_errors
                manager.execute_feature(name, failing_func, default_value="failed")
        
        # Verify failing features are disabled
        for name in failing_features:
            assert not manager.is_feature_enabled(name)
        
        # Verify working features are still enabled and functional
        for name in working_features:
            assert manager.is_feature_enabled(name), \
                f"Feature {name} should still be enabled"
            
            result = manager.execute_feature(name, success_func, default_value="failed")
            assert result == "success", \
                f"Feature {name} should still execute successfully"
    
    @settings(max_examples=100)
    @given(
        num_features=st.integers(min_value=2, max_value=6),
        error_counts=st.lists(
            st.integers(min_value=0, max_value=5),
            min_size=2,
            max_size=6
        )
    )
    def test_partial_failure_independence(self, num_features, error_counts):
        """
        Property: For any set of features with varying error counts,
        only features exceeding the error threshold should be disabled.
        
        Feature: advanced-trading-enhancements, Property 26: Feature independence
        Validates: Requirements 8.5
        """
        # Ensure error_counts matches num_features
        error_counts = error_counts[:num_features]
        while len(error_counts) < num_features:
            error_counts.append(0)
        
        max_errors = 3
        manager = FeatureManager(max_errors=max_errors, error_window=300.0)
        
        # Register features
        feature_names = [f"feature_{i}" for i in range(num_features)]
        for name in feature_names:
            manager.register_feature(name, enabled=True)
        
        def failing_func():
            raise Exception("Error")
        
        # Apply error counts to each feature
        for name, error_count in zip(feature_names, error_counts):
            for _ in range(error_count):
                manager.execute_feature(name, failing_func, default_value=None)
        
        # Verify each feature's state matches expected
        for name, error_count in zip(feature_names, error_counts):
            if error_count >= max_errors:
                assert not manager.is_feature_enabled(name), \
                    f"Feature {name} with {error_count} errors should be disabled"
            else:
                assert manager.is_feature_enabled(name), \
                    f"Feature {name} with {error_count} errors should still be enabled"


class TestErrorHandling:
    """Unit tests for error handling and graceful degradation.
    
    Tests feature disabling on errors, graceful degradation, and logging completeness.
    Validates: Requirements 8.5, 10.5
    """
    
    def test_feature_disabling_on_repeated_errors(self):
        """Test that features are disabled after repeated errors.
        
        Validates: Requirements 8.5
        """
        manager = FeatureManager(max_errors=3, error_window=300.0)
        manager.register_feature("test_feature", enabled=True)
        
        def failing_func():
            raise RuntimeError("Simulated error")
        
        # Execute 3 times - should disable on 3rd error
        for i in range(3):
            result = manager.execute_feature("test_feature", failing_func, default_value="default")
            assert result == "default"
            
            if i < 2:
                assert manager.is_feature_enabled("test_feature"), \
                    f"Feature should still be enabled after {i+1} errors"
            else:
                assert not manager.is_feature_enabled("test_feature"), \
                    "Feature should be disabled after 3 errors"
        
        # Verify status tracking
        status = manager.get_feature_status("test_feature")
        assert status.error_count == 3
        assert status.total_calls == 3
        assert status.successful_calls == 0
    
    def test_graceful_degradation_with_default_values(self):
        """Test graceful degradation returns default values on errors.
        
        Validates: Requirements 10.5
        """
        manager = FeatureManager(max_errors=5, error_window=300.0)
        manager.register_feature("feature1", enabled=True)
        manager.register_feature("feature2", enabled=True)
        
        def failing_func():
            raise ValueError("Error")
        
        def success_func():
            return {"data": "success"}
        
        # Feature 1 fails, should return default
        result1 = manager.execute_feature("feature1", failing_func, default_value={"data": "fallback"})
        assert result1 == {"data": "fallback"}
        
        # Feature 2 succeeds
        result2 = manager.execute_feature("feature2", success_func, default_value={"data": "fallback"})
        assert result2 == {"data": "success"}
    
    def test_error_window_reset(self):
        """Test that error count resets after error window expires.
        
        Validates: Requirements 8.5
        """
        import time
        
        manager = FeatureManager(max_errors=3, error_window=1.0)  # 1 second window
        manager.register_feature("test_feature", enabled=True)
        
        def failing_func():
            raise Exception("Error")
        
        # Cause 2 errors
        for _ in range(2):
            manager.execute_feature("test_feature", failing_func, default_value=None)
        
        assert manager.is_feature_enabled("test_feature")
        
        # Wait for error window to expire
        time.sleep(1.1)
        
        # Execute successfully - should reset error count
        def success_func():
            return "success"
        
        result = manager.execute_feature("test_feature", success_func, default_value=None)
        assert result == "success"
        
        # Now cause 2 more errors - should not disable (error count was reset)
        for _ in range(2):
            manager.execute_feature("test_feature", failing_func, default_value=None)
        
        assert manager.is_feature_enabled("test_feature")
    
    def test_unregistered_feature_handling(self):
        """Test handling of unregistered features.
        
        Validates: Requirements 10.5
        """
        manager = FeatureManager()
        
        def test_func():
            return "success"
        
        # Should return default value for unregistered feature
        result = manager.execute_feature("nonexistent", test_func, default_value="default")
        assert result == "default"
    
    def test_success_rate_tracking(self):
        """Test that success rate is tracked correctly.
        
        Validates: Requirements 8.5
        """
        manager = FeatureManager(max_errors=10, error_window=300.0)
        manager.register_feature("test_feature", enabled=True)
        
        def success_func():
            return "success"
        
        def failing_func():
            raise Exception("Error")
        
        # Execute 7 successes and 3 failures
        for _ in range(7):
            manager.execute_feature("test_feature", success_func, default_value=None)
        
        for _ in range(3):
            manager.execute_feature("test_feature", failing_func, default_value=None)
        
        status = manager.get_feature_status("test_feature")
        assert status.total_calls == 10
        assert status.successful_calls == 7
        assert status.get_success_rate() == 0.7
    
    def test_manual_enable_after_disable(self):
        """Test that features can be manually re-enabled after being disabled.
        
        Validates: Requirements 8.5
        """
        manager = FeatureManager(max_errors=2, error_window=300.0)
        manager.register_feature("test_feature", enabled=True)
        
        def failing_func():
            raise Exception("Error")
        
        # Disable feature through errors
        for _ in range(3):
            manager.execute_feature("test_feature", failing_func, default_value=None)
        
        assert not manager.is_feature_enabled("test_feature")
        
        # Manually re-enable
        manager.enable_feature("test_feature")
        assert manager.is_feature_enabled("test_feature")
        
        # Verify error count was reset
        status = manager.get_feature_status("test_feature")
        assert status.error_count == 0
    
    def test_logging_completeness(self):
        """Test that errors are logged with complete information.
        
        Validates: Requirements 8.5
        """
        import logging
        from io import StringIO
        
        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.ERROR)
        logger = logging.getLogger("src.feature_manager")
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        try:
            manager = FeatureManager(max_errors=2, error_window=300.0)
            manager.register_feature("test_feature", enabled=True)
            
            def failing_func():
                raise ValueError("Test error message")
            
            # Cause errors to trigger logging
            for _ in range(3):
                manager.execute_feature("test_feature", failing_func, default_value=None)
            
            # Check log output
            log_output = log_stream.getvalue()
            
            # Should contain feature name
            assert "test_feature" in log_output
            
            # Should contain error count
            assert "2" in log_output or "errors" in log_output
            
            # Should contain disabled message
            assert "disabled" in log_output.lower()
        
        finally:
            logger.removeHandler(handler)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
