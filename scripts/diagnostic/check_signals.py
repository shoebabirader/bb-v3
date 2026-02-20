"""Quick script to check why signals aren't being generated - ALL PORTFOLIO SYMBOLS."""

from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from binance.client import Client

# Load config
config = Config.load_from_file()

# Create client
client = Client(config.api_key, config.api_secret)

# Get symbols from portfolio
symbols = config.portfolio_symbols if config.enable_portfolio_management else [config.symbol]

print(f"Checking {len(symbols)} symbol(s) for trading signals...")
print("=" * 80)

for symbol in symbols:
    print(f"\n--- {symbol} ---")
    
    # Create data manager for this symbol
    symbol_config = Config.load_from_file()
    symbol_config.symbol = symbol
    data_manager = DataManager(symbol_config, client)
    strategy = StrategyEngine(symbol_config)
    
    try:
        # Fetch data
        candles_15m = data_manager.fetch_historical_data(days=2, timeframe="15m")
        candles_1h = data_manager.fetch_historical_data(days=2, timeframe="1h")
        
        if not candles_15m or not candles_1h:
            print(f"✗ Error: Could not fetch data")
            continue
        
        # Update indicators
        strategy.update_indicators(candles_15m, candles_1h)
        
        # Print current indicator values
        indicators = strategy.current_indicators
        print(f"Current Price: ${indicators.current_price:.4f}")
        print(f"ADX: {indicators.adx:.2f} (threshold: {symbol_config.adx_threshold})")
        print(f"RVOL: {indicators.rvol:.2f} (threshold: {symbol_config.rvol_threshold})")
        print(f"Squeeze Value: {indicators.squeeze_value:.4f}")
        print(f"Squeeze Color: {indicators.squeeze_color}")
        print(f"Is Squeezed: {indicators.is_squeezed}")
        print(f"Trend 15m: {indicators.trend_15m}")
        print(f"Trend 1h: {indicators.trend_1h}")
        print(f"Price vs VWAP: {indicators.price_vs_vwap}")
        
        # Check entry conditions
        long_signal = strategy.check_long_entry()
        short_signal = strategy.check_short_entry()
        
        if long_signal:
            print(f"✓ LONG SIGNAL DETECTED")
        elif short_signal:
            print(f"✓ SHORT SIGNAL DETECTED")
        else:
            print(f"✗ No signal")
            
            # Identify blocking reasons
            reasons = []
            
            # Check long conditions
            if indicators.trend_15m == "BULLISH" and indicators.trend_1h == "BULLISH":
                if indicators.price_vs_vwap != "ABOVE":
                    reasons.append("Price not above VWAP")
                if indicators.squeeze_value <= 0:
                    reasons.append("Squeeze momentum not positive")
                if indicators.squeeze_color != "green":
                    reasons.append(f"Squeeze color not green (is {indicators.squeeze_color})")
                if indicators.adx <= symbol_config.adx_threshold:
                    reasons.append(f"ADX too low ({indicators.adx:.2f} < {symbol_config.adx_threshold})")
                if indicators.rvol <= symbol_config.rvol_threshold:
                    reasons.append(f"RVOL too low ({indicators.rvol:.2f} < {symbol_config.rvol_threshold})")
            
            # Check short conditions
            elif indicators.trend_15m == "BEARISH" and indicators.trend_1h == "BEARISH":
                if indicators.price_vs_vwap != "BELOW":
                    reasons.append("Price not below VWAP")
                if indicators.squeeze_value >= 0:
                    reasons.append("Squeeze momentum not negative")
                if indicators.squeeze_color != "maroon":
                    reasons.append(f"Squeeze color not maroon (is {indicators.squeeze_color})")
                if indicators.adx <= symbol_config.adx_threshold:
                    reasons.append(f"ADX too low ({indicators.adx:.2f} < {symbol_config.adx_threshold})")
                if indicators.rvol <= symbol_config.rvol_threshold:
                    reasons.append(f"RVOL too low ({indicators.rvol:.2f} < {symbol_config.rvol_threshold})")
            else:
                reasons.append(f"Trends not aligned (15m: {indicators.trend_15m}, 1h: {indicators.trend_1h})")
            
            if reasons:
                print("Reasons:")
                for reason in reasons:
                    print(f"  - {reason}")
    
    except Exception as e:
        print(f"✗ Error: {e}")

print("\n" + "=" * 80)
print("Analysis Complete")
print("=" * 80)
print("\nNOTE: Trading bots don't trade constantly. They wait for:")
print("1. Strong trend (ADX > threshold)")
print("2. High volume (RVOL > threshold)")
print("3. Momentum setup (Squeeze, RSI, etc.)")
print("\nIf no signals are found, the market conditions aren't right for trading.")
print("This is NORMAL and EXPECTED behavior.")
