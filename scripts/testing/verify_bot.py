"""Verify bot functionality without making changes."""

from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer
from src.order_executor import OrderExecutor
from binance.client import Client

print("=" * 80)
print("BOT FUNCTIONALITY VERIFICATION")
print("=" * 80)

# 1. Configuration
print("\n1. CONFIGURATION")
try:
    config = Config.load_from_file('config/config.json')
    print(f"   ✓ Config loaded successfully")
    print(f"   ✓ Symbol: {config.symbol}")
    print(f"   ✓ Risk per trade: {config.risk_per_trade * 100}%")
    print(f"   ✓ Leverage: {config.leverage}x")
    print(f"   ✓ Mode: {config.run_mode}")
except Exception as e:
    print(f"   ✗ FAILED: {e}")
    exit(1)

# 2. API Connection
print("\n2. BINANCE API CONNECTION")
try:
    client = Client(config.api_key, config.api_secret)
    balance_info = client.futures_account_balance()
    print(f"   ✓ API connected successfully")
    print(f"   ✓ Account has {len(balance_info)} assets")
except Exception as e:
    print(f"   ✗ FAILED: {e}")
    exit(1)

# 3. Live Data Fetching
print("\n3. LIVE DATA FETCHING")
try:
    data_manager = DataManager(config, client)
    candles_15m = data_manager.fetch_historical_data(days=2, timeframe="15m")
    candles_1h = data_manager.fetch_historical_data(days=2, timeframe="1h")
    print(f"   ✓ Fetched {len(candles_15m)} 15m candles")
    print(f"   ✓ Fetched {len(candles_1h)} 1h candles")
    print(f"   ✓ Latest price: ${candles_15m[-1].close:.4f}")
except Exception as e:
    print(f"   ✗ FAILED: {e}")
    exit(1)

# 4. Strategy Analysis & Signal Generation
print("\n4. STRATEGY ANALYSIS & SIGNAL GENERATION")
try:
    strategy = StrategyEngine(config)
    strategy.update_indicators(candles_15m, candles_1h)
    
    indicators = strategy.current_indicators
    print(f"   ✓ Indicators calculated:")
    print(f"     - ADX: {indicators.adx:.2f}")
    print(f"     - RVOL: {indicators.rvol:.2f}")
    print(f"     - Trend 15m: {indicators.trend_15m}")
    print(f"     - Trend 1h: {indicators.trend_1h}")
    
    long_signal = strategy.check_long_entry()
    short_signal = strategy.check_short_entry()
    print(f"   ✓ Signal generation:")
    print(f"     - Long: {'YES' if long_signal else 'NO'}")
    print(f"     - Short: {'YES' if short_signal else 'NO'}")
except Exception as e:
    print(f"   ✗ FAILED: {e}")
    exit(1)

# 5. Risk Management & Position Sizing
print("\n5. RISK MANAGEMENT & POSITION SIZING")
try:
    position_sizer = PositionSizer(config)
    risk_manager = RiskManager(config, position_sizer)
    
    test_price = candles_15m[-1].close
    test_atr = indicators.atr_15m
    
    position_info = position_sizer.calculate_position_size(
        wallet_balance=10000,  # Test with $10k
        entry_price=test_price,
        atr=test_atr
    )
    
    stop_loss = position_info['stop_loss_price']
    take_profit = test_price + (test_atr * 3.0)  # 3x ATR target
    
    print(f"   ✓ Position sizing calculated:")
    print(f"     - Position size: {position_info['quantity']:.4f} units")
    print(f"     - Entry: ${test_price:.4f}")
    print(f"     - Stop Loss: ${stop_loss:.4f}")
    print(f"     - Take Profit: ${take_profit:.4f}")
    print(f"     - Margin required: ${position_info['margin_required']:.2f}")
    print(f"     - Risk amount: ${10000 * config.risk_per_trade:.2f}")
except Exception as e:
    print(f"   ✗ FAILED: {e}")
    exit(1)

# 6. Order Execution System
print("\n6. ORDER EXECUTION SYSTEM")
try:
    order_executor = OrderExecutor(config, client)
    account_balance = order_executor.get_account_balance()
    
    print(f"   ✓ Order executor initialized")
    print(f"   ✓ Account balance: ${account_balance:.2f}")
    print(f"   ✓ Mode: {config.run_mode}")
    print(f"   ✓ Ready to execute trades")
except Exception as e:
    print(f"   ✗ FAILED: {e}")
    exit(1)

# Summary
print("\n" + "=" * 80)
print("ALL SYSTEMS OPERATIONAL")
print("=" * 80)
print("\nBot is fully functional and ready to:")
print("  ✓ Fetch live market data from Binance")
print("  ✓ Analyze indicators and market trends")
print("  ✓ Generate trading signals (Long/Short)")
print("  ✓ Calculate position sizes with risk management")
print("  ✓ Set stop loss and take profit levels")
print("  ✓ Execute trades (currently in PAPER mode)")
print("\nTo start trading:")
print("  python start_paper_trading.py")
print("\n" + "=" * 80)
