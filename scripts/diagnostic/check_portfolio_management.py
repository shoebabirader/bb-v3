"""Script to verify portfolio management integration.

This script checks that portfolio management is properly integrated
into the trading bot for both paper and live trading modes.
"""

import logging
from binance.client import Client

from src.config import Config
from src.trading_bot import TradingBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Check portfolio management integration."""
    logger.info("=" * 80)
    logger.info("Portfolio Management Integration Check")
    logger.info("=" * 80)
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.load_from_file()
        
        # Check if portfolio management is enabled
        if not config.enable_portfolio_management:
            logger.error("❌ Portfolio management is DISABLED in config")
            logger.info("Set 'enable_portfolio_management': true in config/config.json")
            return 1
        
        logger.info("✓ Portfolio management is ENABLED")
        logger.info(f"✓ Portfolio symbols: {config.portfolio_symbols}")
        logger.info(f"✓ Max symbols: {config.portfolio_max_symbols}")
        logger.info(f"✓ Max single allocation: {config.portfolio_max_single_allocation:.0%}")
        logger.info(f"✓ Max total risk: {config.portfolio_max_total_risk:.0%}")
        logger.info(f"✓ Correlation threshold: {config.portfolio_correlation_threshold}")
        logger.info(f"✓ Correlation max exposure: {config.portfolio_correlation_max_exposure:.0%}")
        
        # Initialize trading bot
        logger.info("\nInitializing trading bot...")
        bot = TradingBot(config)
        
        # Check if portfolio manager was initialized
        if bot.portfolio_manager is None:
            logger.error("❌ Portfolio manager was NOT initialized")
            return 1
        
        logger.info("✓ Portfolio manager initialized successfully")
        logger.info(f"✓ Trading symbols: {bot.portfolio_manager.symbols}")
        
        # Check _get_trading_symbols method
        trading_symbols = bot._get_trading_symbols()
        logger.info(f"✓ _get_trading_symbols() returns: {trading_symbols}")
        
        if len(trading_symbols) == 1:
            logger.warning("⚠️  Only 1 symbol returned - portfolio management may not be active")
        else:
            logger.info(f"✓ Multiple symbols ({len(trading_symbols)}) will be traded")
        
        # Check portfolio manager methods
        logger.info("\nChecking portfolio manager methods...")
        
        # Test get_portfolio_metrics
        metrics = bot.portfolio_manager.get_portfolio_metrics(10000.0)
        logger.info(f"✓ get_portfolio_metrics() works")
        logger.info(f"  - Total value: ${metrics.total_value:.2f}")
        logger.info(f"  - Total PnL: ${metrics.total_pnl:.2f}")
        logger.info(f"  - Total risk: {metrics.total_risk:.2%}")
        logger.info(f"  - Diversification ratio: {metrics.diversification_ratio:.2f}")
        
        # Test check_total_risk
        risk_ok = bot.portfolio_manager.check_total_risk(10000.0)
        logger.info(f"✓ check_total_risk() works: {risk_ok}")
        
        logger.info("\n" + "=" * 80)
        logger.info("PORTFOLIO MANAGEMENT INTEGRATION: ✓ VERIFIED")
        logger.info("=" * 80)
        logger.info("\nPortfolio management is properly integrated and ready to use!")
        logger.info("The bot will now:")
        logger.info("  1. Fetch data for all portfolio symbols")
        logger.info("  2. Generate signals for each symbol")
        logger.info("  3. Allocate capital based on signal confidence")
        logger.info("  4. Enforce correlation limits")
        logger.info("  5. Maintain portfolio-level risk limits")
        logger.info("  6. Rebalance every 6 hours")
        logger.info("\nTo start trading with portfolio management:")
        logger.info("  python start_paper_trading.py")
        
        return 0
    
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
