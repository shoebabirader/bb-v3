"""Check RVOL for all portfolio symbols in real-time."""

from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine

config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)
data_manager = DataManager(config, client)
strategy = StrategyEngine(config)

print("=" * 80)
print("LIVE RVOL CHECK FOR ALL PORTFOLIO SYMBOLS")
print("=" * 80)
print()

print(f"RVOL Threshold: {config.rvol_threshold}")
print(f"Portfolio Symbols: {config.portfolio_symbols}")
print()

for symbol in config.portfolio_symbols:
    print(f"\n{symbol}:")
    print("-" * 40)
    
    try:
        # Fetch recent data
        candles_15m = data_manager.fetch_historical_data(days=2, timeframe="15m", symbol=symbol)
        candles_1h = data_manager.fetch_historical_data(days=2, timeframe="1h", symbol=symbol)
        
        # Update indicators
        strategy.update_indicators(candles_15m, candles_1h)
        
        # Get indicator snapshot
        indicators = strategy.get_indicator_snapshot()
        
        # Show key metrics
        print(f"  Current Price: ${indicators['current_price']:.4f}")
        print(f"  RVOL: {indicators['rvol']:.4f} {'✓ PASS' if indicators['rvol'] >= config.rvol_threshold else '✗ FAIL'}")
        print(f"  ADX: {indicators['adx']:.2f} {'✓ PASS' if indicators['adx'] >= config.adx_threshold else '✗ FAIL'}")
        print(f"  Squeeze Color: {indicators['squeeze_color']}")
        print(f"  Squeeze Momentum: {indicators['squeeze_value']:.4f}")
        print(f"  Trend 15m: {indicators['trend_15m']}")
        print(f"  Trend 1h: {indicators['trend_1h']}")
        print(f"  Price vs VWAP: {indicators['price_vs_vwap']}")
        
        # Show last 5 candle volumes
        print(f"\n  Last 5 candle volumes:")
        for i, candle in enumerate(candles_15m[-5:]):
            print(f"    {i+1}. {candle.volume:15.2f}")
        
        # Calculate average volume
        if len(candles_15m) >= 21:
            avg_vol = sum(c.volume for c in candles_15m[-21:-1]) / 20
            current_vol = candles_15m[-1].volume
            print(f"\n  Current volume: {current_vol:15.2f}")
            print(f"  Average volume: {avg_vol:15.2f}")
            print(f"  Ratio (RVOL): {current_vol / avg_vol if avg_vol > 0 else 0:.4f}")
        
    except Exception as e:
        print(f"  Error: {e}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print("If RVOL is consistently low (< 1.0) for all symbols, this means:")
print("  1. Current market volume is below average (normal market condition)")
print("  2. Bot is correctly waiting for high-volume breakouts")
print("  3. This is NOT a bug - it's the bot being disciplined")
print()
print("Options:")
print("  1. Wait for volume to increase (recommended)")
print("  2. Lower rvol_threshold to 0.5-0.7 for more trades")
print("  3. Temporarily disable RVOL by setting rvol_threshold to 0.01")
