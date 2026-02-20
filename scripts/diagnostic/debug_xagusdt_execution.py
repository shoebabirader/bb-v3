"""Debug why XAGUSDT SHORT signal is not being executed."""

import sys
from src.config import Config
from src.strategy import StrategyEngine
from src.data_manager import DataManager
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer
from src.order_executor import OrderExecutor
from src.portfolio_manager import PortfolioManager
from binance.client import Client

def debug_xagusdt_execution():
    """Check the complete execution flow for XAGUSDT."""
    
    # Load config
    config = Config.load_from_file()
    
    # Initialize components
    client = Client(config.api_key, config.api_secret)
    data_manager = DataManager(config, client)
    strategy = StrategyEngine(config)
    position_sizer = PositionSizer(config)
    risk_manager = RiskManager(config, position_sizer)
    order_executor = OrderExecutor(config, client)
    portfolio_manager = PortfolioManager(config) if config.enable_portfolio_management else None
    
    symbol = "XAGUSDT"
    
    print("=" * 80)
    print(f"XAGUSDT EXECUTION DEBUG")
    print("=" * 80)
    
    # Step 1: Fetch data
    print(f"\n1. Fetching data for {symbol}...")
    candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
    candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
    candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol)
    candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol)
    print(f"   ✓ Data loaded: 15m={len(candles_15m)}, 1h={len(candles_1h)}, 5m={len(candles_5m)}, 4h={len(candles_4h)}")
    
    # Step 2: Update indicators
    print(f"\n2. Updating indicators...")
    strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
    print(f"   ✓ Indicators updated")
    
    # Step 3: Check for signal
    print(f"\n3. Checking for signal...")
    long_signal = strategy.check_long_entry(symbol)
    short_signal = strategy.check_short_entry(symbol)
    
    signal = long_signal or short_signal
    
    if not signal:
        print(f"   ✗ NO SIGNAL DETECTED")
        return
    
    print(f"   ✓ SIGNAL DETECTED: {signal.type}")
    print(f"   Signal symbol: {signal.symbol}")
    print(f"   Signal price: ${signal.price:.2f}")
    
    # Step 4: Check if already have position
    print(f"\n4. Checking for existing position...")
    existing_position = risk_manager.get_active_position(symbol)
    if existing_position:
        print(f"   ✗ ALREADY HAVE POSITION: {existing_position.side} at ${existing_position.entry_price:.2f}")
        return
    print(f"   ✓ No existing position")
    
    # Step 5: Check signal generation enabled
    print(f"\n5. Checking if signal generation is enabled...")
    if not risk_manager.is_signal_generation_enabled():
        print(f"   ✗ SIGNAL GENERATION DISABLED (panic mode)")
        return
    print(f"   ✓ Signal generation enabled")
    
    # Step 6: Get wallet balance
    print(f"\n6. Getting wallet balance...")
    try:
        wallet_balance = order_executor.get_account_balance()
        print(f"   ✓ Wallet balance: ${wallet_balance:.2f}")
    except Exception as e:
        print(f"   ✗ Failed to get balance: {e}")
        return
    
    # Step 7: Check portfolio risk limits (if enabled)
    if portfolio_manager:
        print(f"\n7. Checking portfolio risk limits...")
        
        # Check total risk
        can_trade = portfolio_manager.check_total_risk(wallet_balance)
        if not can_trade:
            print(f"   ✗ PORTFOLIO TOTAL RISK LIMIT EXCEEDED")
            print(f"   Current positions: {len(risk_manager.get_all_active_positions())}")
            print(f"   Max total risk: {config.portfolio_max_total_risk:.0%}")
            return
        print(f"   ✓ Total risk check passed")
        
        # Check if symbol is in portfolio
        if symbol not in portfolio_manager.symbols:
            print(f"   ✗ SYMBOL NOT IN PORTFOLIO")
            print(f"   Portfolio symbols: {portfolio_manager.symbols}")
            return
        print(f"   ✓ Symbol in portfolio")
    else:
        print(f"\n7. Portfolio management disabled, skipping portfolio checks")
    
    # Step 8: Calculate position size
    print(f"\n8. Calculating position size...")
    atr = strategy.current_indicators.atr_15m
    print(f"   ATR: ${atr:.4f}")
    
    try:
        sizing_result = position_sizer.calculate_position_size(
            wallet_balance=wallet_balance,
            entry_price=signal.price,
            atr=atr
        )
        print(f"   ✓ Position size calculated:")
        print(f"     Quantity: {sizing_result['quantity']:.4f}")
        print(f"     Stop distance: ${sizing_result['stop_loss_distance']:.4f}")
        print(f"     Risk amount: ${sizing_result['risk_amount']:.2f}")
    except Exception as e:
        print(f"   ✗ Failed to calculate position size: {e}")
        return
    
    # Step 9: Try to open position
    print(f"\n9. Attempting to open position...")
    try:
        position = risk_manager.open_position(signal, wallet_balance, atr)
        print(f"   ✓ POSITION OPENED:")
        print(f"     Symbol: {position.symbol}")
        print(f"     Side: {position.side}")
        print(f"     Entry: ${position.entry_price:.2f}")
        print(f"     Quantity: {position.quantity:.4f}")
        print(f"     Stop: ${position.stop_loss:.2f}")
        print(f"     Leverage: {position.leverage}x")
    except RuntimeError as e:
        print(f"   ✗ POSITION REJECTED: {e}")
        return
    except Exception as e:
        print(f"   ✗ ERROR OPENING POSITION: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 10: Check margin availability
    print(f"\n10. Checking margin availability...")
    margin_required = (position.entry_price * position.quantity) / position.leverage
    print(f"   Margin required: ${margin_required:.2f}")
    
    try:
        has_margin = order_executor.validate_margin_availability(symbol, margin_required)
        if not has_margin:
            print(f"   ✗ INSUFFICIENT MARGIN")
            # Close the position we just opened
            risk_manager.close_position(position, signal.price, "SIGNAL_EXIT")
            return
        print(f"   ✓ Sufficient margin available")
    except Exception as e:
        print(f"   ✗ Failed to check margin: {e}")
        return
    
    # Step 11: Execute order (simulation)
    print(f"\n11. Order execution (SIMULATION - not placing real order)...")
    side = "BUY" if position.side == "LONG" else "SELL"
    print(f"   Would execute: {side} {position.quantity:.4f} {symbol} @ market")
    print(f"   ✓ Order would be placed successfully")
    
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print(f"✓ Signal detected and position opened successfully!")
    print(f"✓ All checks passed - trade SHOULD execute in live bot")
    print(f"\nIf the live bot is NOT executing this trade, check:")
    print(f"1. Is the bot actually running?")
    print(f"2. Check bot logs for errors")
    print(f"3. Verify WebSocket is connected and receiving data")
    print(f"4. Check if there's already a position for {symbol}")

if __name__ == "__main__":
    try:
        debug_xagusdt_execution()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
