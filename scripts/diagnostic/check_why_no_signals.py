"""Deep dive into why signals aren't being generated even with good RVOL."""
from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine

print("="*70)
print("SIGNAL GENERATION DEEP DIVE")
print("="*70)

# Load config
config = Config.load_from_file('config/config.json')
client = Client(config.api_key, config.api_secret)
data_manager = DataManager(config, client)

# Check TRXUSDT since it has the best RVOL
symbol = "TRXUSDT"
config.symbol = symbol

print(f"\nAnalyzing {symbol} (highest RVOL)...")
print(f"{'='*70}\n")

# Create strategy
strategy = StrategyEngine(config)

# Fetch data
candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m", symbol=symbol)
candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h", symbol=symbol)

print(f"Data fetched: {len(candles_15m)} 15m candles, {len(candles_1h)} 1h candles")

# Update indicators
strategy.update_indicators(candles_15m, candles_1h)

# Get indicators
ind = strategy.current_indicators

print(f"\nCurrent Indicators:")
print(f"  ADX: {ind.adx:.2f} (threshold: {config.adx_threshold})")
print(f"  RVOL: {ind.rvol:.2f} (threshold: {config.rvol_threshold})")
print(f"  ATR 15m: {ind.atr_15m:.6f}")
print(f"  ATR 1h: {ind.atr_1h:.6f}")
print(f"  Trend 15m: {ind.trend_15m}")
print(f"  Trend 1h: {ind.trend_1h}")
print(f"  Squeeze Color: {ind.squeeze_color}")
print(f"  Squeeze Value: {ind.squeeze_value:.4f}")
print(f"  Is Squeezed: {ind.is_squeezed}")
print(f"  Price vs VWAP: {ind.price_vs_vwap}")
print(f"  VWAP 15m: ${ind.vwap_15m:.4f}")
print(f"  Current Price: ${ind.current_price:.4f}")

# Check entry conditions manually
print(f"\n{'='*70}")
print("LONG ENTRY CONDITIONS CHECK")
print(f"{'='*70}")

long_conditions = {
    "ADX >= threshold": (ind.adx >= config.adx_threshold, f"{ind.adx:.2f} >= {config.adx_threshold}"),
    "RVOL >= threshold": (ind.rvol >= config.rvol_threshold, f"{ind.rvol:.2f} >= {config.rvol_threshold}"),
    "15m trend BULLISH": (ind.trend_15m == "BULLISH", f"{ind.trend_15m}"),
    "1h trend BULLISH": (ind.trend_1h == "BULLISH", f"{ind.trend_1h}"),
    "Squeeze firing (green)": (ind.squeeze_color == "green", f"{ind.squeeze_color}"),
    "Price above VWAP": (ind.price_vs_vwap == "ABOVE", f"{ind.price_vs_vwap}"),
}

for condition, (passed, value) in long_conditions.items():
    status = "✓" if passed else "✗"
    print(f"  {status} {condition}: {value}")

print(f"\n{'='*70}")
print("SHORT ENTRY CONDITIONS CHECK")
print(f"{'='*70}")

short_conditions = {
    "ADX >= threshold": (ind.adx >= config.adx_threshold, f"{ind.adx:.2f} >= {config.adx_threshold}"),
    "RVOL >= threshold": (ind.rvol >= config.rvol_threshold, f"{ind.rvol:.2f} >= {config.rvol_threshold}"),
    "15m trend BEARISH": (ind.trend_15m == "BEARISH", f"{ind.trend_15m}"),
    "1h trend BEARISH": (ind.trend_1h == "BEARISH", f"{ind.trend_1h}"),
    "Squeeze firing (red)": (ind.squeeze_color == "red", f"{ind.squeeze_color}"),
    "Price below VWAP": (ind.price_vs_vwap == "BELOW", f"{ind.price_vs_vwap}"),
}

for condition, (passed, value) in short_conditions.items():
    status = "✓" if passed else "✗"
    print(f"  {status} {condition}: {value}")

# Check actual signals
print(f"\n{'='*70}")
print("ACTUAL SIGNAL CHECK")
print(f"{'='*70}")

long_signal = strategy.check_long_entry(symbol)
short_signal = strategy.check_short_entry(symbol)

print(f"  LONG signal: {long_signal is not None}")
print(f"  SHORT signal: {short_signal is not None}")

if long_signal:
    print(f"\n  ✅ LONG SIGNAL DETECTED!")
    print(f"     Entry: ${long_signal.price:.4f}")
    print(f"     Stop: ${long_signal.stop_loss:.4f}")
elif short_signal:
    print(f"\n  ✅ SHORT SIGNAL DETECTED!")
    print(f"     Entry: ${short_signal.price:.4f}")
    print(f"     Stop: ${short_signal.stop_loss:.4f}")
else:
    print(f"\n  ⚠️  NO SIGNAL DETECTED")
    
    # Identify what's missing
    long_passed = sum(1 for passed, _ in long_conditions.values() if passed)
    short_passed = sum(1 for passed, _ in short_conditions.values() if passed)
    
    print(f"\n  LONG conditions met: {long_passed}/{len(long_conditions)}")
    print(f"  SHORT conditions met: {short_passed}/{len(short_conditions)}")
    
    if long_passed >= short_passed and long_passed > 0:
        print(f"\n  Closest to LONG signal. Missing:")
        for condition, (passed, value) in long_conditions.items():
            if not passed:
                print(f"    • {condition}")
    elif short_passed > 0:
        print(f"\n  Closest to SHORT signal. Missing:")
        for condition, (passed, value) in short_conditions.items():
            if not passed:
                print(f"    • {condition}")
    else:
        print(f"\n  Market conditions not favorable for either direction.")

print(f"\n{'='*70}")
print("DIAGNOSIS COMPLETE")
print(f"{'='*70}")
