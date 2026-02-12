#!/usr/bin/env python3
"""Start bot with detailed logging to diagnose hanging issues."""

import sys
import logging

# Set up detailed logging BEFORE importing anything else
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/startup_debug.log', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("STARTING BOT WITH DETAILED LOGGING")
logger.info("=" * 80)

try:
    logger.info("Step 1: Importing modules...")
    from src.config import Config
    from src.trading_bot import TradingBot
    logger.info("  OK Modules imported")
    
    logger.info("Step 2: Loading configuration...")
    config = Config.load_from_file("config/config.json")
    logger.info(f"  OK Config loaded: {config.run_mode} mode, symbol={config.symbol}")
    
    logger.info("Step 3: Creating TradingBot instance...")
    bot = TradingBot(config)
    logger.info("  OK TradingBot created")
    
    logger.info("Step 4: Starting bot...")
    bot.start()
    logger.info("  OK Bot started successfully")
    
except KeyboardInterrupt:
    logger.info("\nBot stopped by user (Ctrl+C)")
except Exception as e:
    logger.error(f"\nERROR: {e}", exc_info=True)
    sys.exit(1)
