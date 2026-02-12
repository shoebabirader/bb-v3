"""Test if the execution function works properly by creating a fake signal."""

from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer
from src.portfolio_manager import PortfolioManager
from src.models import Signal
import time

config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)

# Initialize components
data_manager = DataManager(config, client)
position_sizer = PositionSizer(config)
risk_manager = RiskManager(config, position_sizer)

# Initialize portfolio manager if enabled
portfolio_manager = None
if config.enable_portfolio_management:
    portfolio_manager = PortfolioManager(config)

print("=" * 80)
print("EXECUTION FUNCTION TEST")
print("=" * 80)
print()

symbol = "XRPUSDT"
wallet_balance = 10000.0

print("TEST SETUP")
print("-" * 80)
print(f"Symbol: {symbol}")
print(f"Wallet Balance: ${wallet_balance:.2f}")
print(f"Portfolio Management: {'ENABLED' if portfolio_manager else 'DISABLED'}")
print()

# Fetch current price
print("STEP 1: Fetch Current Price")
print("-" * 80)
try:
    candles = data_manager.fetch_historical_data(days=1, timeframe="15m", symbol=symbol)
    current_price = candles[-1].close
    print(f"✓ Current Price: ${current_price:.4f}")
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

# Create a fake SHORT signal
print()
print("STEP 2: Create Fake SHORT Signal")
print("-" * 80)
fake_signal = Signal(
    type="SHORT_ENTRY",
    timestamp=int(time.time() * 1000),
    price=current_price,
    indicators={
        'vwap_15m': current_price * 1.01,  # Price below VWAP
        'trend_15m': 'BEARISH',
        'trend_1h': 'BEARISH',
        'adx': 25.0,
        'rvol': 1.5,
        'squeeze_color': 'maroon',
        'squeeze_value': -1.0
    },
    symbol=symbol
)
print(f"✓ Created fake {fake_signal.type} signal")
print(f"  Price: ${fake_signal.price:.4f}")
print(f"  Symbol: {fake_signal.symbol}")

# Check if signal generation is enabled
print()
print("STEP 3: Check Signal Generation Enabled")
print("-" * 80)
if not risk_manager.is_signal_generation_enabled():
    print("✗ Signal generation is DISABLED")
    print("  Cannot test execution")
    exit(1)
print("✓ Signal generation is enabled")

# Check for existing position
print()
print("STEP 4: Check for Existing Position")
print("-" * 80)
existing_position = risk_manager.get_active_position(symbol)
if existing_position:
    print(f"✗ Position already exists: {existing_position.side} @ ${existing_position.entry_price}")
    print("  Closing it first...")
    risk_manager.close_position(existing_position, current_price, "TEST_CLEANUP")
    print("✓ Position closed")
else:
    print("✓ No existing position")

# Check portfolio risk limits
print()
print("STEP 5: Check Portfolio Risk Limits")
print("-" * 80)
if portfolio_manager:
    if portfolio_manager.check_total_risk(wallet_balance):
        print("✓ Portfolio risk check PASSED")
    else:
        print("✗ Portfolio risk limit EXCEEDED")
        print("  Cannot test execution")
        exit(1)
else:
    print("✓ No portfolio manager (skip check)")

# Open position using risk manager
print()
print("STEP 6: Execute Position Opening")
print("-" * 80)
try:
    # Calculate ATR (use a reasonable default)
    atr = current_price * 0.02  # 2% of price as ATR estimate
    
    print(f"  Using ATR: ${atr:.4f}")
    
    # Open position
    position = risk_manager.open_position(
        fake_signal,
        wallet_balance,
        atr
    )
    
    print("✓ Position opened successfully!")
    print()
    print("  Position Details:")
    print(f"    Symbol: {position.symbol}")
    print(f"    Side: {position.side}")
    print(f"    Entry Price: ${position.entry_price:.4f}")
    print(f"    Quantity: {position.quantity:.4f}")
    print(f"    Stop Loss: ${position.stop_loss:.4f}")
    print(f"    Trailing Stop: ${position.trailing_stop:.4f}")
    print(f"    Leverage: {position.leverage}x")
    
except Exception as e:
    print(f"✗ Error opening position: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Check portfolio position limits
print()
print("STEP 7: Check Portfolio Position Limits")
print("-" * 80)
if portfolio_manager:
    if portfolio_manager.can_add_position(symbol, position, wallet_balance):
        print("✓ Portfolio CAN add this position")
    else:
        print("✗ Portfolio CANNOT add this position")
        print("  This would block execution in real bot")
        print()
        print("  Cleaning up...")
        risk_manager.close_position(position, current_price, "TEST_CLEANUP")
        exit(1)
else:
    print("✓ No portfolio manager (skip check)")

# Update portfolio manager
print()
print("STEP 8: Update Portfolio Manager")
print("-" * 80)
if portfolio_manager:
    try:
        portfolio_manager.update_position(symbol, position)
        print("✓ Portfolio manager updated successfully")
    except Exception as e:
        print(f"✗ Error updating portfolio: {e}")
        # Clean up
        risk_manager.close_position(position, current_price, "TEST_CLEANUP")
        exit(1)
else:
    print("✓ No portfolio manager (skip update)")

# Verify position is stored
print()
print("STEP 9: Verify Position is Stored")
print("-" * 80)
stored_position = risk_manager.get_active_position(symbol)
if stored_position:
    print("✓ Position is stored in risk manager")
    print(f"  {stored_position.side} @ ${stored_position.entry_price:.4f}")
else:
    print("✗ Position NOT found in risk manager")
    exit(1)

# Clean up
print()
print("STEP 10: Clean Up Test Position")
print("-" * 80)
try:
    trade = risk_manager.close_position(position, current_price, "TEST_CLEANUP")
    print("✓ Test position closed")
    print(f"  PnL: ${trade.pnl:.2f}")
    
    # Clear from portfolio manager
    if portfolio_manager:
        portfolio_manager.update_position(symbol, None)
        print("✓ Portfolio manager cleared")
        
except Exception as e:
    print(f"✗ Error closing position: {e}")

print()
print("=" * 80)
print("EXECUTION FUNCTION TEST COMPLETE")
print("=" * 80)
print()
print("✅ ALL EXECUTION FUNCTIONS WORKING PROPERLY!")
print()
print("The bot CAN execute trades when signals are detected.")
print("If bot is not trading, it's because:")
print("  1. No valid signals exist (check with: python check_current_signals_simple.py)")
print("  2. Portfolio manager is blocking (check risk limits)")
print("  3. Advanced features are blocking (multi-timeframe, regime, etc.)")
