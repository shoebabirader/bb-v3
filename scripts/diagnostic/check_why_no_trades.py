"""Check why the bot isn't generating trading signals."""

import logging
from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Check trading signals for all portfolio symbols."""
    print("=" * 80)
    print("Trading Signal Analysis")
    print("=" * 80)
    
    # Load config
    config = Config.load_from_file()
    
    # Initialize client and data manager
    client = Client(config.api_key, config.api_secret)
    data_manager = DataManager(config, client)
    
    # Initialize strategy
    strategy = StrategyEngine(config)
    
    # Get symbols to check
    if config.enable_portfolio_management:
        symbols = config.portfolio_symbols
    else:
        symbols = [config.symbol]
    
    print(f"\nChecking {len(symbols)} symbol(s) for trading signals...\n")
    
    for symbol in symbols:
        print(f"--- {symbol} ---")
        
        try:
            # Fetch data
            candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
            candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)
            candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m", symbol=symbol) if config.enable_multi_timeframe else None
            candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h", symbol=symbol) if config.enable_multi_timeframe else None
            
            # Update indicators
            strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
            
            # Get current indicators
            ind = strategy.current_indicators
            
            print(f"Current Price: ${candles_15m[-1].close:.4f}")
            print(f"  ADX: {ind.adx:.2f} (threshold: {config.adx_threshold})")
            print(f"  RVOL: {ind.rvol:.2f} (threshold: {config.rvol_threshold})")
            print(f"  Squeeze Value: {ind.squeeze_value:.4f}")
            print(f"  Squeeze Color: {ind.squeeze_color}")
            print(f"  Is Squeezed: {ind.is_squeezed}")
            print(f"  Trend 15m: {ind.trend_15m}")
            print(f"  Trend 1h: {ind.trend_1h}")
            print(f"  Price vs VWAP: {ind.price_vs_vwap}")
            
            # Check signals
            long_signal = strategy.check_long_entry()
            short_signal = strategy.check_short_entry()
            
            if long_signal:
                print(f"  ✓ LONG SIGNAL DETECTED")
                print(f"    Reason: {long_signal.reason}")
                print(f"    Confidence: {long_signal.confidence:.2f}")
            elif short_signal:
                print(f"  ✓ SHORT SIGNAL DETECTED")
                print(f"    Reason: {short_signal.reason}")
                print(f"    Confidence: {short_signal.confidence:.2f}")
            else:
                print(f"  ✗ No signal")
                
                # Explain why
                reasons = []
                if ind.adx < config.adx_threshold:
                    reasons.append(f"ADX too low ({ind.adx:.2f} < {config.adx_threshold})")
                if ind.rvol < config.rvol_threshold:
                    reasons.append(f"RVOL too low ({ind.rvol:.2f} < {config.rvol_threshold})")
                if ind.trend_15m not in ["BULLISH", "BEARISH"]:
                    reasons.append(f"No clear trend (15m: {ind.trend_15m}, 1h: {ind.trend_1h})")
                if ind.squeeze_value == 0:
                    reasons.append(f"No momentum (squeeze value: {ind.squeeze_value:.4f})")
                
                if reasons:
                    print(f"    Reasons:")
                    for reason in reasons:
                        print(f"      - {reason}")
            
            print()
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            print()
    
    print("=" * 80)
    print("Analysis Complete")
    print("=" * 80)
    print("\nNOTE: Trading bots don't trade constantly. They wait for:")
    print("  1. Strong trend (ADX > threshold)")
    print("  2. High volume (RVOL > threshold)")
    print("  3. Momentum setup (Squeeze, RSI, etc.)")
    print("\nIf no signals are found, the market conditions aren't right for trading.")
    print("This is NORMAL and EXPECTED behavior.")

if __name__ == "__main__":
    main()
