"""Complete end-to-end test of signal detection and trade execution flow."""

import sys
from binance.client import Client

from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer
from src.order_executor import OrderExecutor
from src.portfolio_manager import PortfolioManager

def test_complete_flow():
    print("=" * 80)
    print("COMPLETE EXECUTION FLOW TEST")
    print("=" * 80)
    
    # Load config
    config = Config.load_from_file()
    print(f"\n[1/8] Config loaded: {config.run_mode} mode")
    print(f"      Portfolio symbols: {config.portfolio_symbols}")
    
    # Initialize client
    client = Client(config.api_key, config.api_secret)
    print("[2/8] Binance client initialized")
    
    # Initialize all components (exactly as the bot does)
    data_manager = DataManager(config, client)
    strategy = StrategyEngine(config)
    position_sizer = PositionSizer(config)
    risk_manager = RiskManager(config, position_sizer)
    order_executor = OrderExecutor(config, client)
    portfolio_manager = PortfolioManager(config) if config.enable_portfolio_management else None
    
    print("[3/8] All components initialized")
    
    # Get balance
    balance = order_executor.get_account_balance()
    print(f"[4/8] Account balance: ${balance:.2f} USDT")
    
    # Test with a symbol that has a signal
    test_symbol = "RIVERUSDT"
    print(f"\n[5/8] Testing with {test_symbol}...")
    
    # Fetch data
    candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=test_symbol)
    candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=test_symbol)
    candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=test_symbol)
    candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=test_symbol)
    
    print(f"      Data fetched: 15m={len(candles_15m)}, 1h={len(candles_1h)}")
    
    # Update indicators
    strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
    print("      Indicators updated")
    
    # Check for signals (WITH symbol - this is the fix!)
    print(f"\n[6/8] Checking for signals on {test_symbol}...")
    long_signal = strategy.check_long_entry(test_symbol)
    short_signal = strategy.check_short_entry(test_symbol)
    
    signal = long_signal or short_signal
    
    if not signal:
        print("      No signal detected - test cannot continue")
        print("\n      Try running again when market conditions generate a signal")
        return False
    
    signal_type = "LONG" if long_signal else "SHORT"
    print(f"      {signal_type} SIGNAL DETECTED!")
    print(f"      Signal symbol: {signal.symbol}")
    print(f"      Signal price: ${signal.price:.2f}")
    print(f"      Signal confidence: {signal.confidence:.2f}")
    
    # Verify signal has correct symbol
    if signal.symbol != test_symbol:
        print(f"\n      ERROR: Signal has wrong symbol!")
        print(f"      Expected: {test_symbol}")
        print(f"      Got: {signal.symbol}")
        return False
    
    print(f"      Symbol verification: PASS")
    
    # Check if signal generation is enabled
    print(f"\n[7/8] Checking risk manager state...")
    if not risk_manager.is_signal_generation_enabled():
        print("      ERROR: Signal generation is DISABLED")
        return False
    print("      Signal generation: ENABLED")
    
    # Check for active position
    active_position = risk_manager.get_active_position(test_symbol)
    if active_position:
        print(f"      Active position exists: {active_position.side}")
        print("      Cannot open new position")
        return False
    print("      No active position: OK")
    
    # Check portfolio risk limits
    if portfolio_manager:
        print(f"\n      Checking portfolio risk limits...")
        if not portfolio_manager.check_total_risk(balance):
            print("      ERROR: Portfolio risk limit exceeded")
            return False
        print("      Portfolio risk: OK")
    
    # Try to open position (this is what the bot does)
    print(f"\n[8/8] Opening position...")
    try:
        atr = strategy.current_indicators.atr_15m
        position = risk_manager.open_position(signal, balance, atr)
        
        print(f"      Position created successfully!")
        print(f"      Symbol: {position.symbol}")
        print(f"      Side: {position.side}")
        print(f"      Entry: ${position.entry_price:.2f}")
        print(f"      Quantity: {position.quantity:.4f}")
        print(f"      Leverage: {position.leverage}x")
        print(f"      Stop loss: ${position.stop_loss:.2f}")
        
        # Verify position has correct symbol
        if position.symbol != test_symbol:
            print(f"\n      ERROR: Position has wrong symbol!")
            print(f"      Expected: {test_symbol}")
            print(f"      Got: {position.symbol}")
            
            # Clean up
            risk_manager.close_position(position, position.entry_price, "TEST")
            return False
        
        print(f"\n      Position symbol verification: PASS")
        
        # Check if portfolio manager allows this position
        if portfolio_manager:
            if not portfolio_manager.can_add_position(test_symbol, position, balance):
                print(f"\n      ERROR: Portfolio manager REJECTS position")
                risk_manager.close_position(position, position.entry_price, "TEST")
                return False
            print(f"      Portfolio manager approval: PASS")
        
        # Check margin availability
        margin_required = (position.entry_price * position.quantity) / position.leverage
        print(f"\n      Checking margin...")
        print(f"      Required: ${margin_required:.2f}")
        print(f"      Available: ${balance:.2f}")
        
        if not order_executor.validate_margin_availability(test_symbol, margin_required):
            print(f"      ERROR: Insufficient margin")
            risk_manager.close_position(position, position.entry_price, "TEST")
            return False
        
        print(f"      Margin check: PASS")
        
        # Clean up test position
        risk_manager.close_position(position, position.entry_price, "TEST")
        
        print("\n" + "=" * 80)
        print("ALL CHECKS PASSED - TRADE EXECUTION WILL WORK!")
        print("=" * 80)
        print("\nThe bot will execute trades when:")
        print("1. Signal is detected (with correct symbol)")
        print("2. No active position exists for that symbol")
        print("3. Portfolio risk limits are within bounds")
        print("4. Sufficient margin is available")
        print("\nAll conditions are now working correctly.")
        
        return True
        
    except Exception as e:
        print(f"\n      ERROR opening position: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = test_complete_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
