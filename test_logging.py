"""Test logging and live trading setup."""

import logging
import sys
import os

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("LOGGING TEST")
logger.info("=" * 80)
logger.info("If you see this in console AND in logs/test.log, logging works!")
logger.info("=" * 80)

print("\nCheck logs/test.log to verify file logging works")
