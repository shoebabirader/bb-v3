"""Check if bot is running and why it's not executing the valid XAGUSDT SHORT signal."""

import psutil
import sys
from binance.client import Client
from src.config import Config
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer

print("=" * 80)
print("BOT EXECUTION DIAGNOSTIC - XAGUSDT SHORT SIGNAL")
print("=" * 80)
print()

# Step 1: Check if bot is running
print("STEP 1: Check if Bot Process is Running")
print("-" * 80)

bot_running = False
bot_processes = []

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info['cmdline']
        if cmdline:
            cmdline_str = ' '.join(cmdline)
            if 'python' in cmdline_str.lower() and ('main.py' in cmdline_str or 'start_paper_trading.py' in cmdline_str):
                bot_running = True
                bot_processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cmdline': cmdline_str
                })
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

if bot_running:
    print(f"✓ Bot IS RUNNING ({len(bot_processes)} process(es))")
    for proc in bot_processes:
        print(f"  PID: {proc['pid']}")
        print(f"  Command: {proc['cmdline']}")
else:
    print("✗ Bot is NOT RUNNING!")
    print()
    print("=" * 80)
    print("⚠️  THE BOT MUST BE RUNNING TO EXECUTE TRADES!")
    print("=" * 80)
    print()
    print("You have a VALID SHORT SIGNAL for XAGUSDT, but the bot is not running.")
    print()
    print("To start the bot and execute the trade:")
    print("  python main.py")
    print()
    print("The bot will automatically detect the signal and execute the trade.")
    sys.exit(0)

print()

# Step 2: Check for existing positions
print("STEP 2: Check for Existing Positions")
print("-" * 80)

config = Config.load_from_file()
position_sizer = PositionSizer(config)
risk_manager = RiskManager(config, position_sizer)

existing_position = risk_manager.get_active_position("XAGUSDT")
if existing_position:
    print(f"⚠️  Position already exists for XAGUSDT!")
    print(f"  Side: {existing_position.side}")
    print(f"  Entry: ${existing_position.entry_price:.4f}")
    print(f"  Quantity: {existing_position.quantity:.4f}")
    print()
    print("The bot will NOT open a new position while one already exists.")
    print("Wait for the current position to close, or close it manually.")
else:
    print("✓ No existing position for XAGUSDT")

print()

# Step 3: Check signal generation status
print("STEP 3: Check Signal Generation Status")
print("-" * 80)

if risk_manager.is_signal_generation_enabled():
    print("✓ Signal generation is ENABLED")
else:
    print("✗ Signal generation is DISABLED")
    print("  This blocks all new trades")
    print()
    print("Possible reasons:")
    print("  - Maximum drawdown exceeded")
    print("  - Too many consecutive losses")
    print("  - Risk limits breached")

print()

# Step 4: Check account balance
print("STEP 4: Check Account Balance")
print("-" * 80)

try:
    client = Client(config.api_key, config.api_secret)
    account = client.futures_account()
    balance = float(account['totalWalletBalance'])
    
    print(f"✓ Account balance: ${balance:.2f}")
    
    if balance < 10.0:
        print("⚠️  WARNING: Balance is very low!")
        print("  Minimum recommended: $50 for safe trading")
        print("  Your balance: $" + f"{balance:.2f}")
    
    # Calculate required margin for XAGUSDT SHORT
    current_price = 81.42  # From your signal check
    risk_amount = balance * config.risk_per_trade
    atr = current_price * 0.02  # Estimate 2% ATR
    stop_distance = atr * config.stop_loss_atr_multiplier
    quantity = (risk_amount / stop_distance) * config.leverage
    notional_value = current_price * quantity
    margin_required = notional_value / config.leverage
    
    print()
    print("  Trade Calculation:")
    print(f"    Risk per trade: {config.risk_per_trade * 100}%")
    print(f"    Risk amount: ${risk_amount:.2f}")
    print(f"    Leverage: {config.leverage}x")
    print(f"    Estimated quantity: {quantity:.4f}")
    print(f"    Notional value: ${notional_value:.2f}")
    print(f"    Margin required: ${margin_required:.2f}")
    
    if margin_required > balance:
        print()
        print("✗ INSUFFICIENT MARGIN!")
        print(f"  Required: ${margin_required:.2f}")
        print(f"  Available: ${balance:.2f}")
        print()
        print("This will block trade execution.")
    else:
        print()
        print(f"✓ Sufficient margin (${balance - margin_required:.2f} remaining)")
        
except Exception as e:
    print(f"✗ Error checking balance: {e}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()

if bot_running and not existing_position and risk_manager.is_signal_generation_enabled():
    print("✅ BOT SHOULD BE EXECUTING THE TRADE!")
    print()
    print("If trade is still not executing:")
    print("  1. Check bot terminal for error messages")
    print("  2. Check logs/trades.log for execution errors")
    print("  3. Verify Binance API has futures trading permission")
    print("  4. Ensure sufficient margin (see calculation above)")
    print()
    print("The bot checks for signals every 0.1 seconds.")
    print("The trade should execute within 1-2 minutes.")
else:
    print("⚠️  BOT CANNOT EXECUTE TRADE")
    print()
    if not bot_running:
        print("  ✗ Bot is not running - START IT: python main.py")
    if existing_position:
        print("  ✗ Position already exists - wait for it to close")
    if not risk_manager.is_signal_generation_enabled():
        print("  ✗ Signal generation is disabled - check risk limits")

print()
