"""Unit tests for ML Training Pipeline."""

import os
import time
import tempfile
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch

from src.config import Config
from src.models import Candle
from src.data_manager import DataManager
from src.ml_predictor import MLPredictor
from src.ml_training_pipeline import MLTrainingPipeline
from src.ml_model_trainer import MLModelTrainer


# Helper function to generate candles
def generate_candles(count: int, base_price: float = 50000.0, volatility: float = 0.01) -> list:
    """Generate synthetic candle data for testing."""
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


class TestMLTrainingPipeline:
    """Unit tests for ML Training Pipeline."""
    
    def test_collect_historical_data(self):
        """Test data collection for training.
        
        Validates: Requirements 4.7
        """
        config = Config()
        config.ml_training_lookback_days = 90
        config.timeframe_entry = "15m"
        
        # Mock data manager
        data_manager = Mock(spec=DataManager)
        candles = generate_candles(count=500, base_price=50000.0, volatility=0.02)
        data_manager.fetch_historical_data.return_value = candles
        
        # Create pipeline
        pipeline = MLTrainingPipeline(config, data_manager)
        
        # Collect data
        result = pipeline.collect_historical_data(days=90)
        
        # Verify data manager was called correctly
        data_manager.fetch_historical_data.assert_called_once_with(
            days=90,
            timeframe="15m",
            use_cache=False
        )
        
        # Verify result
        assert len(result) == 500
        assert result == candles
    
    def test_collect_historical_data_insufficient(self):
        """Test data collection with insufficient data.
        
        Validates: Requirements 4.7
        """
        config = Config()
        data_manager = Mock(spec=DataManager)
        
        # Return insufficient data
        candles = generate_candles(count=50, base_price=50000.0, volatility=0.02)
        data_manager.fetch_historical_data.return_value = candles
        
        pipeline = MLTrainingPipeline(config, data_manager)
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Insufficient historical data"):
            pipeline.collect_historical_data(days=90)
    
    def test_generate_labels(self):
        """Test label generation for training.
        
        Validates: Requirements 4.7
        """
        config = Config()
        config.ml_prediction_horizon_hours = 4
        config.timeframe_entry = "15m"
        
        data_manager = Mock(spec=DataManager)
        pipeline = MLTrainingPipeline(config, data_manager)
        
        # Generate candles with known price pattern
        candles = []
        timestamp = int(time.time() * 1000)
        
        # Create 100 candles with alternating up/down pattern
        for i in range(100):
            price = 50000.0 + (i * 100)  # Increasing price
            candle = Candle(
                timestamp=timestamp,
                open=price,
                high=price + 50,
                low=price - 50,
                close=price,
                volume=1000.0
            )
            candles.append(candle)
            timestamp += 900000  # 15 minutes
        
        # Generate labels
        labels = pipeline.generate_labels(candles)
        
        # For 15m candles, 4 hours = 16 candles ahead
        # So we should have len(candles) - 16 labels
        expected_label_count = len(candles) - 16
        assert len(labels) == expected_label_count
        
        # Since price is increasing, most labels should be 1 (bullish)
        bullish_count = np.sum(labels)
        assert bullish_count > len(labels) * 0.8  # At least 80% bullish
    
    def test_generate_labels_decreasing_price(self):
        """Test label generation with decreasing price.
        
        Validates: Requirements 4.7
        """
        config = Config()
        config.ml_prediction_horizon_hours = 4
        config.timeframe_entry = "15m"
        
        data_manager = Mock(spec=DataManager)
        pipeline = MLTrainingPipeline(config, data_manager)
        
        # Generate candles with decreasing price
        candles = []
        timestamp = int(time.time() * 1000)
        
        for i in range(100):
            price = 50000.0 - (i * 100)  # Decreasing price
            candle = Candle(
                timestamp=timestamp,
                open=price,
                high=price + 50,
                low=price - 50,
                close=price,
                volume=1000.0
            )
            candles.append(candle)
            timestamp += 900000  # 15 minutes
        
        # Generate labels
        labels = pipeline.generate_labels(candles)
        
        # Since price is decreasing, most labels should be 0 (bearish)
        bearish_count = len(labels) - np.sum(labels)
        assert bearish_count > len(labels) * 0.8  # At least 80% bearish
    
    def test_split_train_validation(self):
        """Test train/validation split.
        
        Validates: Requirements 4.7
        """
        config = Config()
        data_manager = Mock(spec=DataManager)
        pipeline = MLTrainingPipeline(config, data_manager)
        
        # Create synthetic features and labels
        n_samples = 1000
        n_features = 20
        features = np.random.randn(n_samples, n_features).astype(np.float32)
        labels = np.random.randint(0, 2, size=n_samples).astype(np.int32)
        
        # Split data
        X_train, X_val, y_train, y_val = pipeline.split_train_validation(features, labels)
        
        # Verify split sizes (80/20 split)
        assert len(X_train) == int(n_samples * 0.8)
        assert len(X_val) == int(n_samples * 0.2)
        assert len(y_train) == int(n_samples * 0.8)
        assert len(y_val) == int(n_samples * 0.2)
        
        # Verify no data leakage (train and val should be disjoint)
        assert len(X_train) + len(X_val) == n_samples
        assert len(y_train) + len(y_val) == n_samples
    
    def test_prepare_training_data(self):
        """Test complete training data preparation.
        
        Validates: Requirements 4.7
        """
        config = Config()
        config.ml_training_lookback_days = 90
        config.ml_prediction_horizon_hours = 4
        config.timeframe_entry = "15m"
        
        # Mock data manager
        data_manager = Mock(spec=DataManager)
        candles = generate_candles(count=500, base_price=50000.0, volatility=0.02)
        data_manager.fetch_historical_data.return_value = candles
        
        # Create pipeline
        pipeline = MLTrainingPipeline(config, data_manager)
        
        # Create ML predictor
        ml_predictor = MLPredictor(config)
        
        # Prepare training data
        X_train, X_val, y_train, y_val, scaler = pipeline.prepare_training_data(ml_predictor)
        
        # Verify shapes
        assert X_train.shape[1] == config.ml_feature_count  # 20 features
        assert X_val.shape[1] == config.ml_feature_count
        assert len(X_train) == len(y_train)
        assert len(X_val) == len(y_val)
        
        # Verify scaler was fitted
        assert scaler is not None
        assert hasattr(scaler, 'mean_')
        assert hasattr(scaler, 'scale_')
        
        # Verify labels are binary
        assert np.all((y_train == 0) | (y_train == 1))
        assert np.all((y_val == 0) | (y_val == 1))
    
    def test_get_timeframe_minutes(self):
        """Test timeframe to minutes conversion.
        
        Validates: Requirements 4.7
        """
        config = Config()
        data_manager = Mock(spec=DataManager)
        pipeline = MLTrainingPipeline(config, data_manager)
        
        # Test various timeframes
        assert pipeline._get_timeframe_minutes("1m") == 1
        assert pipeline._get_timeframe_minutes("5m") == 5
        assert pipeline._get_timeframe_minutes("15m") == 15
        assert pipeline._get_timeframe_minutes("1h") == 60
        assert pipeline._get_timeframe_minutes("4h") == 240
        
        # Test invalid timeframe
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            pipeline._get_timeframe_minutes("invalid")


