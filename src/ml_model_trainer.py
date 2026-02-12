"""ML Model Trainer for trend prediction models."""

import logging
import os
from typing import Tuple, Optional, Dict
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.preprocessing import StandardScaler

from src.config import Config
from src.ml_predictor import MLPredictor


class MLModelTrainer:
    """Trainer for ML models used in trend prediction.
    
    Supports:
    - Random Forest Classifier
    - Gradient Boosting Classifier
    - Model training and validation
    - Model saving to disk
    """
    
    def __init__(self, config: Config):
        """Initialize model trainer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Model hyperparameters
        self.random_state = 42
        
        # Random Forest parameters
        self.rf_n_estimators = 100
        self.rf_max_depth = 10
        self.rf_min_samples_split = 10
        self.rf_min_samples_leaf = 5
        
        # Gradient Boosting parameters
        self.gb_n_estimators = 100
        self.gb_learning_rate = 0.1
        self.gb_max_depth = 5
        self.gb_min_samples_split = 10
        self.gb_min_samples_leaf = 5
    
    def train_random_forest(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray
    ) -> Tuple[RandomForestClassifier, Dict[str, float]]:
        """Train a Random Forest classifier.
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            
        Returns:
            Tuple of (trained_model, validation_metrics)
        """
        self.logger.info("Training Random Forest classifier")
        self.logger.info(
            f"Hyperparameters: n_estimators={self.rf_n_estimators}, "
            f"max_depth={self.rf_max_depth}, "
            f"min_samples_split={self.rf_min_samples_split}, "
            f"min_samples_leaf={self.rf_min_samples_leaf}"
        )
        
        # Create model
        model = RandomForestClassifier(
            n_estimators=self.rf_n_estimators,
            max_depth=self.rf_max_depth,
            min_samples_split=self.rf_min_samples_split,
            min_samples_leaf=self.rf_min_samples_leaf,
            random_state=self.random_state,
            n_jobs=-1,  # Use all CPU cores
            verbose=0
        )
        
        # Train model
        self.logger.info(f"Training on {len(X_train)} samples...")
        model.fit(X_train, y_train)
        self.logger.info("Training complete")
        
        # Validate model
        metrics = self._validate_model(model, X_val, y_val)
        
        return model, metrics
    
    def train_gradient_boosting(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray
    ) -> Tuple[GradientBoostingClassifier, Dict[str, float]]:
        """Train a Gradient Boosting classifier.
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            
        Returns:
            Tuple of (trained_model, validation_metrics)
        """
        self.logger.info("Training Gradient Boosting classifier")
        self.logger.info(
            f"Hyperparameters: n_estimators={self.gb_n_estimators}, "
            f"learning_rate={self.gb_learning_rate}, "
            f"max_depth={self.gb_max_depth}, "
            f"min_samples_split={self.gb_min_samples_split}, "
            f"min_samples_leaf={self.gb_min_samples_leaf}"
        )
        
        # Create model
        model = GradientBoostingClassifier(
            n_estimators=self.gb_n_estimators,
            learning_rate=self.gb_learning_rate,
            max_depth=self.gb_max_depth,
            min_samples_split=self.gb_min_samples_split,
            min_samples_leaf=self.gb_min_samples_leaf,
            random_state=self.random_state,
            verbose=0
        )
        
        # Train model
        self.logger.info(f"Training on {len(X_train)} samples...")
        model.fit(X_train, y_train)
        self.logger.info("Training complete")
        
        # Validate model
        metrics = self._validate_model(model, X_val, y_val)
        
        return model, metrics
    
    def _validate_model(
        self,
        model,
        X_val: np.ndarray,
        y_val: np.ndarray
    ) -> Dict[str, float]:
        """Validate model on validation set.
        
        Args:
            model: Trained model
            X_val: Validation features
            y_val: Validation labels
            
        Returns:
            Dictionary of validation metrics
        """
        self.logger.info(f"Validating on {len(X_val)} samples...")
        
        # Make predictions
        y_pred = model.predict(X_val)
        y_pred_proba = model.predict_proba(X_val)[:, 1]  # Probability of class 1
        
        # Calculate metrics
        accuracy = accuracy_score(y_val, y_pred)
        precision = precision_score(y_val, y_pred, zero_division=0)
        recall = recall_score(y_val, y_pred, zero_division=0)
        f1 = f1_score(y_val, y_pred, zero_division=0)
        
        # Confusion matrix
        cm = confusion_matrix(y_val, y_pred)
        tn, fp, fn, tp = cm.ravel()
        
        metrics = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'true_positives': int(tp)
        }
        
        # Log metrics
        self.logger.info("Validation Results:")
        self.logger.info(f"  Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
        self.logger.info(f"  Precision: {precision:.4f}")
        self.logger.info(f"  Recall:    {recall:.4f}")
        self.logger.info(f"  F1 Score:  {f1:.4f}")
        self.logger.info(f"  Confusion Matrix:")
        self.logger.info(f"    TN: {tn:4d}  FP: {fp:4d}")
        self.logger.info(f"    FN: {fn:4d}  TP: {tp:4d}")
        
        # Check if accuracy meets minimum threshold
        if accuracy < self.config.ml_min_accuracy:
            self.logger.warning(
                f"Model accuracy {accuracy:.2%} is below minimum threshold "
                f"{self.config.ml_min_accuracy:.2%}"
            )
        else:
            self.logger.info(
                f"Model accuracy {accuracy:.2%} meets minimum threshold "
                f"{self.config.ml_min_accuracy:.2%}"
            )
        
        return metrics
    
    def save_model(
        self,
        model,
        scaler: StandardScaler,
        model_path: Optional[str] = None
    ) -> None:
        """Save trained model and scaler to disk.
        
        Args:
            model: Trained model to save
            scaler: Feature scaler to save
            model_path: Path to save model (default: from config)
        """
        if model_path is None:
            model_path = self.config.ml_model_path
        
        self.logger.info(f"Saving model to {model_path}")
        
        # Create MLPredictor instance to use its save method
        ml_predictor = MLPredictor(self.config)
        ml_predictor.model = model
        ml_predictor.feature_scaler = scaler
        
        # Save using MLPredictor's save method
        ml_predictor.save_model(model_path)
        
        self.logger.info(f"Model saved successfully to {model_path}")
    
    def train_and_save_model(
        self,
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_train: np.ndarray,
        y_val: np.ndarray,
        scaler: StandardScaler,
        model_type: str = "random_forest",
        model_path: Optional[str] = None
    ) -> Tuple[object, Dict[str, float]]:
        """Train a model and save it to disk.
        
        This is a convenience method that combines training and saving.
        
        Args:
            X_train: Training features
            X_val: Validation features
            y_train: Training labels
            y_val: Validation labels
            scaler: Feature scaler
            model_type: Type of model ("random_forest" or "gradient_boosting")
            model_path: Path to save model (default: from config)
            
        Returns:
            Tuple of (trained_model, validation_metrics)
            
        Raises:
            ValueError: If model_type is not supported
        """
        self.logger.info(f"Training {model_type} model")
        
        # Train model based on type
        if model_type == "random_forest":
            model, metrics = self.train_random_forest(X_train, y_train, X_val, y_val)
        elif model_type == "gradient_boosting":
            model, metrics = self.train_gradient_boosting(X_train, y_train, X_val, y_val)
        else:
            raise ValueError(
                f"Unsupported model_type: {model_type}. "
                f"Must be 'random_forest' or 'gradient_boosting'"
            )
        
        # Save model
        self.save_model(model, scaler, model_path)
        
        return model, metrics
