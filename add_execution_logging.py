"""Add detailed execution logging to see why trades aren't executing."""

import fileinput
import sys

# Add logging after signal check in trading_bot.py
trading_bot_file = "src/trading_bot.py"

print("Adding detailed execution logging to trading_bot.py...")
print()

# Read the file
with open(trading_bot_file, 'r') as f:
    content = f.read()

# Find the section where signals are checked
search_str = """                if self.risk_manager.is_signal_generation_enabled():
                    long_signal = self.strategy.check_long_entry(symbol)
                    short_signal = self.strategy.check_short_entry(symbol)
                    
                    signal = long_signal or short_signal
                    
                    if signal:"""

replace_str = """                if self.risk_manager.is_signal_generation_enabled():
                    long_signal = self.strategy.check_long_entry(symbol)
                    short_signal = self.strategy.check_short_entry(symbol)
                    
                    # DEBUG LOGGING
                    logger.info(f"[{symbol}] Signal check: LONG={long_signal is not None}, SHORT={short_signal is not None}")
                    if long_signal:
                        logger.info(f"[{symbol}] LONG SIGNAL DETECTED! Price=${long_signal.price:.4f}")
                    if short_signal:
                        logger.info(f"[{symbol}] SHORT SIGNAL DETECTED! Price=${short_signal.price:.4f}")
                    
                    signal = long_signal or short_signal
                    
                    if signal:
                        logger.info(f"[{symbol}] ✓ Signal exists, proceeding to open position...")"""

if search_str in content:
    content = content.replace(search_str, replace_str)
    
    with open(trading_bot_file, 'w') as f:
        f.write(content)
    
    print("✓ Added signal detection logging")
else:
    print("✗ Could not find signal check section")
    sys.exit(1)

# Add logging after position opening
search_str2 = """                        # Open position
                        atr = self.strategy.current_indicators.atr_15m
                        position = self.risk_manager.open_position(
                            signal,
                            self.wallet_balance,
                            atr
                        )"""

replace_str2 = """                        # Open position
                        atr = self.strategy.current_indicators.atr_15m
                        logger.info(f"[{symbol}] Opening position: ATR=${atr:.4f}, Balance=${self.wallet_balance:.2f}")
                        position = self.risk_manager.open_position(
                            signal,
                            self.wallet_balance,
                            atr
                        )
                        logger.info(f"[{symbol}] ✓ Position created: {position.side} qty={position.quantity:.4f} @ ${position.entry_price:.4f}")"""

if search_str2 in content:
    content = content.replace(search_str2, replace_str2)
    
    with open(trading_bot_file, 'w') as f:
        f.write(content)
    
    print("✓ Added position opening logging")
else:
    print("✗ Could not find position opening section")

# Add logging before order execution
search_str3 = """                        # Execute entry order (if not simulating)
                        if not simulate_execution:
                            # Validate margin availability
                            margin_required = (position.entry_price * position.quantity) / position.leverage"""

replace_str3 = """                        # Execute entry order (if not simulating)
                        logger.info(f"[{symbol}] Checking if should execute order (simulate={simulate_execution})...")
                        if not simulate_execution:
                            # Validate margin availability
                            margin_required = (position.entry_price * position.quantity) / position.leverage
                            logger.info(f"[{symbol}] Margin required: ${margin_required:.2f}")"""

if search_str3 in content:
    content = content.replace(search_str3, replace_str3)
    
    with open(trading_bot_file, 'w') as f:
        f.write(content)
    
    print("✓ Added order execution logging")
else:
    print("✗ Could not find order execution section")

print()
print("=" * 80)
print("LOGGING ADDED SUCCESSFULLY")
print("=" * 80)
print()
print("Now restart the bot:")
print("  1. Stop bot: Ctrl+C")
print("  2. Start bot: python main.py")
print()
print("Watch the terminal for detailed execution logs.")
print("You'll see exactly where the execution stops.")
print()
