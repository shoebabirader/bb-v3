"""Diagnose why signals are detected but not executing in LIVE mode."""
import json
from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer

print("="*70)
print("LIVE TRADING SIGNAL DIAGNOSIS")
print("="*70)

# Load config
config = Config.load_from_file('config/config.json')
print(f"\n1. Configuration:")
print(f"   Run Mode: {config.run_mode}")
print(f"   Portfolio Enabled: {config.enable_portfolio_management}")
print(f"   Symbols: {config.portfolio_symbols if config.enable_portfolio_management else [config.symbol]}")
print(f"   Risk per trade: {config.risk_per_trade * 100}%")
print(f"   ADX Threshold: {config.adx_threshold}")
print(f"   RVOL Threshold: {config.rvol_threshold}")

# Initialize components
client = Client(config.api_key, config.api_secret)
data_manager = DataManager(config, client)

# Check each symbol
symbols = config.portfolio_symbols if config.enable_portfolio_management else [config.symbol]

for symbol in symbols:
    print(f"\n{'='*70}")
    print(f"Checking {symbol}")
    print(f"{'='*70}")
    
    try:
        # Update config for this symbol
        config.symbol = symbol
        
        # Create strategy
        strategy = StrategyEngine(config)
        
        # Fetch data
        print(f"\n2. Fetching data...")
        candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
        candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
        
        print(f"   15m candles: {len(candles_15m)}")
        print(f"   1h candles: {len(candles_1h)}")
        
        # Update indicators
        print(f"\n3. Updating indicators...")
        strategy.update_indicators(candles_15m, candles_1h)
        
        # Get current indicators
        indicators = strategy.current_indicators
        print(f"   ADX: {indicators.adx:.2f} (threshold: {config.adx_threshold})")
        print(f"   RVOL: {indicators.rvol:.2f} (threshold: {config.rvol_threshold})")
        print(f"   ATR: {indicators.atr_15m:.6f}")
        print(f"   EMA 20: {indicators.ema_20:.4f}")
        print(f"   EMA 50: {indicators.ema_50:.4f}")
        
        # Check signals
        print(f"\n4. Checking signals...")
        long_signal = strategy.check_long_entry()
        short_signal = strategy.check_short_entry()
        
        print(f"   LONG signal: {long_signal is not None}")
        print(f"   SHORT signal: {short_signal is not None}")
        
        if long_signal:
            print(f"   ✓ LONG SIGNAL DETECTED!")
            print(f"     Entry: {long_signal.entry_price:.4f}")
            print(f"     Stop: {long_signal.stop_loss:.4f}")
        
        if short_signal:
            print(f"   ✓ SHORT SIGNAL DETECTED!")
            print(f"     Entry: {short_signal.entry_price:.4f}")
            print(f"     Stop: {short_signal.stop_loss:.4f}")
        
        if not long_signal and not short_signal:
            print(f"   ⚠ No signals detected")
            
            # Check why
            print(f"\n5. Signal blocking reasons:")
            
            # Check ADX
            if indicators.adx < config.adx_threshold:
                print(f"   ✗ ADX too low: {indicators.adx:.2f} < {config.adx_threshold}")
            else:
                print(f"   ✓ ADX OK: {indicators.adx:.2f} >= {config.adx_threshold}")
            
            # Check RVOL
            if indicators.rvol < config.rvol_threshold:
                print(f"   ✗ RVOL too low: {indicators.rvol:.2f} < {config.rvol_threshold}")
            else:
                print(f"   ✓ RVOL OK: {indicators.rvol:.2f} >= {config.rvol_threshold}")
            
            # Check trend
            if indicators.ema_20 > indicators.ema_50:
                print(f"   ✓ Uptrend: EMA20 ({indicators.ema_20:.4f}) > EMA50 ({indicators.ema_50:.4f})")
            elif indicators.ema_20 < indicators.ema_50:
                print(f"   ✓ Downtrend: EMA20 ({indicators.ema_20:.4f}) < EMA50 ({indicators.ema_50:.4f})")
            else:
                print(f"   ⚠ No clear trend: EMA20 ≈ EMA50")
        
        # Check if there are open positions
        print(f"\n6. Checking open positions...")
        try:
            positions = client.futures_position_information(symbol=symbol)
            for pos in positions:
                if float(pos['positionAmt']) != 0:
                    print(f"   ⚠ Open position: {pos['positionAmt']} @ {pos['entryPrice']}")
                    print(f"     Unrealized PnL: {pos['unRealizedProfit']}")
        except Exception as e:
            print(f"   Error checking positions: {e}")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*70}")
print("DIAGNOSIS COMPLETE")
print(f"{'='*70}")
