"""Comprehensive diagnostic script to identify why signals aren't being executed."""

import sys
import logging
from binance.client import Client

from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer
from src.order_executor import OrderExecutor
from src.portfolio_manager import PortfolioManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("=" * 80)
    print("Signal Execution Diagnostic Tool")
    print("=" * 80)
    
    # Load config
    config = Config.load_from_file()
    print(f"\n✓ Config loaded: {config.run_mode} mode")
    print(f"  Symbols: {config.portfolio_symbols if config.enable_portfolio_management else [config.symbol]}")
    print(f"  Portfolio management: {config.enable_portfolio_management}")
    print(f"  Multi-timeframe: {config.enable_multi_timeframe}")
    
    # Initialize client
    client = Client(config.api_key, config.api_secret)
    print("\n✓ Binance client initialized")
    
    # Initialize components
    data_manager = DataManager(config, client)
    strategy = StrategyEngine(config)
    position_sizer = PositionSizer(config)
    risk_manager = RiskManager(config, position_sizer)
    order_executor = OrderExecutor(config, client)
    
    # Check authentication
    print("\n--- Authentication Check ---")
    if order_executor.validate_authentication():
        print("✓ API authentication successful")
    else:
        print("✗ API authentication FAILED")
        return
    
    # Get balance
    try:
        balance = order_executor.get_account_balance()
        print(f"✓ Account balance: ${balance:.2f} USDT")
    except Exception as e:
        print(f"✗ Failed to get balance: {e}")
        return
    
    # Initialize portfolio manager if enabled
    portfolio_manager = None
    if config.enable_portfolio_management:
        portfolio_manager = PortfolioManager(config)
        print(f"\n✓ Portfolio Manager initialized")
        print(f"  Max total risk: {config.portfolio_max_total_risk:.0%}")
        print(f"  Max single allocation: {config.portfolio_max_single_allocation:.0%}")
    
    # Get trading symbols
    symbols = config.portfolio_symbols if config.enable_portfolio_management else [config.symbol]
    
    print(f"\n--- Checking {len(symbols)} Symbol(s) ---")
    
    for symbol in symbols:
        print(f"\n{'=' * 80}")
        print(f"Symbol: {symbol}")
        print(f"{'=' * 80}")
        
        # Fetch data
        try:
            print(f"Fetching data for {symbol}...")
            candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
            candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
            
            candles_5m = None
            candles_4h = None
            if config.enable_multi_timeframe:
                candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol)
                candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol)
            
            print(f"✓ Data fetched: 15m={len(candles_15m)}, 1h={len(candles_1h)}, " +
                  f"5m={len(candles_5m) if candles_5m else 0}, 4h={len(candles_4h) if candles_4h else 0}")
        except Exception as e:
            print(f"✗ Failed to fetch data: {e}")
            continue
        
        # Check data sufficiency
        print("\n--- Data Sufficiency Check ---")
        if len(candles_15m) < 50:
            print(f"✗ Insufficient 15m data: {len(candles_15m)} < 50")
            continue
        else:
            print(f"✓ Sufficient 15m data: {len(candles_15m)} candles")
        
        if len(candles_1h) < 30:
            print(f"✗ Insufficient 1h data: {len(candles_1h)} < 30")
            continue
        else:
            print(f"✓ Sufficient 1h data: {len(candles_1h)} candles")
        
        # Update indicators
        print("\n--- Indicator Calculation ---")
        try:
            strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
            print("✓ Indicators updated successfully")
            
            # Display key indicators
            indicators = strategy.current_indicators
            print(f"  ADX: {indicators.adx:.2f}")
            print(f"  RVOL: {indicators.rvol:.2f}")
            print(f"  ATR 15m: {indicators.atr_15m:.4f}")
            print(f"  ATR 1h: {indicators.atr_1h:.4f}")
            print(f"  Trend 15m: {indicators.trend_15m}")
            print(f"  Trend 1h: {indicators.trend_1h}")
            print(f"  Price: ${indicators.current_price:.2f}")
            print(f"  Price vs VWAP: {indicators.price_vs_vwap}")
        except Exception as e:
            print(f"✗ Failed to update indicators: {e}")
            continue
        
        # Check signal generation enabled
        print("\n--- Signal Generation Check ---")
        if risk_manager.is_signal_generation_enabled():
            print("✓ Signal generation is ENABLED")
        else:
            print("✗ Signal generation is DISABLED (panic close triggered?)")
            continue
        
        # Check for active position
        print("\n--- Position Check ---")
        active_position = risk_manager.get_active_position(symbol)
        if active_position:
            print(f"⚠ Active position exists: {active_position.side} @ ${active_position.entry_price:.2f}")
            print(f"  Quantity: {active_position.quantity}")
            print(f"  Leverage: {active_position.leverage}x")
            continue
        else:
            print("✓ No active position - ready for new signals")
        
        # Check for signals
        print("\n--- Signal Detection ---")
        try:
            long_signal = strategy.check_long_entry(symbol)
            short_signal = strategy.check_short_entry(symbol)
            
            if long_signal:
                print(f"✓ LONG SIGNAL DETECTED")
                print(f"  Confidence: {long_signal.confidence:.2f}")
                print(f"  Price: ${long_signal.price:.2f}")
            elif short_signal:
                print(f"✓ SHORT SIGNAL DETECTED")
                print(f"  Confidence: {short_signal.confidence:.2f}")
                print(f"  Price: ${short_signal.price:.2f}")
            else:
                print("○ No signal detected")
                continue
            
            signal = long_signal or short_signal
            
            # Check portfolio risk limits
            if portfolio_manager:
                print("\n--- Portfolio Risk Check ---")
                if not portfolio_manager.check_total_risk(balance):
                    print("✗ BLOCKED: Portfolio total risk limit exceeded")
                    print(f"  Current risk: {portfolio_manager.get_total_risk():.2%}")
                    print(f"  Max allowed: {config.portfolio_max_total_risk:.0%}")
                    continue
                else:
                    print("✓ Portfolio total risk within limits")
            
            # Calculate position size
            print("\n--- Position Sizing ---")
            try:
                atr = strategy.current_indicators.atr_15m
                position = risk_manager.open_position(signal, balance, atr)
                print(f"✓ Position calculated:")
                print(f"  Symbol: {position.symbol}")
                print(f"  Side: {position.side}")
                print(f"  Entry: ${position.entry_price:.2f}")
                print(f"  Quantity: {position.quantity}")
                print(f"  Leverage: {position.leverage}x")
                print(f"  Stop loss: ${position.stop_loss:.2f}")
                
                # Check if portfolio manager allows this position
                if portfolio_manager:
                    print("\n--- Portfolio Position Check ---")
                    if portfolio_manager.can_add_position(symbol, position, balance):
                        print("✓ Portfolio manager ALLOWS this position")
                    else:
                        print("✗ BLOCKED: Portfolio manager REJECTS this position")
                        print(f"  Would exceed portfolio risk limits")
                        # Close the test position
                        risk_manager.close_position(position, position.entry_price, "TEST")
                        continue
                
                # Check margin availability
                print("\n--- Margin Check ---")
                margin_required = (position.entry_price * position.quantity) / position.leverage
                print(f"  Margin required: ${margin_required:.2f}")
                print(f"  Available balance: ${balance:.2f}")
                
                if order_executor.validate_margin_availability(symbol, margin_required):
                    print("✓ Sufficient margin available")
                else:
                    print("✗ BLOCKED: Insufficient margin")
                    # Close the test position
                    risk_manager.close_position(position, position.entry_price, "TEST")
                    continue
                
                # If we got here, the trade SHOULD execute
                print("\n" + "=" * 80)
                print("✓✓✓ ALL CHECKS PASSED - TRADE SHOULD EXECUTE ✓✓✓")
                print("=" * 80)
                
                # Close the test position
                risk_manager.close_position(position, position.entry_price, "TEST")
                
            except Exception as e:
                print(f"✗ Failed to calculate position: {e}")
                import traceback
                traceback.print_exc()
                continue
            
        except Exception as e:
            print(f"✗ Failed to check signals: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "=" * 80)
    print("Diagnostic Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()