class TestMLModelTrainer:
    """Unit tests for ML Model Trainer."""
    
    def test_train_random_forest(self):
        """Test Random Forest training.
        
        Validates: Requirements 4.7
        """
        config = Config()
        trainer = MLModelTrainer(config)
        
        # Create synthetic training data
        n_samples = 1000
        n_features = 20
        X_train = np.random.randn(n_samples, n_features).astype(np.float32)
        y_train = np.random.randint(0, 2, size=n_samples).astype(np.int32)
        
        # Create validation data
        n_val = 200
        X_val = np.random.randn(n_val, n_features).astype(np.float32)
        y_val = np.random.randint(0, 2, size=n_val).astype(np.int32)
        
        # Train model
        model, metrics = trainer.train_random_forest(X_train, y_train, X_val, y_val)
        
        # Verify model was trained
        assert model is not None
        assert hasattr(model, 'predict')
        assert hasattr(model, 'predict_proba')
        
        # Verify metrics
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 0.0 <= metrics['accuracy'] <= 1.0
    
    def test_train_gradient_boosting(self):
        """Test Gradient Boosting training.
        
        Validates: Requirements 4.7
        """
        config = Config()
        trainer = MLModelTrainer(config)
        
        # Create synthetic training data
        n_samples = 1000
        n_features = 20
        X_train = np.random.randn(n_samples, n_features).astype(np.float32)
        y_train = np.random.randint(0, 2, size=n_samples).astype(np.int32)
        
        # Create validation data
        n_val = 200
        X_val = np.random.randn(n_val, n_features).astype(np.float32)
        y_val = np.random.randint(0, 2, size=n_val).astype(np.int32)
        
        # Train model
        model, metrics = trainer.train_gradient_boosting(X_train, y_train, X_val, y_val)
        
        # Verify model was trained
        assert model is not None
        assert hasattr(model, 'predict')
        assert hasattr(model, 'predict_proba')
        
        # Verify metrics
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 0.0 <= metrics['accuracy'] <= 1.0
    
    def test_save_model(self):
        """Test model saving.
        
        Validates: Requirements 4.7
        """
        config = Config()
        trainer = MLModelTrainer(config)
        
        # Create a simple trained model
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        X_dummy = np.random.randn(100, 20)
        y_dummy = np.random.randint(0, 2, size=100)
        model.fit(X_dummy, y_dummy)
        
        scaler = StandardScaler()
        scaler.fit(X_dummy)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
            temp_path = f.name
        
        try:
            # Save model
            trainer.save_model(model, scaler, temp_path)
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
            # Verify file is not empty
            assert os.path.getsize(temp_path) > 0
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_train_and_save_model_random_forest(self):
        """Test complete train and save workflow for Random Forest.
        
        Validates: Requirements 4.7
        """
        config = Config()
        trainer = MLModelTrainer(config)
        
        # Create synthetic data
        n_samples = 1000
        n_features = 20
        X_train = np.random.randn(n_samples, n_features).astype(np.float32)
        y_train = np.random.randint(0, 2, size=n_samples).astype(np.int32)
        
        n_val = 200
        X_val = np.random.randn(n_val, n_features).astype(np.float32)
        y_val = np.random.randint(0, 2, size=n_val).astype(np.int32)
        
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        scaler.fit(X_train)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
            temp_path = f.name
        
        try:
            # Train and save
            model, metrics = trainer.train_and_save_model(
                X_train, X_val, y_train, y_val,
                scaler,
                model_type="random_forest",
                model_path=temp_path
            )
            
            # Verify model was trained
            assert model is not None
            
            # Verify metrics
            assert 'accuracy' in metrics
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_train_and_save_model_gradient_boosting(self):
        """Test complete train and save workflow for Gradient Boosting.
        
        Validates: Requirements 4.7
        """
        config = Config()
        trainer = MLModelTrainer(config)
        
        # Create synthetic data
        n_samples = 1000
        n_features = 20
        X_train = np.random.randn(n_samples, n_features).astype(np.float32)
        y_train = np.random.randint(0, 2, size=n_samples).astype(np.int32)
        
        n_val = 200
        X_val = np.random.randn(n_val, n_features).astype(np.float32)
        y_val = np.random.randint(0, 2, size=n_val).astype(np.int32)
        
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        scaler.fit(X_train)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
            temp_path = f.name
        
        try:
            # Train and save
            model, metrics = trainer.train_and_save_model(
                X_train, X_val, y_train, y_val,
                scaler,
                model_type="gradient_boosting",
                model_path=temp_path
            )
            
            # Verify model was trained
            assert model is not None
            
            # Verify metrics
            assert 'accuracy' in metrics
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_train_and_save_model_invalid_type(self):
        """Test train and save with invalid model type.
        
        Validates: Requirements 4.7
        """
        config = Config()
        trainer = MLModelTrainer(config)
        
        # Create dummy data
        X_train = np.random.randn(100, 20)
        X_val = np.random.randn(20, 20)
        y_train = np.random.randint(0, 2, size=100)
        y_val = np.random.randint(0, 2, size=20)
        
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        
        # Should raise ValueError for invalid model type
        with pytest.raises(ValueError, match="Unsupported model_type"):
            trainer.train_and_save_model(
                X_train, X_val, y_train, y_val,
                scaler,
                model_type="invalid_model"
            )
    
    def test_model_loading_after_save(self):
        """Test that saved model can be loaded and used.
        
        Validates: Requirements 4.7
        """
        config = Config()
        trainer = MLModelTrainer(config)
        
        # Create and train a simple model
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        X_train = np.random.randn(100, 20)
        y_train = np.random.randint(0, 2, size=100)
        model.fit(X_train, y_train)
        
        scaler = StandardScaler()
        scaler.fit(X_train)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
            temp_path = f.name
        
        try:
            # Save model
            trainer.save_model(model, scaler, temp_path)
            
            # Load model using MLPredictor
            config.ml_model_path = temp_path
            ml_predictor = MLPredictor(config)
            
            # Verify model was loaded
            assert ml_predictor.model is not None
            assert ml_predictor.feature_scaler is not None
            assert ml_predictor.enabled
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
