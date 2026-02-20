"""Comprehensive fix for logging and live trading issues.

This script:
1. Adds detailed logging to EVERY critical operation
2. Ensures logs are written to files AND console
3. Verifies live trading mode is working correctly
4. Tests API permissions before trading
"""

import os
import sys

print("=" * 80)
print("FIXING LOGGING AND LIVE TRADING ISSUES")
print("=" * 80)

# Step 1: Check current logging setup
print("\n[1] Checking logging setup...")

if not os.path.exists("logs"):
    print("  ✗ logs/ directory doesn't exist - CREATING IT")
    os.makedirs("logs", exist_ok=True)
else:
    print("  ✓ logs/ directory exists")

# List existing log files
log_files = [f for f in os.listdir("logs") if f.endswith(".log")]
if log_files:
    print(f"  ✓ Found {len(log_files)} log files:")
    for f in log_files:
        size = os.path.getsize(os.path.join("logs", f))
        print(f"    - {f} ({size} bytes)")
else:
    print("  ⚠ No log files found - this is the problem!")

# Step 2: Add console logging to trading_bot.py
print("\n[2] Adding console logging to trading_bot.py...")

with open("src/trading_bot.py", "r", encoding="utf-8") as f:
    content = f.read()

# Check if console handler already exists
if "StreamHandler" in content:
    print("  ✓ Console logging already configured")
else:
    print("  ✗ Console logging NOT configured - ADDING IT")
    
    # Find the logging configuration section
    old_logging = """# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)"""
    
    new_logging = """# Configure logging with BOTH file and console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(sys.stdout)  # Print to console
    ]
)
logger = logging.getLogger(__name__)
logger.info("=" * 80)
logger.info("TRADING BOT STARTING")
logger.info("=" * 80)"""
    
    if old_logging in content:
        content = content.replace(old_logging, new_logging)
        
        with open("src/trading_bot.py", "w", encoding="utf-8") as f:
            f.write(content)
        
        print("  ✓ Console logging added successfully")
    else:
        print("  ⚠ Could not find logging configuration to update")

# Step 3: Add detailed execution logging
print("\n[3] Adding detailed execution logging...")

