"""Script to train ML model for trend prediction.

This script demonstrates how to use the ML training pipeline to:
1. Collect historical data
2. Prepare training data with features and labels
3. Train a Random Forest or Gradient Boosting model
4. Validate the model
5. Save the trained model to disk

Usage:
    python train_ml_model.py [--model-type random_forest|gradient_boosting] [--days 90]
"""

import argparse
import logging
import sys
from binance.client import Client

from src.config import Config
from src.data_manager import DataManager
from src.ml_predictor import MLPredictor
from src.ml_training_pipeline import MLTrainingPipeline
from src.ml_model_trainer import MLModelTrainer


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main training function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Train ML model for trend prediction')
    parser.add_argument(
        '--model-type',
        type=str,
        default='random_forest',
        choices=['random_forest', 'gradient_boosting'],
        help='Type of model to train (default: random_forest)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days of historical data to use (default: 90)'
    )
    parser.add_argument(
        '--sample-every',
        type=int,
        default=4,
        help='Sample every Nth candle to speed up training (default: 4 = 1 hour intervals for 15m candles)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Path to save trained model (default: from config)'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("ML Model Training Pipeline")
    logger.info("=" * 80)
    logger.info(f"Model Type: {args.model_type}")
    logger.info(f"Training Days: {args.days}")
    logger.info(f"Sampling: Every {args.sample_every} candles")
    logger.info("=" * 80)
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.load_from_file()
        
        # Override training days if specified
        if args.days:
            config.ml_training_lookback_days = args.days
        
        # Initialize Binance client
        logger.info("Initializing Binance client...")
        client = Client(config.api_key, config.api_secret)
        
        # Initialize data manager
        logger.info("Initializing data manager...")
        data_manager = DataManager(config, client)
        
        # Initialize ML predictor (for feature extraction)
        logger.info("Initializing ML predictor...")
        ml_predictor = MLPredictor(config)
        
        # Initialize training pipeline
        logger.info("Initializing training pipeline...")
        pipeline = MLTrainingPipeline(config, data_manager)
        
        # Prepare training data
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Preparing Training Data")
        logger.info("=" * 80)
        X_train, X_val, y_train, y_val, scaler = pipeline.prepare_training_data(
            ml_predictor,
            days=args.days,
            sample_every=args.sample_every
        )
        
        logger.info(f"\nTraining data prepared:")
        logger.info(f"  Training samples: {len(X_train)}")
        logger.info(f"  Validation samples: {len(X_val)}")
        logger.info(f"  Features per sample: {X_train.shape[1]}")
        logger.info(f"  Training labels - Bullish: {sum(y_train)}, Bearish: {len(y_train) - sum(y_train)}")
        logger.info(f"  Validation labels - Bullish: {sum(y_val)}, Bearish: {len(y_val) - sum(y_val)}")
        
        # Initialize model trainer
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Training Model")
        logger.info("=" * 80)
        trainer = MLModelTrainer(config)
        
        # Determine output path
        output_path = args.output if args.output else config.ml_model_path
        
        # Train and save model
        model, metrics = trainer.train_and_save_model(
            X_train, X_val, y_train, y_val,
            scaler,
            model_type=args.model_type,
            model_path=output_path
        )
        
        # Display final results
        logger.info("\n" + "=" * 80)
        logger.info("TRAINING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Model Type: {args.model_type}")
        logger.info(f"Model saved to: {output_path}")
        logger.info(f"\nValidation Metrics:")
        logger.info(f"  Accuracy:  {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
        logger.info(f"  Precision: {metrics['precision']:.4f}")
        logger.info(f"  Recall:    {metrics['recall']:.4f}")
        logger.info(f"  F1 Score:  {metrics['f1_score']:.4f}")
        logger.info(f"\nConfusion Matrix:")
        logger.info(f"  True Negatives:  {metrics['true_negatives']:4d}")
        logger.info(f"  False Positives: {metrics['false_positives']:4d}")
        logger.info(f"  False Negatives: {metrics['false_negatives']:4d}")
        logger.info(f"  True Positives:  {metrics['true_positives']:4d}")
        
        # Check if model meets minimum accuracy
        if metrics['accuracy'] >= config.ml_min_accuracy:
            logger.info(f"\n✓ Model accuracy meets minimum threshold ({config.ml_min_accuracy:.2%})")
            logger.info("  Model is ready for use in trading bot")
        else:
            logger.warning(f"\n✗ Model accuracy below minimum threshold ({config.ml_min_accuracy:.2%})")
            logger.warning("  Consider:")
            logger.warning("    - Collecting more training data")
            logger.warning("    - Adjusting model hyperparameters")
            logger.warning("    - Trying a different model type")
        
        logger.info("\n" + "=" * 80)
        logger.info("To use this model, set enable_ml_prediction=true in config.json")
        logger.info("=" * 80)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nTraining interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"\nTraining failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
