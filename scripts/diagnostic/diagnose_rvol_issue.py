"""Diagnostic script to investigate RVOL calculation issue."""

from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.indicators import IndicatorCalculator

# Load config
config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)
data_manager = DataManager(config, client)

print("=" * 80)
print("RVOL DIAGNOSTIC REPORT")
print("=" * 80)
print()

# Test with XAGUSDT (the current trading symbol)
symbol = config.symbol
print(f"Testing symbol: {symbol}")
print()

# Fetch historical data
print("Fetching 15m candles...")
candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
print(f"Fetched {len(candles_15m)} candles")
print()

# Check last 25 candles for volume data
print("=" * 80)
print("VOLUME DATA CHECK (Last 25 candles)")
print("=" * 80)
print()

last_25 = candles_15m[-25:]
for i, candle in enumerate(last_25):
    print(f"Candle {i+1:2d}: Volume = {candle.volume:15.2f}, Close = {candle.close:10.4f}")

print()
print("=" * 80)
print("RVOL CALCULATION TEST")
print("=" * 80)
print()

# Test RVOL calculation with different periods
for period in [10, 20, 30]:
    if len(candles_15m) >= period + 1:
        rvol = IndicatorCalculator.calculate_rvol(candles_15m, period)
        print(f"RVOL (period={period}): {rvol:.4f}")
        
        # Show the calculation breakdown
        historical_candles = candles_15m[-(period + 1):-1]
        current_candle = candles_15m[-1]
        
        avg_volume = sum(c.volume for c in historical_candles) / len(historical_candles)
        
        print(f"  Current volume: {current_candle.volume:.2f}")
        print(f"  Average volume (last {period}): {avg_volume:.2f}")
        print(f"  Ratio: {current_candle.volume / avg_volume if avg_volume > 0 else 0:.4f}")
        print()

print("=" * 80)
print("VOLUME STATISTICS")
print("=" * 80)
print()

volumes = [c.volume for c in candles_15m]
print(f"Total candles: {len(volumes)}")
print(f"Min volume: {min(volumes):.2f}")
print(f"Max volume: {max(volumes):.2f}")
print(f"Average volume: {sum(volumes) / len(volumes):.2f}")
print(f"Zero volume candles: {sum(1 for v in volumes if v == 0)}")
print()

# Check if volume is consistently zero or very low
if max(volumes) < 1.0:
    print("⚠️  WARNING: All volumes are very low (< 1.0)")
    print("   This suggests volume data might not be loading correctly")
    print()

if sum(1 for v in volumes if v == 0) > len(volumes) * 0.1:
    print("⚠️  WARNING: More than 10% of candles have zero volume")
    print("   This suggests data quality issues")
    print()

print("=" * 80)
print("TESTING OTHER SYMBOLS")
print("=" * 80)
print()

for test_symbol in ["XAUUSDT", "BTCUSDT", "ETHUSDT"]:
    try:
        print(f"\n{test_symbol}:")
        test_candles = data_manager.fetch_historical_data(days=1, timeframe="15m", symbol=test_symbol)
        
        if len(test_candles) >= 21:
            rvol = IndicatorCalculator.calculate_rvol(test_candles, 20)
            current_vol = test_candles[-1].volume
            avg_vol = sum(c.volume for c in test_candles[-21:-1]) / 20
            
            print(f"  RVOL: {rvol:.4f}")
            print(f"  Current volume: {current_vol:.2f}")
            print(f"  Average volume: {avg_vol:.2f}")
        else:
            print(f"  Not enough data ({len(test_candles)} candles)")
    except Exception as e:
        print(f"  Error: {e}")

print()
print("=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)
