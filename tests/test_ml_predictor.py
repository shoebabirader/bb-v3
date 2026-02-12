"""Property-based and unit tests for ML Predictor."""

import os
import time
import pickle
import tempfile
import pytest
import numpy as np
from hypothesis import given, strategies as st, settings
from src.config import Config
from src.models import Candle
from src.ml_predictor import MLPredictor


# Helper function to generate candles
def generate_candles(count: int, base_price: float = 50000.0, volatility: float = 0.01) -> list:
    """Generate synthetic candle data for testing.
    
    Args:
        count: Number of candles to generate
        base_price: Base price for candles
        volatility: Price volatility factor
        
    Returns:
        List of Candle objects
    """
    import random
    candles = []
    current_price = base_price
    timestamp = int(time.time() * 1000) - (count * 900000)  # Start count * 15min ago
    
    for i in range(count):
        # Add some random price movement
        price_change = current_price * volatility * (random.random() - 0.5) * 2
        current_price += price_change
        
        high = current_price * (1 + abs(random.random() * volatility))
        low = current_price * (1 - abs(random.random() * volatility))
        open_price = current_price + (random.random() - 0.5) * volatility * current_price
        close_price = current_price + (random.random() - 0.5) * volatility * current_price
        volume = random.uniform(100, 1000)
        
        candle = Candle(
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=volume
        )
        candles.append(candle)
        timestamp += 900000  # 15 minutes
    
    return candles


# Mock model for testing
class MockModel:
    """Mock ML model for testing."""
    
    def __init__(self, return_value: float = 0.7):
        self.return_value = return_value
    
    def predict_proba(self, X):
        """Mock predict_proba method."""
        # Return probabilities for [class_0, class_1]
        return np.array([[1 - self.return_value, self.return_value]])
    
    def predict(self, X):
        """Mock predict method."""
        return np.array([self.return_value])


# Feature: advanced-trading-enhancements, Property 11: Prediction range invariant
@given(
    candle_count=st.integers(min_value=100, max_value=500),
    volatility=st.floats(min_value=0.001, max_value=0.1),
    mock_prediction=st.floats(min_value=-1.0, max_value=2.0)
)
@settings(max_examples=100)
def test_prediction_range_invariant(candle_count, volatility, mock_prediction):
    """For any input features, the ML prediction output must be between 0.0 and 1.0 inclusive.
    
    Property 11: Prediction range invariant
    Validates: Requirements 4.3
    """
    # Create config
    config = Config()
    config.ml_model_path = "test_model.pkl"
    
    # Create predictor
    predictor = MLPredictor(config)
    
    # Set up mock model with potentially out-of-range prediction
    predictor.model = MockModel(return_value=mock_prediction)
    predictor.enabled = True
    
    # Generate candles
    candles = generate_candles(count=candle_count, base_price=50000.0, volatility=volatility)
    
    # Make prediction
    prediction = predictor.predict(candles)
    
    # Verify prediction is in valid range
    assert 0.0 <= prediction <= 1.0, (
        f"Prediction {prediction} outside valid range [0.0, 1.0]"
    )


# Feature: advanced-trading-enhancements, Property 14: Accuracy-based disabling
@given(
    accuracy_values=st.lists(
        st.booleans(),
        min_size=100,
        max_size=100
    )
)
@settings(max_examples=100)
def test_accuracy_based_disabling(accuracy_values):
    """For any sequence of predictions where rolling 100-prediction accuracy falls below 55%, 
    the ML predictor must be disabled.
    
    Property 14: Accuracy-based disabling
    Validates: Requirements 4.8
    """
    # Create config
    config = Config()
    config.ml_min_accuracy = 0.55
    config.ml_accuracy_window = 100
    config.ml_model_path = "test_model.pkl"
    
    # Create predictor
    predictor = MLPredictor(config)
    predictor.model = MockModel()
    predictor.enabled = True
    
    # Calculate expected accuracy
    correct_count = sum(1 for v in accuracy_values if v)
    expected_accuracy = correct_count / len(accuracy_values)
    
    # Feed accuracy values
    for outcome in accuracy_values:
        predictor.update_accuracy(0.7, outcome)
    
    # Check if predictor should be disabled
    should_be_disabled = expected_accuracy < config.ml_min_accuracy
    
    # Verify predictor state matches expectation
    assert predictor.enabled != should_be_disabled, (
        f"Predictor enabled={predictor.enabled}, but accuracy={expected_accuracy:.2%}, "
        f"threshold={config.ml_min_accuracy:.2%}"
    )
    
    # Verify should_disable() method returns correct value
    assert predictor.should_disable() == should_be_disabled


