"""Trace signal execution step-by-step to find where it's blocked."""

from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer
from src.portfolio_manager import PortfolioManager

config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)

# Initialize components
data_manager = DataManager(config, client)
strategy = StrategyEngine(config)
position_sizer = PositionSizer(config)
risk_manager = RiskManager(config, position_sizer)

# Initialize portfolio manager if enabled
portfolio_manager = None
if config.enable_portfolio_management:
    portfolio_manager = PortfolioManager(config)

print("=" * 80)
print("SIGNAL EXECUTION TRACE FOR XRPUSDT")
print("=" * 80)
print()

symbol = "XRPUSDT"
wallet_balance = 10000.0  # Default for paper trading

print("STEP 1: Fetch Data")
print("-" * 80)
try:
    candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
    candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
    candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol)
    candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol)
    print(f"✓ Data fetched: 15m={len(candles_15m)}, 1h={len(candles_1h)}, 5m={len(candles_5m)}, 4h={len(candles_4h)}")
except Exception as e:
    print(f"✗ Error fetching data: {e}")
    exit(1)

print()
print("STEP 2: Update Indicators")
print("-" * 80)
try:
    strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
    print("✓ Indicators updated")
except Exception as e:
    print(f"✗ Error updating indicators: {e}")
    exit(1)

print()
print("STEP 3: Check for Active Position")
print("-" * 80)
active_position = risk_manager.get_active_position(symbol)
if active_position:
    print(f"✗ Active position exists: {active_position.side} @ ${active_position.entry_price}")
    print("  Bot will NOT open new position while one is active")
    exit(0)
else:
    print("✓ No active position")

print()
print("STEP 4: Check if Signal Generation is Enabled")
print("-" * 80)
if risk_manager.is_signal_generation_enabled():
    print("✓ Signal generation is enabled")
else:
    print("✗ Signal generation is DISABLED")
    print("  This blocks all new trades")
    exit(1)

print()
print("STEP 5: Check for Signals")
print("-" * 80)
long_signal = strategy.check_long_entry(symbol)
short_signal = strategy.check_short_entry(symbol)

if long_signal:
    print(f"✓ LONG signal detected for {symbol}")
    signal = long_signal
elif short_signal:
    print(f"✓ SHORT signal detected for {symbol}")
    signal = short_signal
else:
    print("✗ No signal detected")
    print("  Check signal conditions with: python check_all_signal_conditions.py")
    exit(0)

print()
print("STEP 6: Check Portfolio Risk Limits (if enabled)")
print("-" * 80)
if portfolio_manager:
    print(f"Portfolio management: ENABLED")
    if portfolio_manager.check_total_risk(wallet_balance):
        print("✓ Portfolio risk check passed")
    else:
        print("✗ Portfolio risk limit EXCEEDED")
        print("  This blocks the trade")
        exit(1)
else:
    print("Portfolio management: DISABLED")
    print("✓ No portfolio risk check needed")

print()
print("STEP 7: Open Position")
print("-" * 80)
try:
    atr = strategy.current_indicators.atr_15m
    print(f"ATR: {atr:.4f}")
    
    position = risk_manager.open_position(
        signal,
        wallet_balance,
        atr
    )
    print(f"✓ Position created: {position.side} @ ${position.entry_price:.4f}")
    print(f"  Quantity: {position.quantity:.4f}")
    print(f"  Stop Loss: ${position.stop_loss:.4f}")
except Exception as e:
    print(f"✗ Error opening position: {e}")
    exit(1)

print()
print("STEP 8: Check Portfolio Position Limits (if enabled)")
print("-" * 80)
if portfolio_manager:
    current_price = candles_15m[-1].close
    if portfolio_manager.can_add_position(symbol, position, wallet_balance):
        print("✓ Portfolio can add this position")
    else:
        print("✗ Portfolio CANNOT add this position")
        print("  Reasons:")
        print("  - May exceed max single allocation")
        print("  - May have correlation issues")
        print("  - May exceed total risk")
        print()
        print("  Position would be closed immediately")
        
        # Close the position
        risk_manager.close_position(position, current_price, "SIGNAL_EXIT")
        exit(1)
else:
    print("Portfolio management: DISABLED")
    print("✓ No portfolio position check needed")

print()
print("STEP 9: Update Portfolio Manager")
print("-" * 80)
if portfolio_manager:
    try:
        portfolio_manager.update_position(symbol, position)
        print("✓ Portfolio manager updated")
    except Exception as e:
        print(f"✗ Error updating portfolio: {e}")
else:
    print("Portfolio management: DISABLED")
    print("✓ No portfolio update needed")

print()
print("=" * 80)
print("EXECUTION TRACE COMPLETE")
print("=" * 80)
print()
print("✓ ALL CHECKS PASSED!")
print()
print("The signal SHOULD execute successfully.")
print()
print("If the bot is still not executing:")
print("  1. Check if bot is actually running")
print("  2. Check bot logs for errors")
print("  3. Verify config matches this test")
print("  4. Try restarting the bot")
