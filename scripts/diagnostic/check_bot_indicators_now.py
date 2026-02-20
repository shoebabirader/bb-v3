import sys
sys.path.append('src')

from data_manager import DataManager
from indicators import add_all_indicators
from config import Config
import pandas as pd

# Initialize
config = Config()
data_manager = DataManager(config)

symbol = "XRPUSDT"

print(f"\n{'='*80}")
print(f"CHECKING LIVE BOT INDICATORS FOR {symbol}")
print(f"{'='*80}\n")

# Fetch data with use_cache=False (same as bot now does)
print("Fetching FRESH data (use_cache=FALSE)...")
candles_15m = data_manager.fetch_historical_data(days=2, timeframe="15m", symbol=symbol, use_cache=False)
candles_1h = data_manager.fetch_historical_data(days=2, timeframe="1h", symbol=symbol, use_cache=False)

print(f"✓ Got {len(candles_15m)} candles for 15m")
print(f"✓ Got {len(candles_1h)} candles for 1h")

# Calculate indicators
df_15m = pd.DataFrame(candles_15m)
df_1h = pd.DataFrame(candles_1h)

# Add indicators
df_15m = add_all_indicators(df_15m)
df_1h = add_all_indicators(df_1h)

# Get latest values
latest_15m = df_15m.iloc[-1]
latest_1h = df_1h.iloc[-1]

print(f"\n--- LATEST INDICATOR VALUES ---")
print(f"Current Price: ${latest_15m['close']:.4f}")
print(f"\n15m Timeframe:")
print(f"  ADX: {latest_15m['adx']:.2f}")
print(f"  RVOL: {latest_15m['rvol']:.2f}")
print(f"  Squeeze: {latest_15m['squeeze']:.4f}")
print(f"  Squeeze Color: {latest_15m['squeeze_color']}")
print(f"  RSI: {latest_15m['rsi']:.2f}")
print(f"  EMA Trend: {latest_15m['ema_trend']}")

print(f"\n1h Timeframe:")
print(f"  ADX: {latest_1h['adx']:.2f}")
print(f"  EMA Trend: {latest_1h['ema_trend']}")

print(f"\n{'='*80}")
print("This is what the bot should be seeing with use_cache=False")
print(f"{'='*80}\n")
