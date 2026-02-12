"""Machine Learning Predictor for trend direction prediction."""

import os
import pickle
import logging
from typing import List, Optional, Dict
from collections import deque
import numpy as np
from src.config import Config
from src.models import Candle
from src.indicators import IndicatorCalculator


class MLPredictor:
    """Machine learning predictor for trend direction.
    
    Uses a trained model to predict bullish continuation probability
    for the next 4 hours. Tracks accuracy and auto-disables if performance
    falls below minimum threshold.
    """
    
    def __init__(self, config: Config):
        """Initialize ML Predictor.
        
        Args:
            config: Configuration object with ML parameters
        """
        self.config = config
        self.model = None
        self.feature_scaler = None
        self.enabled = True
        self.accuracy_tracker = deque(maxlen=config.ml_accuracy_window)
        self.indicator_calc = IndicatorCalculator()
        self.logger = logging.getLogger(__name__)
        
        # Try to load model if path exists
        if os.path.exists(config.ml_model_path):
            try:
                self.load_model(config.ml_model_path)
                self.logger.info(f"ML model loaded from {config.ml_model_path}")
            except Exception as e:
                self.logger.error(f"Failed to load ML model: {e}")
                self.enabled = False
        else:
            self.logger.warning(f"ML model not found at {config.ml_model_path}. ML predictions disabled.")
            self.enabled = False
    
    def load_model(self, model_path: str) -> None:
        """Load trained model from disk.
        
        Args:
            model_path: Path to the pickled model file
            
        Raises:
            FileNotFoundError: If model file doesn't exist
            Exception: If model loading fails
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            # Model data should contain both model and scaler
            if isinstance(model_data, dict):
                self.model = model_data.get('model')
                self.feature_scaler = model_data.get('scaler')
            else:
                # Backward compatibility: just the model
                self.model = model_data
                self.feature_scaler = None
            
            self.enabled = True
            self.logger.info(f"Model loaded successfully from {model_path}")
            
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            self.model = None
            self.feature_scaler = None
            self.enabled = False
            raise
    
    def save_model(self, model_path: str) -> None:
        """Save trained model to disk.
        
        Args:
            model_path: Path where model should be saved
            
        Raises:
            ValueError: If no model is loaded
        """
        if self.model is None:
            raise ValueError("No model to save")
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            # Save both model and scaler
            model_data = {
                'model': self.model,
                'scaler': self.feature_scaler
            }
            
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            self.logger.info(f"Model saved successfully to {model_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
            raise
    
    def update_accuracy(self, prediction: float, actual_outcome: bool) -> None:
        """Track prediction accuracy.
        
        Args:
            prediction: Predicted probability (0.0-1.0)
            actual_outcome: True if price went up, False if down
        """
        # Convert prediction to binary (>0.5 = bullish)
        predicted_bullish = prediction > 0.5
        
        # Track if prediction was correct
        correct = predicted_bullish == actual_outcome
        self.accuracy_tracker.append(1.0 if correct else 0.0)
        
        # Check if we should disable
        if self.should_disable():
            self.enabled = False
            current_accuracy = self.get_accuracy()
            self.logger.warning(
                f"ML Predictor disabled due to low accuracy: {current_accuracy:.2%} "
                f"(minimum: {self.config.ml_min_accuracy:.2%})"
            )
    
    def should_disable(self) -> bool:
        """Check if accuracy is below threshold.
        
        Returns:
            True if predictor should be disabled, False otherwise
        """
        if len(self.accuracy_tracker) < self.config.ml_accuracy_window:
            # Not enough data yet
            return False
        
        accuracy = self.get_accuracy()
        return accuracy < self.config.ml_min_accuracy
    
    def get_accuracy(self) -> float:
        """Get current rolling accuracy.
        
        Returns:
            Accuracy as float (0.0-1.0), or 0.0 if no predictions yet
        """
        if len(self.accuracy_tracker) == 0:
            return 0.0
        
        return sum(self.accuracy_tracker) / len(self.accuracy_tracker)
    
    def extract_features(self, candles: List[Candle]) -> Optional[np.ndarray]:
        """Extract features for ML prediction.
        
        Extracts 20 features from candle data:
        - Price features (4): returns 1h, 4h, 24h, price vs VWAP
        - Volume features (2): RVOL, volume trend
        - Volatility features (3): ATR, ATR percentile, BB width
        - Momentum features (3): RSI, MACD, squeeze momentum
        - Trend features (2): ADX, trend strength
        - Time features (2): hour of day, day of week
        - Additional features (4): price position, volume position, volatility rank, momentum rank
        
        Args:
            candles: List of Candle objects (needs at least 100 candles)
            
        Returns:
            Numpy array of features, or None if insufficient data
        """
        if len(candles) < 100:
            self.logger.warning("Insufficient candles for feature extraction (need 100+)")
            return None
        
        try:
            features = []
            
            # === Price Features (4) ===
            # 1. 1-hour return (last 4 candles for 15m timeframe)
            if len(candles) >= 5:
                return_1h = (candles[-1].close - candles[-5].close) / candles[-5].close
            else:
                return_1h = 0.0
            features.append(return_1h)
            
            # 2. 4-hour return (last 16 candles for 15m timeframe)
            if len(candles) >= 17:
                return_4h = (candles[-1].close - candles[-17].close) / candles[-17].close
            else:
                return_4h = 0.0
            features.append(return_4h)
            
            # 3. 24-hour return (last 96 candles for 15m timeframe)
            if len(candles) >= 97:
                return_24h = (candles[-1].close - candles[-97].close) / candles[-97].close
            else:
                return_24h = 0.0
            features.append(return_24h)
            
            # 4. Price vs VWAP (using last 96 candles for 24h VWAP)
            if len(candles) >= 96:
                anchor_time = candles[-96].timestamp
                vwap = self.indicator_calc.calculate_vwap(candles, anchor_time)
                price_vs_vwap = (candles[-1].close - vwap) / vwap if vwap > 0 else 0.0
            else:
                price_vs_vwap = 0.0
            features.append(price_vs_vwap)
            
            # === Volume Features (2) ===
            # 5. RVOL
            rvol = self.indicator_calc.calculate_rvol(candles, period=20)
            features.append(rvol)
            
            # 6. Volume trend (volume change over last 10 candles)
            if len(candles) >= 11:
                recent_vol = sum(c.volume for c in candles[-5:]) / 5
                older_vol = sum(c.volume for c in candles[-10:-5]) / 5
                volume_trend = (recent_vol - older_vol) / older_vol if older_vol > 0 else 0.0
            else:
                volume_trend = 0.0
            features.append(volume_trend)
            
            # === Volatility Features (3) ===
            # 7. ATR (normalized by price)
            atr = self.indicator_calc.calculate_atr(candles, period=14)
            atr_normalized = atr / candles[-1].close if candles[-1].close > 0 else 0.0
            features.append(atr_normalized)
            
            # 8. ATR percentile (current ATR vs 30-day ATR distribution)
            if len(candles) >= 96:
                # Calculate ATR for last 30 days (assuming 15m candles)
                atr_values = []
                for i in range(len(candles) - 96, len(candles)):
                    if i >= 14:
                        atr_val = self.indicator_calc.calculate_atr(candles[:i+1], period=14)
                        atr_values.append(atr_val)
                
                if atr_values:
                    atr_percentile = sum(1 for v in atr_values if v < atr) / len(atr_values)
                else:
                    atr_percentile = 0.5
            else:
                atr_percentile = 0.5
            features.append(atr_percentile)
            
            # 9. Bollinger Band width (normalized)
            if len(candles) >= 20:
                closes = [c.close for c in candles[-20:]]
                bb_mean = sum(closes) / len(closes)
                bb_std = (sum((c - bb_mean) ** 2 for c in closes) / len(closes)) ** 0.5
                bb_width = (4 * bb_std) / bb_mean if bb_mean > 0 else 0.0
            else:
                bb_width = 0.0
            features.append(bb_width)
            
            # === Momentum Features (3) ===
            # 10. RSI (14-period)
            rsi = self._calculate_rsi(candles, period=14)
            features.append(rsi / 100.0)  # Normalize to 0-1
            
            # 11. MACD signal (simplified)
            macd_signal = self._calculate_macd_signal(candles)
            features.append(macd_signal)
            
            # 12. Squeeze momentum
            squeeze_data = self.indicator_calc.calculate_squeeze_momentum(candles)
            squeeze_momentum = squeeze_data['value']
            # Normalize squeeze momentum
            squeeze_normalized = np.tanh(squeeze_momentum / candles[-1].close) if candles[-1].close > 0 else 0.0
            features.append(squeeze_normalized)
            
            # === Trend Features (2) ===
            # 13. ADX
            adx = self.indicator_calc.calculate_adx(candles, period=14)
            features.append(adx / 100.0)  # Normalize to 0-1
            
            # 14. Trend strength (price momentum)
            if len(candles) >= 20:
                trend_strength = (candles[-1].close - candles[-20].close) / candles[-20].close
            else:
                trend_strength = 0.0
            features.append(trend_strength)
            
            # === Time Features (2) ===
            # 15. Hour of day (normalized)
            from datetime import datetime
            timestamp_sec = candles[-1].timestamp / 1000
            dt = datetime.fromtimestamp(timestamp_sec)
            hour_normalized = dt.hour / 24.0
            features.append(hour_normalized)
            
            # 16. Day of week (normalized)
            day_normalized = dt.weekday() / 7.0
            features.append(day_normalized)
            
            # === Additional Features (4) ===
            # 17. Price position in recent range
            if len(candles) >= 20:
                recent_high = max(c.high for c in candles[-20:])
                recent_low = min(c.low for c in candles[-20:])
                price_position = (candles[-1].close - recent_low) / (recent_high - recent_low) if recent_high > recent_low else 0.5
            else:
                price_position = 0.5
            features.append(price_position)
            
            # 18. Volume position (current vs recent range)
            if len(candles) >= 20:
                recent_volumes = [c.volume for c in candles[-20:]]
                max_vol = max(recent_volumes)
                min_vol = min(recent_volumes)
                volume_position = (candles[-1].volume - min_vol) / (max_vol - min_vol) if max_vol > min_vol else 0.5
            else:
                volume_position = 0.5
            features.append(volume_position)
            
            # 19. Volatility rank (ATR rank in recent period)
            features.append(atr_percentile)  # Already calculated above
            
            # 20. Momentum rank (RSI-based momentum rank)
            momentum_rank = rsi / 100.0  # Use RSI as momentum rank
            features.append(momentum_rank)
            
            # Convert to numpy array
            feature_array = np.array(features, dtype=np.float32)
            
            # Apply feature scaling if scaler is available
            if self.feature_scaler is not None:
                feature_array = self.feature_scaler.transform(feature_array.reshape(1, -1))[0]
            
            return feature_array
            
        except Exception as e:
            self.logger.error(f"Error extracting features: {e}")
            return None
    
    def _calculate_rsi(self, candles: List[Candle], period: int = 14) -> float:
        """Calculate Relative Strength Index.
        
        Args:
            candles: List of Candle objects
            period: RSI period (default: 14)
            
        Returns:
            RSI value (0-100)
        """
        if len(candles) < period + 1:
            return 50.0  # Neutral
        
        # Calculate price changes
        changes = []
        for i in range(1, len(candles)):
            change = candles[i].close - candles[i-1].close
            changes.append(change)
        
        # Separate gains and losses
        gains = [max(0, c) for c in changes[-period:]]
        losses = [abs(min(0, c)) for c in changes[-period:]]
        
        # Calculate average gain and loss
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd_signal(self, candles: List[Candle]) -> float:
        """Calculate MACD signal (simplified).
        
        Args:
            candles: List of Candle objects
            
        Returns:
            MACD signal value (normalized)
        """
        if len(candles) < 26:
            return 0.0
        
        closes = [c.close for c in candles]
        
        # Calculate EMAs
        ema_12 = self._calculate_ema(closes, 12)
        ema_26 = self._calculate_ema(closes, 26)
        
        # MACD line
        macd = ema_12 - ema_26
        
        # Normalize by price
        macd_normalized = macd / candles[-1].close if candles[-1].close > 0 else 0.0
        
        return macd_normalized
    
    def _calculate_ema(self, values: List[float], period: int) -> float:
        """Calculate Exponential Moving Average.
        
        Args:
            values: List of values
            period: EMA period
            
        Returns:
            EMA value
        """
        if len(values) < period:
            return sum(values) / len(values) if values else 0.0
        
        multiplier = 2.0 / (period + 1)
        ema = sum(values[:period]) / period
        
        for value in values[period:]:
            ema = (value * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def predict(self, candles: List[Candle]) -> float:
        """Predict bullish continuation probability.
        
        Args:
            candles: List of Candle objects
            
        Returns:
            Probability between 0.0 and 1.0, where:
            - 1.0 = high confidence bullish
            - 0.0 = high confidence bearish
            - 0.5 = neutral
            Returns 0.5 if prediction fails or predictor is disabled
        """
        # Check if predictor is enabled
        if not self.enabled:
            self.logger.debug("ML Predictor is disabled, returning neutral prediction")
            return 0.5
        
        # Check if model is loaded
        if self.model is None:
            self.logger.warning("No model loaded, returning neutral prediction")
            return 0.5
        
        try:
            # Extract features
            features = self.extract_features(candles)
            
            if features is None:
                self.logger.warning("Feature extraction failed, returning neutral prediction")
                return 0.5
            
            # Make prediction
            # Reshape for sklearn models (expects 2D array)
            features_2d = features.reshape(1, -1)
            
            # Check if model has predict_proba method (for classifiers)
            if hasattr(self.model, 'predict_proba'):
                # Get probability for positive class (bullish)
                probabilities = self.model.predict_proba(features_2d)
                # probabilities is typically [[prob_class_0, prob_class_1]]
                prediction = float(probabilities[0][1])
            elif hasattr(self.model, 'predict'):
                # For regressors or models without predict_proba
                raw_prediction = self.model.predict(features_2d)[0]
                # Clip to [0, 1] range
                prediction = float(np.clip(raw_prediction, 0.0, 1.0))
            else:
                self.logger.error("Model has no predict or predict_proba method")
                return 0.5
            
            # Ensure prediction is in valid range
            prediction = float(np.clip(prediction, 0.0, 1.0))
            
            self.logger.debug(f"ML prediction: {prediction:.3f}")
            return prediction
            
        except Exception as e:
            self.logger.error(f"Error during prediction: {e}")
            return 0.5
    
    def train_model(self, historical_data: List[Candle]) -> None:
        """Train model on historical data.
        
        This is a placeholder for model training functionality.
        In production, this would:
        1. Extract features from historical data
        2. Generate labels (price direction in 4 hours)
        3. Split into train/validation sets
        4. Train a Random Forest or Gradient Boosting model
        5. Validate on holdout set
        6. Save the trained model
        
        Args:
            historical_data: List of historical candles (90+ days recommended)
            
        Raises:
            NotImplementedError: Training is not implemented in basic version
        """
        raise NotImplementedError(
            "Model training is not implemented in the basic version. "
            "Please train a model externally and load it using load_model()."
        )
