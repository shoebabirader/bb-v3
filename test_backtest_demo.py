#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo script to test backtest mode with the trading bot.

This script demonstrates how to run a simple backtest with the trading bot.
It uses the existing configuration and runs a backtest on historical data.

Usage:
    python test_backtest_demo.py
"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.config import Config
from src.trading_bot import TradingBot


def main():
    """Run a demo backtest."""
    print("=" * 60)
    print("Binance Futures Trading Bot - Backtest Demo")
    print("=" * 60)
    print()
    
    try:
        # Load configuration
        print("Loading configuration...")
        config = Config.load_from_file()
        
        # Verify we're in backtest mode
        if config.run_mode != "BACKTEST":
            print(f"Warning: Config is set to {config.run_mode} mode")
            print("   Changing to BACKTEST mode for demo...")
            config.run_mode = "BACKTEST"
        
        print(f"[OK] Configuration loaded successfully")
        print(f"  - Symbol: {config.symbol}")
        print(f"  - Portfolio: {config.portfolio_symbols if config.enable_portfolio_management else 'Disabled'}")
        print(f"  - Backtest Days: {config.backtest_days}")
        print(f"  - Risk per Trade: {config.risk_per_trade * 100}%")
        print(f"  - Leverage: {config.leverage}x")
        print(f"  - Multi-Timeframe: {'Enabled' if config.enable_multi_timeframe else 'Disabled'}")
        print()
        
        # Create and start trading bot
        print("Initializing trading bot...")
        bot = TradingBot(config)
        print("[OK] Trading bot initialized")
        print()
        
        print("Starting backtest...")
        print("This may take a few moments to fetch and process historical data...")
        print()
        
        # Run the backtest
        bot.start()
        
        print()
        print("=" * 60)
        print("Backtest Complete!")
        print("=" * 60)
        print()
        print(f"Results saved to: {config.log_file}")
        print()
        
    except FileNotFoundError as e:
        print(f"\n[ERROR] Configuration file not found")
        print(f"   {e}")
        print(f"\n   Please create config/config.json from config/config.template.json")
        sys.exit(1)
    
    except ValueError as e:
        print(f"\n[ERROR] Configuration Error:")
        print(f"   {e}")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n[WARNING] Backtest interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n[ERROR] Fatal Error:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
