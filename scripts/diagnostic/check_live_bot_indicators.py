"""Check what indicators the LIVE bot is seeing."""

import time
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from binance.client import Client

def main():
    print("=" * 80)
    print("CHECKING LIVE BOT INDICATORS")
    print("=" * 80)
    
    # Load config
    config = Config.load_from_file("config/config.json")
    print(f"\nSymbol: {config.symbol}")
    
    # Initialize client
    client = Client(config.api_key, config.api_secret)
    
    # Initialize data manager and strategy
    data_manager = DataManager(config, client)
    strategy = StrategyEngine(config)
    
    # Fetch fresh data
    print(f"\nFetching fresh data for {config.symbol}...")
    candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=config.symbol)
    candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=config.symbol)
    
    print(f"  15m candles: {len(candles_15m)}")
    print(f"  1h candles: {len(candles_1h)}")
    
    # Update indicators
    strategy.update_indicators(candles_15m, candles_1h, None, None)
    
    # Check signals
    long_signal = strategy.check_long_entry(config.symbol)
    short_signal = strategy.check_short_entry(config.symbol)
    
    print(f"\n{'='*80}")
    print(f"CURRENT INDICATORS (LIVE BOT VIEW)")
    print(f"{'='*80}")
    print(f"Price: ${candles_15m[-1].close:.4f}")
    print(f"ADX: {strategy.current_indicators.adx:.2f} (threshold: {config.adx_threshold})")
    print(f"RVOL: {strategy.current_indicators.rvol:.2f} (threshold: {config.rvol_threshold})")
    print(f"Squeeze Value: {strategy.current_indicators.squeeze_value:.4f}")
    print(f"Squeeze Color: {strategy.current_indicators.squeeze_color}")
    print(f"Is Squeezed: {strategy.current_indicators.is_squeezed}")
    print(f"Trend 15m: {strategy.current_indicators.trend_15m}")
    print(f"Trend 1h: {strategy.current_indicators.trend_1h}")
    print(f"Price vs VWAP: {'ABOVE' if candles_15m[-1].close > strategy.current_indicators.vwap else 'BELOW'}")
    
    print(f"\n{'='*80}")
    print(f"SIGNAL CHECK")
    print(f"{'='*80}")
    print(f"LONG Signal: {'✓ DETECTED' if long_signal else '✗ None'}")
    print(f"SHORT Signal: {'✓ DETECTED' if short_signal else '✗ None'}")
    
    if not long_signal and not short_signal:
        print(f"\nChecking each condition for SHORT:")
        print(f"  price_vs_vwap == BELOW: {strategy.current_indicators.price_vs_vwap == 'BELOW'}")
        print(f"  trend_15m == BEARISH: {strategy.current_indicators.trend_15m == 'BEARISH'}")
        print(f"  trend_1h == BEARISH: {strategy.current_indicators.trend_1h == 'BEARISH'}")
        print(f"  squeeze_value < 0: {strategy.current_indicators.squeeze_value < 0}")
        print(f"  squeeze_color == maroon: {strategy.current_indicators.squeeze_color == 'maroon'}")
        print(f"  adx > threshold: {strategy.current_indicators.adx > config.adx_threshold}")
        print(f"  rvol > threshold: {strategy.current_indicators.rvol > config.rvol_threshold}")

if __name__ == "__main__":
    main()