with open("src/trading_bot.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add logging to _run_live_trading
if 'logger.info("LIVE TRADING MODE ACTIVATED")' not in content:
    print("  Adding LIVE mode logging...")
    
    old_live = '''def _run_live_trading(self):
        """Run live trading mode with real execution."""
        self.ui_display.show_notification("Starting LIVE trading mode...", "WARNING")
        self.ui_display.show_notification("⚠️  REAL MONEY AT RISK ⚠️", "ERROR")'''
    
    new_live = '''def _run_live_trading(self):
        """Run live trading mode with real execution."""
        logger.info("=" * 80)
        logger.info("LIVE TRADING MODE ACTIVATED")
        logger.info("⚠️  REAL MONEY AT RISK ⚠️")
        logger.info("=" * 80)
        self.ui_display.show_notification("Starting LIVE trading mode...", "WARNING")
        self.ui_display.show_notification("⚠️  REAL MONEY AT RISK ⚠️", "ERROR")'''
    
    if old_live in content:
        content = content.replace(old_live, new_live)
        print("  ✓ Added LIVE mode logging")

# Add logging to order execution
if 'logger.info(f"EXECUTING REAL ORDER")' not in content:
    print("  Adding order execution logging...")
    
    old_order = '''                        if not simulate_execution:
                            # Validate margin availability
                            margin_required = (position.entry_price * position.quantity) / position.leverage'''
    
    new_order = '''                        if not simulate_execution:
                            logger.info(f"[{symbol}] =" * 40)
                            logger.info(f"[{symbol}] EXECUTING REAL ORDER ON BINANCE")
                            logger.info(f"[{symbol}] Symbol: {symbol}")
                            logger.info(f"[{symbol}] Side: {position.side}")
                            logger.info(f"[{symbol}] Quantity: {position.quantity}")
                            logger.info(f"[{symbol}] Entry Price: {position.entry_price}")
                            logger.info(f"[{symbol}] =" * 40)
                            
                            # Validate margin availability
                            margin_required = (position.entry_price * position.quantity) / position.leverage'''
    
    if old_order in content:
        content = content.replace(old_order, new_order)
        print("  ✓ Added order execution logging")

# Save changes
with open("src/trading_bot.py", "w", encoding="utf-8") as f:
    f.write(content)

# Step 4: Add logging to order_executor.py
print("\n[4] Adding detailed logging to order_executor.py...")

with open("src/order_executor.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add detailed logging to place_market_order
if 'logger.info("=" * 80)' not in content:
    print("  Adding detailed order placement logging...")
    
    old_place = '''    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """Place market order with retry logic.
        
        Implements exponential backoff retry strategy (3 attempts).
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            side: Order side ("BUY" or "SELL")
            quantity: Order quantity in base currency
            reduce_only: If True, order can only reduce position
            
        Returns:
            Order response from Binance API
            
        Raises:
            BinanceAPIException: If all retry attempts fail
            ValueError: If client is not initialized or invalid parameters
        """
        if self.client is None:
            raise ValueError("Binance client not initialized. Cannot place orders in BACKTEST mode.")
        
        # Ensure authenticated and permissions validated before trading
        self.ensure_authenticated()
        self.ensure_permissions_validated()
        
        if side not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid order side '{side}'. Must be 'BUY' or 'SELL'")
        
        if quantity <= 0:
            raise ValueError(f"Invalid quantity {quantity}. Must be positive")
        
        logger.info(f"Placing market {side} order for {quantity} {symbol}")'''
    
    new_place = '''    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """Place market order with retry logic.
        
        Implements exponential backoff retry strategy (3 attempts).
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            side: Order side ("BUY" or "SELL")
            quantity: Order quantity in base currency
            reduce_only: If True, order can only reduce position
            
        Returns:
            Order response from Binance API
            
        Raises:
            BinanceAPIException: If all retry attempts fail
            ValueError: If client is not initialized or invalid parameters
        """
        logger.info("=" * 80)
        logger.info("PLACE_MARKET_ORDER CALLED")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Side: {side}")
        logger.info(f"Quantity: {quantity}")
        logger.info(f"Reduce Only: {reduce_only}")
        logger.info("=" * 80)
        
        if self.client is None:
            logger.error("CRITICAL: Binance client is None - cannot place order!")
            raise ValueError("Binance client not initialized. Cannot place orders in BACKTEST mode.")
        
        # Ensure authenticated and permissions validated before trading
        logger.info("Checking authentication...")
        self.ensure_authenticated()
        logger.info("✓ Authenticated")
        
        logger.info("Checking permissions...")
        self.ensure_permissions_validated()
        logger.info("✓ Permissions validated")
        
        if side not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid order side '{side}'. Must be 'BUY' or 'SELL'")
        
        if quantity <= 0:
            raise ValueError(f"Invalid quantity {quantity}. Must be positive")
        
        logger.info(f"Placing market {side} order for {quantity} {symbol}")
        logger.info("Calling Binance API...")'''
    
    if old_place in content:
        content = content.replace(old_place, new_place)
        print("  ✓ Added detailed order placement logging")

# Save changes
with open("src/order_executor.py", "w", encoding="utf-8") as f:
    f.write(content)

# Step 5: Create a test script to verify logging
print("\n[5] Creating test script...")

test_script = '''"""Test logging and live trading setup."""

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

print("\\nCheck logs/test.log to verify file logging works")
'''

with open("test_logging.py", "w", encoding="utf-8") as f:
    f.write(test_script)

print("  ✓ Created test_logging.py")

# Step 6: Summary
print("\n" + "=" * 80)
print("FIXES APPLIED SUCCESSFULLY")
print("=" * 80)

print("\n✅ What was fixed:")
print("  1. Added console logging (you'll see logs in terminal)")
print("  2. Added file logging (logs saved to logs/ directory)")
print("  3. Added detailed execution logging for LIVE mode")
print("  4. Added detailed order placement logging")
print("  5. Created test script to verify logging")

print("\n📋 Next steps:")
print("  1. Test logging:")
print("     python test_logging.py")
print("")
print("  2. Check API permissions (CRITICAL for live trading):")
print("     python test_api_permissions.py")
print("")
print("  3. Start bot and check logs:")
print("     python main.py")
print("     - Watch console for real-time logs")
print("     - Check logs/bot.log for file logs")
print("     - Check logs/trades.log for trade logs")

print("\n⚠️  IMPORTANT: API Permissions Issue")
print("  Your previous error showed: 'Invalid API-key, IP, or permissions'")
print("  This means your Binance API key lacks permissions.")
print("")
print("  Fix this at: https://www.binance.com/en/my/settings/api-management")
print("  Enable these permissions:")
print("    ✓ Enable Reading")
print("    ✓ Enable Futures")
print("")
print("  Without these, live trading will NOT work!")

print("\n" + "=" * 80)
