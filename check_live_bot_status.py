"""Check why live bot is not executing trades."""

import sys
from src.config import Config
from src.strategy import StrategyEngine
from src.data_manager import DataManager
from src.portfolio_manager import PortfolioManager
from binance.client import Client

def main():
    print("=" * 80)
    print("LIVE BOT STATUS CHECK")
    print("=" * 80)
    
    # Load config
    config = Config.load_from_file('config/config.json')
    print(f"\n✓ Config loaded: {config.run_mode} mode")
    print(f"  Risk per trade: {config.risk_per_trade}%")
    print(f"  Portfolio symbols: {config.portfolio_symbols}")
    print(f"  Portfolio max total risk: {config.portfolio_max_total_risk * 100}%")
    
    # Initialize client
    client = Client(config.api_key, config.api_secret)
    
    # Check account balance
    try:
        account = client.futures_account()
        balance = float(account['totalWalletBalance'])
        print(f"\n✓ Account balance: ${balance:.2f} USDT")
    except Exception as e:
        print(f"\n✗ Error getting balance: {e}")
        return
    
    # Check portfolio manager
    if config.enable_portfolio_management:
        portfolio_mgr = PortfolioManager(config)
        print(f"\n✓ Portfolio management enabled")
        print(f"  Max total risk: {config.portfolio_max_total_risk * 100}%")
        print(f"  Max single allocation: {config.portfolio_max_single_allocation * 100}%")
        
        # Check if we can open positions
        for symbol in config.portfolio_symbols:
            position_size = balance * config.risk_per_trade / 100
            can_open, reason = portfolio_mgr.can_add_position(symbol, position_size, balance)
            status = "✓" if can_open else "✗"
            print(f"  {status} {symbol}: {reason if not can_open else 'Can open position'}")
    
    # Check for signals on each symbol
    print(f"\n" + "=" * 80)
    print("CHECKING SIGNALS FOR EACH SYMBOL")
    print("=" * 80)
    
    data_manager = DataManager(config, client)
    strategy = StrategyEngine(config)
    
    for symbol in config.portfolio_symbols:
        print(f"\n--- {symbol} ---")
        
        try:
            # Fetch recent data
            candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
            candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
            
            if config.enable_multi_timeframe:
                candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol)
                candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol)
            else:
                candles_5m = None
                candles_4h = None
            
            # Check for signal
            signal = strategy.generate_signal(
                candles_15m=candles_15m,
                candles_1h=candles_1h,
                candles_5m=candles_5m,
                candles_4h=candles_4h,
                symbol=symbol
            )
            
            if signal:
                print(f"✓ {signal.direction} SIGNAL DETECTED")
                print(f"  Entry: ${signal.entry_price:.4f}")
                print(f"  Stop Loss: ${signal.stop_loss:.4f}")
                print(f"  Confidence: {signal.confidence:.2f}")
            else:
                print(f"✗ No signal")
                
        except Exception as e:
            print(f"✗ Error: {e}")

if __name__ == "__main__":
    main()
