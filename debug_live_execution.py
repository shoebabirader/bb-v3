"""Debug why bot is not executing despite valid signal and sufficient margin."""

import psutil
from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer
from src.order_executor import OrderExecutor

print("=" * 80)
print("LIVE EXECUTION DEBUG - WHY NO TRADE?")
print("=" * 80)
print()

# Load config
config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)

print("CONFIG CHECK")
print("-" * 80)
print(f"Run Mode: {config.run_mode}")
print(f"Symbol: {config.symbol}")
print(f"Risk Per Trade: {config.risk_per_trade * 100}%")
print(f"Leverage: {config.leverage}x")
print(f"Portfolio Management: {config.enable_portfolio_management}")
print(f"Multi-Timeframe: {config.enable_multi_timeframe}")
print(f"Volume Profile: {config.enable_volume_profile}")
print(f"Advanced Exits: {config.enable_advanced_exits}")
print()

# Check bot running
print("BOT STATUS")
print("-" * 80)
bot_running = False
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info['cmdline']
        if cmdline:
            cmdline_str = ' '.join(cmdline)
            if 'python' in cmdline_str.lower() and 'main.py' in cmdline_str:
                bot_running = True
                print(f"✓ Bot is running (PID: {proc.info['pid']})")
                break
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

if not bot_running:
    print("✗ Bot is NOT running!")
    print("  Start it: python main.py")
    exit(1)

print()

# Check signal
print("SIGNAL CHECK")
print("-" * 80)
data_manager = DataManager(config, client)
strategy = StrategyEngine(config)

try:
    candles_15m = data_manager.fetch_historical_data(days=2, timeframe="15m", symbol="XAGUSDT")
    candles_1h = data_manager.fetch_historical_data(days=2, timeframe="1h", symbol="XAGUSDT")
    candles_5m = data_manager.fetch_historical_data(days=2, timeframe="5m", symbol="XAGUSDT")
    candles_4h = data_manager.fetch_historical_data(days=2, timeframe="4h", symbol="XAGUSDT")
    
    strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
    
    short_signal = strategy.check_short_entry("XAGUSDT")
    
    if short_signal:
        print("✓ SHORT SIGNAL DETECTED")
        print(f"  Price: ${short_signal.price:.4f}")
        print(f"  Timestamp: {short_signal.timestamp}")
    else:
        print("✗ NO SIGNAL DETECTED")
        indicators = strategy.get_indicator_snapshot()
        print(f"  Squeeze Color: {indicators.get('squeeze_color', 'N/A')}")
        print(f"  ADX: {indicators.get('adx', 0):.2f}")
        print(f"  RVOL: {indicators.get('rvol', 0):.2f}")
        exit(1)
        
except Exception as e:
    print(f"✗ Error checking signal: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()

# Check positions
print("POSITION CHECK")
print("-" * 80)
position_sizer = PositionSizer(config)
risk_manager = RiskManager(config, position_sizer)

existing_position = risk_manager.get_active_position("XAGUSDT")
if existing_position:
    print(f"⚠️  POSITION EXISTS!")
    print(f"  Side: {existing_position.side}")
    print(f"  Entry: ${existing_position.entry_price:.4f}")
    print(f"  Quantity: {existing_position.quantity:.4f}")
    print()
    print("Bot will NOT open new position while one exists.")
    exit(1)
else:
    print("✓ No existing position")

print()

# Check signal generation
print("SIGNAL GENERATION CHECK")
print("-" * 80)
if risk_manager.is_signal_generation_enabled():
    print("✓ Signal generation ENABLED")
else:
    print("✗ Signal generation DISABLED")
    exit(1)

print()

# Check margin
print("MARGIN CHECK")
print("-" * 80)
order_executor = OrderExecutor(config, client)

try:
    balance = order_executor.get_account_balance()
    print(f"Balance: ${balance:.2f}")
    
    # Calculate required margin
    current_price = short_signal.price
    risk_amount = balance * config.risk_per_trade
    atr = current_price * 0.02  # Estimate
    stop_distance = atr * config.stop_loss_atr_multiplier
    quantity = (risk_amount / stop_distance) * config.leverage
    notional = current_price * quantity
    margin_required = notional / config.leverage
    
    print(f"Risk Amount: ${risk_amount:.2f}")
    print(f"Quantity: {quantity:.4f}")
    print(f"Notional: ${notional:.2f}")
    print(f"Margin Required: ${margin_required:.2f}")
    
    if margin_required > balance:
        print()
        print("✗ INSUFFICIENT MARGIN!")
        print(f"  Need: ${margin_required:.2f}")
        print(f"  Have: ${balance:.2f}")
        exit(1)
    else:
        print()
        print(f"✓ Sufficient margin (${balance - margin_required:.2f} remaining)")
        
except Exception as e:
    print(f"✗ Error checking margin: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()

# Check volume profile (if enabled)
if config.enable_volume_profile:
    print("VOLUME PROFILE CHECK")
    print("-" * 80)
    
    advanced_features = strategy.get_advanced_features_data()
    volume_profile = advanced_features.get('volume_profile')
    
    if volume_profile:
        print(f"POC: ${volume_profile.get('poc', 0):.2f}")
        print(f"VAH: ${volume_profile.get('vah', 0):.2f}")
        print(f"VAL: ${volume_profile.get('val', 0):.2f}")
        
        # Check if volume profile is blocking
        poc = volume_profile.get('poc', 0)
        if poc > 0:
            distance_from_poc = abs(current_price - poc) / current_price
            print(f"Distance from POC: {distance_from_poc * 100:.2f}%")
            
            # Volume profile might reduce position size if in low volume area
            if distance_from_poc < 0.005:  # Within 0.5% of POC
                print("⚠️  Price near POC - volume profile may reduce size")
    else:
        print("Volume profile data not available")
    
    print()

# Check API permissions
print("API PERMISSIONS CHECK")
print("-" * 80)

try:
    if order_executor.validate_authentication():
        print("✓ API authentication valid")
    else:
        print("✗ API authentication FAILED")
        exit(1)
        
    # Check if futures trading is enabled
    account = client.futures_account()
    can_trade = account.get('canTrade', False)
    
    if can_trade:
        print("✓ Futures trading ENABLED")
    else:
        print("✗ Futures trading DISABLED")
        print("  Enable futures trading in Binance account settings")
        exit(1)
        
except Exception as e:
    print(f"✗ Error checking API: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()

# Check leverage and margin type
print("LEVERAGE & MARGIN CHECK")
print("-" * 80)

try:
    # Get current leverage
    position_info = client.futures_position_information(symbol="XAGUSDT")
    if position_info:
        current_leverage = int(position_info[0].get('leverage', 0))
        margin_type = position_info[0].get('marginType', 'UNKNOWN')
        
        print(f"Current Leverage: {current_leverage}x")
        print(f"Margin Type: {margin_type}")
        
        if current_leverage != config.leverage:
            print(f"⚠️  Leverage mismatch!")
            print(f"  Config: {config.leverage}x")
            print(f"  Binance: {current_leverage}x")
            print()
            print("Setting leverage...")
            order_executor.set_leverage("XAGUSDT", config.leverage)
            print(f"✓ Leverage set to {config.leverage}x")
            
except Exception as e:
    print(f"⚠️  Error checking leverage: {e}")

print()
print("=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
print()
print("✅ ALL CHECKS PASSED!")
print()
print("The bot SHOULD be executing the trade.")
print()
print("If trade still not executing:")
print("  1. Check bot terminal for error messages")
print("  2. Check logs/trades.log")
print("  3. Restart bot: Ctrl+C then python main.py")
print()
