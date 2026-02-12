"""ML Model Training Pipeline for trend prediction."""

import logging
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from src.config import Config
from src.models import Candle
from src.data_manager import DataManager
from src.ml_predictor import MLPredictor


class MLTrainingPipeline:
    """Pipeline for training ML models for trend prediction.
    
    Handles:
    - Collecting historical data (90 days)
    - Generating training labels (price direction in 4 hours)
    - Splitting into train/validation sets
    - Training and validating models
    """
    
    def __init__(self, config: Config, data_manager: DataManager):
        """Initialize training pipeline.
        
        Args:
            config: Configuration object
            data_manager: DataManager for fetching historical data
        """
        self.config = config
        self.data_manager = data_manager
        self.logger = logging.getLogger(__name__)
        
        # Training parameters
        self.lookback_days = config.ml_training_lookback_days
        self.prediction_horizon_hours = config.ml_prediction_horizon_hours
        self.validation_split = 0.2  # 20% for validation
        self.random_state = 42
    
    def collect_historical_data(self, days: Optional[int] = None) -> List[Candle]:
        """Collect historical data for training.
        
        Args:
            days: Number of days to collect (default: from config)
            
        Returns:
            List of Candle objects
            
        Raises:
            ValueError: If insufficient data is available
        """
        if days is None:
            days = self.lookback_days
        
        self.logger.info(f"Collecting {days} days of historical data for training")
        
        try:
            # Fetch historical data using 15m timeframe (primary timeframe)
            candles = self.data_manager.fetch_historical_data(
                days=days,
                timeframe=self.config.timeframe_entry,
                use_cache=False  # Don't use cache for training
            )
            
            if len(candles) < 100:
                raise ValueError(
                    f"Insufficient historical data: got {len(candles)} candles, "
                    f"need at least 100 for feature extraction"
                )
            
            self.logger.info(f"Collected {len(candles)} candles from {days} days")
            return candles
            
        except Exception as e:
            self.logger.error(f"Failed to collect historical data: {e}")
            raise
    
    def generate_labels(self, candles: List[Candle]) -> np.ndarray:
        """Generate training labels (price direction in N hours).
        
        For each candle, the label is 1 if the price goes up in the next
        prediction_horizon_hours, and 0 if it goes down.
        
        Args:
            candles: List of Candle objects
            
        Returns:
            Numpy array of labels (0 or 1)
        """
        self.logger.info(f"Generating labels with {self.prediction_horizon_hours}h horizon")
        
        # Calculate how many candles ahead to look
        # For 15m candles: 4 hours = 16 candles
        timeframe_minutes = self._get_timeframe_minutes(self.config.timeframe_entry)
        candles_ahead = int((self.prediction_horizon_hours * 60) / timeframe_minutes)
        
        self.logger.debug(
            f"Looking {candles_ahead} candles ahead "
            f"({self.prediction_horizon_hours}h at {timeframe_minutes}m intervals)"
        )
        
        labels = []
        
        # Generate labels for all candles except the last N
        for i in range(len(candles) - candles_ahead):
            current_price = candles[i].close
            future_price = candles[i + candles_ahead].close
            
            # Label is 1 if price goes up, 0 if it goes down
            label = 1 if future_price > current_price else 0
            labels.append(label)
        
        # Convert to numpy array
        labels_array = np.array(labels, dtype=np.int32)
        
        # Log label distribution
        bullish_count = np.sum(labels_array)
        bearish_count = len(labels_array) - bullish_count
        bullish_pct = (bullish_count / len(labels_array)) * 100 if len(labels_array) > 0 else 0
        
        self.logger.info(
            f"Generated {len(labels_array)} labels: "
            f"{bullish_count} bullish ({bullish_pct:.1f}%), "
            f"{bearish_count} bearish ({100-bullish_pct:.1f}%)"
        )
        
        return labels_array
    
    def extract_features_for_training(
        self,
        candles: List[Candle],
        ml_predictor: MLPredictor,
        sample_every: int = 4
    ) -> np.ndarray:
        """Extract features for all training samples.
        
        Args:
            candles: List of Candle objects
            ml_predictor: MLPredictor instance for feature extraction
            sample_every: Sample every Nth candle to speed up training (default: 4 = 1 hour intervals)
            
        Returns:
            Numpy array of features (n_samples, n_features)
        """
        self.logger.info("Extracting features for training")
        
        # Calculate how many candles ahead we're predicting
        timeframe_minutes = self._get_timeframe_minutes(self.config.timeframe_entry)
        candles_ahead = int((self.prediction_horizon_hours * 60) / timeframe_minutes)
        
        # We need at least 100 candles for feature extraction
        min_candles_for_features = 100
        
        features_list = []
        valid_indices = []
        
        # Calculate indices to sample
        all_indices = range(min_candles_for_features, len(candles) - candles_ahead)
        sampled_indices = list(all_indices)[::sample_every]
        
        total_samples = len(sampled_indices)
        self.logger.info(
            f"Processing {total_samples} samples (sampling every {sample_every} candles = "
            f"{sample_every * timeframe_minutes} minutes)..."
        )
        
        # Extract features for each valid sample with progress logging
        for idx, i in enumerate(sampled_indices):
            # Log progress every 10%
            if idx % max(1, total_samples // 10) == 0:
                progress_pct = (idx / total_samples) * 100
                self.logger.info(f"Progress: {progress_pct:.1f}% ({idx}/{total_samples})")
            
            # Get candles up to this point
            candles_slice = candles[:i+1]
            
            # Extract features
            features = ml_predictor.extract_features(candles_slice)
            
            if features is not None:
                features_list.append(features)
                valid_indices.append(i)
            else:
                self.logger.warning(f"Failed to extract features at index {i}")
        
        if len(features_list) == 0:
            raise ValueError("Failed to extract any valid features")
        
        # Convert to numpy array
        features_array = np.array(features_list, dtype=np.float32)
        
        self.logger.info(
            f"Extracted features for {len(features_array)} samples "
            f"(shape: {features_array.shape})"
        )
        
        return features_array, valid_indices
    
    def split_train_validation(
        self,
        features: np.ndarray,
        labels: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Split data into training and validation sets.
        
        Args:
            features: Feature array (n_samples, n_features)
            labels: Label array (n_samples,)
            
        Returns:
            Tuple of (X_train, X_val, y_train, y_val)
        """
        self.logger.info(
            f"Splitting data: {len(features)} samples, "
            f"validation_split={self.validation_split}"
        )
        
        # Use sklearn's train_test_split for stratified splitting
        X_train, X_val, y_train, y_val = train_test_split(
            features,
            labels,
            test_size=self.validation_split,
            random_state=self.random_state,
            stratify=labels  # Maintain class distribution
        )
        
        self.logger.info(
            f"Training set: {len(X_train)} samples "
            f"({np.sum(y_train)} bullish, {len(y_train) - np.sum(y_train)} bearish)"
        )
        self.logger.info(
            f"Validation set: {len(X_val)} samples "
            f"({np.sum(y_val)} bullish, {len(y_val) - np.sum(y_val)} bearish)"
        )
        
        return X_train, X_val, y_train, y_val
    
    def prepare_training_data(
        self,
        ml_predictor: MLPredictor,
        days: Optional[int] = None,
        sample_every: int = 4
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
        """Prepare complete training dataset.
        
        This is the main method that orchestrates the entire data preparation:
        1. Collect historical data
        2. Extract features
        3. Generate labels
        4. Align features and labels
        5. Scale features
        6. Split into train/validation sets
        
        Args:
            ml_predictor: MLPredictor instance for feature extraction
            days: Number of days to collect (default: from config)
            sample_every: Sample every Nth candle to speed up training (default: 4 = 1 hour)
            
        Returns:
            Tuple of (X_train, X_val, y_train, y_val, scaler)
        """
        self.logger.info("Starting training data preparation")
        
        # Step 1: Collect historical data
        candles = self.collect_historical_data(days)
        
        # Step 2: Extract features
        features, valid_indices = self.extract_features_for_training(
            candles, ml_predictor, sample_every=sample_every
        )
        
        # Step 3: Generate labels for all candles
        all_labels = self.generate_labels(candles)
        
        # Step 4: Align labels with valid feature indices
        # valid_indices tells us which candles have valid features
        # We need to get the corresponding labels
        min_candles_for_features = 100
        
        # Adjust valid_indices to match label indices
        # Labels start from index 0, but features start from index min_candles_for_features
        label_indices = [idx - min_candles_for_features for idx in valid_indices]
        
        # Filter labels to match features
        labels = all_labels[label_indices]
        
        if len(features) != len(labels):
            raise ValueError(
                f"Feature-label mismatch: {len(features)} features, {len(labels)} labels"
            )
        
        self.logger.info(f"Aligned {len(features)} feature-label pairs")
        
        # Step 5: Scale features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        self.logger.info("Features scaled using StandardScaler")
        
        # Step 6: Split into train/validation sets
        X_train, X_val, y_train, y_val = self.split_train_validation(
            features_scaled,
            labels
        )
        
        self.logger.info("Training data preparation complete")
        
        return X_train, X_val, y_train, y_val, scaler
    
    def _get_timeframe_minutes(self, timeframe: str) -> int:
        """Get the duration of a timeframe in minutes.
        
        Args:
            timeframe: Timeframe string (e.g., "15m", "1h")
            
        Returns:
            Duration in minutes
        """
        timeframe_minutes = {
            "1m": 1,
            "3m": 3,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "2h": 120,
            "4h": 240,
            "6h": 360,
            "8h": 480,
            "12h": 720,
            "1d": 1440,
        }
        
        if timeframe not in timeframe_minutes:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        return timeframe_minutes[timeframe]
