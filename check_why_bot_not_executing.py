"""Comprehensive check: Why is the bot not executing trades despite valid signals?"""

import psutil
from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer

print("=" * 80)
print("COMPREHENSIVE EXECUTION DIAGNOSTIC")
print("=" * 80)
print()

# Load config
config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)

print("STEP 1: Check Bot Process")
print("-" * 80)
bot_running = False
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info['cmdline']
        if cmdline:
            cmdline_str = ' '.join(cmdline)
            if 'python' in cmdline_str.lower() and ('main.py' in cmdline_str or 'start_paper_trading.py' in cmdline_str):
                print(f"✓ Bot is RUNNING (PID: {proc.info['pid']})")
                bot_running = True
                break
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

if not bot_running:
    print("✗ Bot is NOT RUNNING")
    print()
    print("⚠️  THE BOT MUST BE RUNNING TO EXECUTE TRADES!")
    print()
    print("To start the bot:")
    print("  python main.py")
    print()
    print("=" * 80)
    exit(0)

print()
print("STEP 2: Check Current Signals")
print("-" * 80)

data_manager = DataManager(config, client)
strategy = StrategyEngine(config)

signals_found = []

for symbol in config.portfolio_symbols:
    try:
        candles_15m = data_manager.fetch_historical_data(days=2, timeframe="15m", symbol=symbol)
        candles_1h = data_manager.fetch_historical_data(days=2, timeframe="1h", symbol=symbol)
        candles_5m = data_manager.fetch_historical_data(days=2, timeframe="5m", symbol=symbol)
        candles_4h = data_manager.fetch_historical_data(days=2, timeframe="4h", symbol=symbol)
        
        strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
        
        long_signal = strategy.check_long_entry(symbol)
        short_signal = strategy.check_short_entry(symbol)
        
        if long_signal:
            print(f"✓ {symbol}: LONG SIGNAL ACTIVE")
            signals_found.append((symbol, "LONG"))
        elif short_signal:
            print(f"✓ {symbol}: SHORT SIGNAL ACTIVE")
            signals_found.append((symbol, "SHORT"))
        else:
            indicators = strategy.get_indicator_snapshot()
            print(f"  {symbol}: No signal (RVOL={indicators['rvol']:.2f}, ADX={indicators['adx']:.1f}, Squeeze={indicators['squeeze_color']})")
    except Exception as e:
        print(f"  {symbol}: Error - {e}")

print()
if not signals_found:
    print("✗ NO SIGNALS CURRENTLY ACTIVE")
    print()
    print("⚠️  MARKET CONDITIONS CHANGED - NO VALID SIGNALS EXIST!")
    print()
    print("Signals are dynamic and change every minute as:")
    print("  - Price moves relative to VWAP")
    print("  - Momentum changes (squeeze color)")
    print("  - Volume changes (RVOL)")
    print("  - Trend changes (ADX)")
    print()
    print("The SHORT signal you saw earlier is no longer valid.")
    print("The bot will execute trades when new signals appear.")
    print()
    print("=" * 80)
    exit(0)

print(f"✓ Found {len(signals_found)} active signal(s)")
print()

print("STEP 3: Check Existing Positions")
print("-" * 80)

position_sizer = PositionSizer(config)
risk_manager = RiskManager(config, position_sizer)

for symbol, signal_type in signals_found:
    existing_position = risk_manager.get_active_position(symbol)
    if existing_position:
        print(f"⚠️  {symbol}: Position already exists ({existing_position.side} @ ${existing_position.entry_price:.4f})")
        print(f"    Bot will NOT open new position while one exists")
    else:
        print(f"✓ {symbol}: No existing position - ready for entry")

print()
print("STEP 4: Check Signal Generation Status")
print("-" * 80)

if risk_manager.is_signal_generation_enabled():
    print("✓ Signal generation is ENABLED")
else:
    print("✗ Signal generation is DISABLED")
    print("  Bot will NOT open new positions")

print()
print("STEP 5: Check Configuration")
print("-" * 80)
print(f"Run Mode: {config.run_mode}")
print(f"Symbol: {config.symbol}")
print(f"Portfolio Management: {'ENABLED' if config.enable_portfolio_management else 'DISABLED'}")
print(f"Multi-Timeframe: {'ENABLED' if config.enable_multi_timeframe else 'DISABLED'}")
print(f"Regime Detection: {'ENABLED' if config.enable_regime_detection else 'DISABLED'}")
print(f"ADX Threshold: {config.adx_threshold}")
print(f"RVOL Threshold: {config.rvol_threshold}")

print()
print("=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)
print()

if bot_running and signals_found and risk_manager.is_signal_generation_enabled():
    print("✅ BOT SHOULD BE EXECUTING TRADES!")
    print()
    print("If trades are still not executing, check:")
    print("  1. Bot terminal output for error messages")
    print("  2. logs/trades.log for execution errors")
    print("  3. Binance API permissions (futures trading enabled)")
    print("  4. Sufficient balance for margin requirements")
    print()
    print("The bot processes signals every 60 seconds.")
    print("Wait 1-2 minutes and check if position opens.")
else:
    print("⚠️  BOT CANNOT EXECUTE TRADES")
    print()
    if not bot_running:
        print("  Reason: Bot is not running")
    elif not signals_found:
        print("  Reason: No valid signals exist")
    elif not risk_manager.is_signal_generation_enabled():
        print("  Reason: Signal generation is disabled")

print()