class TestMLPredictorUnit:
    """Unit tests for ML Predictor edge cases."""
    
    def test_feature_extraction_with_sufficient_data(self):
        """Test feature extraction with sufficient candle data.
        
        Validates: Requirements 4.2
        """
        config = Config()
        predictor = MLPredictor(config)
        
        # Generate sufficient candles
        candles = generate_candles(count=150, base_price=50000.0, volatility=0.02)
        
        # Extract features
        features = predictor.extract_features(candles)
        
        # Should return valid features
        assert features is not None
        assert len(features) == config.ml_feature_count
        assert all(np.isfinite(f) for f in features)
    
    def test_feature_extraction_with_insufficient_data(self):
        """Test feature extraction with insufficient candle data.
        
        Validates: Requirements 4.2
        """
        config = Config()
        predictor = MLPredictor(config)
        
        # Generate insufficient candles
        candles = generate_candles(count=50, base_price=50000.0, volatility=0.02)
        
        # Extract features
        features = predictor.extract_features(candles)
        
        # Should return None
        assert features is None
    
    def test_prediction_with_mock_model(self):
        """Test prediction with a mock model.
        
        Validates: Requirements 4.1, 4.3
        """
        config = Config()
        config.ml_model_path = "test_model.pkl"
        predictor = MLPredictor(config)
        
        # Set up mock model
        predictor.model = MockModel(return_value=0.75)
        predictor.enabled = True
        
        # Generate candles
        candles = generate_candles(count=150, base_price=50000.0, volatility=0.02)
        
        # Make prediction
        prediction = predictor.predict(candles)
        
        # Should return the mock value
        assert 0.0 <= prediction <= 1.0
        assert abs(prediction - 0.75) < 0.01
    
    def test_prediction_when_disabled(self):
        """Test that prediction returns neutral when predictor is disabled.
        
        Validates: Requirements 4.1, 4.3
        """
        config = Config()
        predictor = MLPredictor(config)
        predictor.enabled = False
        
        # Generate candles
        candles = generate_candles(count=150, base_price=50000.0, volatility=0.02)
        
        # Make prediction
        prediction = predictor.predict(candles)
        
        # Should return neutral (0.5)
        assert prediction == 0.5
    
    def test_prediction_without_model(self):
        """Test that prediction returns neutral when no model is loaded.
        
        Validates: Requirements 4.1, 4.3
        """
        config = Config()
        predictor = MLPredictor(config)
        predictor.model = None
        predictor.enabled = True
        
        # Generate candles
        candles = generate_candles(count=150, base_price=50000.0, volatility=0.02)
        
        # Make prediction
        prediction = predictor.predict(candles)
        
        # Should return neutral (0.5)
        assert prediction == 0.5
    
    def test_prediction_with_insufficient_data(self):
        """Test that prediction returns neutral with insufficient data.
        
        Validates: Requirements 4.1, 4.3
        """
        config = Config()
        config.ml_model_path = "test_model.pkl"
        predictor = MLPredictor(config)
        predictor.model = MockModel()
        predictor.enabled = True
        
        # Generate insufficient candles
        candles = generate_candles(count=50, base_price=50000.0, volatility=0.02)
        
        # Make prediction
        prediction = predictor.predict(candles)
        
        # Should return neutral (0.5)
        assert prediction == 0.5
    
    def test_accuracy_tracking(self):
        """Test accuracy tracking functionality.
        
        Validates: Requirements 4.8
        """
        config = Config()
        config.ml_accuracy_window = 10
        predictor = MLPredictor(config)
        
        # Add some correct predictions
        for _ in range(7):
            predictor.update_accuracy(0.7, True)
        
        # Add some incorrect predictions
        for _ in range(3):
            predictor.update_accuracy(0.7, False)
        
        # Check accuracy
        accuracy = predictor.get_accuracy()
        assert abs(accuracy - 0.7) < 0.01
    
    def test_accuracy_window_limit(self):
        """Test that accuracy tracker respects window limit.
        
        Validates: Requirements 4.8
        """
        config = Config()
        config.ml_accuracy_window = 5
        predictor = MLPredictor(config)
        
        # Add more predictions than window size
        for i in range(10):
            predictor.update_accuracy(0.7, i < 5)
        
        # Should only track last 5
        assert len(predictor.accuracy_tracker) == 5
    
    def test_should_disable_with_low_accuracy(self):
        """Test that predictor should disable with low accuracy.
        
        Validates: Requirements 4.8
        """
        config = Config()
        config.ml_min_accuracy = 0.55
        config.ml_accuracy_window = 10
        predictor = MLPredictor(config)
        
        # Add predictions with 40% accuracy (below threshold)
        for i in range(10):
            predictor.update_accuracy(0.7, i < 4)
        
        # Should indicate it should be disabled
        assert predictor.should_disable()
    
    def test_should_not_disable_with_high_accuracy(self):
        """Test that predictor should not disable with high accuracy.
        
        Validates: Requirements 4.8
        """
        config = Config()
        config.ml_min_accuracy = 0.55
        config.ml_accuracy_window = 10
        predictor = MLPredictor(config)
        
        # Add predictions with 70% accuracy (above threshold)
        for i in range(10):
            predictor.update_accuracy(0.7, i < 7)
        
        # Should not indicate it should be disabled
        assert not predictor.should_disable()
    
    def test_should_not_disable_with_insufficient_data(self):
        """Test that predictor should not disable with insufficient accuracy data.
        
        Validates: Requirements 4.8
        """
        config = Config()
        config.ml_min_accuracy = 0.55
        config.ml_accuracy_window = 100
        predictor = MLPredictor(config)
        
        # Add only a few predictions
        for i in range(10):
            predictor.update_accuracy(0.7, i < 2)
        
        # Should not disable yet (not enough data)
        assert not predictor.should_disable()
    
    def test_model_save_and_load(self):
        """Test model saving and loading.
        
        Validates: Requirements 4.1
        """
        config = Config()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
            temp_path = f.name
        
        try:
            # Create predictor and set up mock model
            predictor1 = MLPredictor(config)
            predictor1.model = MockModel(return_value=0.8)
            predictor1.feature_scaler = None
            
            # Save model
            predictor1.save_model(temp_path)
            
            # Create new predictor and load model
            config.ml_model_path = temp_path
            predictor2 = MLPredictor(config)
            
            # Should have loaded the model
            assert predictor2.model is not None
            assert predictor2.enabled
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_model_load_nonexistent_file(self):
        """Test loading model from nonexistent file.
        
        Validates: Requirements 4.1
        """
        config = Config()
        config.ml_model_path = "nonexistent_model.pkl"
        
        # Create predictor (should handle missing file gracefully)
        predictor = MLPredictor(config)
        
        # Should be disabled
        assert not predictor.enabled
        assert predictor.model is None
    
    def test_train_model_not_implemented(self):
        """Test that train_model raises NotImplementedError.
        
        Validates: Requirements 4.7
        """
        config = Config()
        predictor = MLPredictor(config)
        
        # Generate candles
        candles = generate_candles(count=1000, base_price=50000.0, volatility=0.02)
        
        # Should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            predictor.train_model(candles)
    
    def test_feature_extraction_handles_errors(self):
        """Test that feature extraction handles errors gracefully.
        
        Validates: Requirements 4.2
        """
        config = Config()
        predictor = MLPredictor(config)
        
        # Create invalid candles (empty list)
        candles = []
        
        # Should return None
        features = predictor.extract_features(candles)
        assert features is None
    
    def test_prediction_handles_errors(self):
        """Test that prediction handles errors gracefully.
        
        Validates: Requirements 4.1, 4.3
        """
        config = Config()
        predictor = MLPredictor(config)
        
        # Set up model that will raise an error
        class ErrorModel:
            def predict_proba(self, X):
                raise ValueError("Test error")
        
        predictor.model = ErrorModel()
        predictor.enabled = True
        
        # Generate candles
        candles = generate_candles(count=150, base_price=50000.0, volatility=0.02)
        
        # Should return neutral (0.5) on error
        prediction = predictor.predict(candles)
        assert prediction == 0.5
    
    def test_get_accuracy_with_no_data(self):
        """Test get_accuracy with no tracking data.
        
        Validates: Requirements 4.8
        """
        config = Config()
        predictor = MLPredictor(config)
        
        # Should return 0.0
        accuracy = predictor.get_accuracy()
        assert accuracy == 0.0
    
    def test_update_accuracy_converts_prediction_to_binary(self):
        """Test that update_accuracy correctly converts predictions to binary.
        
        Validates: Requirements 4.8
        """
        config = Config()
        config.ml_accuracy_window = 10
        predictor = MLPredictor(config)
        
        # Test with prediction > 0.5 (bullish)
        predictor.update_accuracy(0.7, True)  # Correct
        predictor.update_accuracy(0.7, False)  # Incorrect
        
        # Test with prediction < 0.5 (bearish)
        predictor.update_accuracy(0.3, False)  # Correct
        predictor.update_accuracy(0.3, True)  # Incorrect
        
        # Should have 50% accuracy
        accuracy = predictor.get_accuracy()
        assert abs(accuracy - 0.5) < 0.01
