"""Check if multi-timeframe data is sufficient."""

from src.config import Config
from src.data_manager import DataManager
from binance.client import Client

print("=" * 80)
print("MULTI-TIMEFRAME DATA VERIFICATION")
print("=" * 80)

# Load config
config = Config.load_from_file('config/config.json')
print(f"\nMulti-timeframe enabled: {config.enable_multi_timeframe}")
print(f"Min timeframe alignment: {config.min_timeframe_alignment}")

if not config.enable_multi_timeframe:
    print("\n⚠️  Multi-timeframe is DISABLED in config")
    print("Only 15m and 1h data will be used")
    exit(0)

# Create client and data manager
client = Client(config.api_key, config.api_secret)
data_manager = DataManager(config, client)

print(f"\nFetching data for {config.symbol}...")
print("-" * 80)

# Fetch all 4 timeframes
timeframes = {
    '5m': 2,   # 2 days
    '15m': 2,  # 2 days
    '1h': 2,   # 2 days
    '4h': 7    # 7 days (need more for 4h)
}

data_summary = {}

for tf, days in timeframes.items():
    try:
        candles = data_manager.fetch_historical_data(days=days, timeframe=tf)
        data_summary[tf] = len(candles)
        print(f"✓ {tf:4s}: {len(candles):4d} candles fetched")
    except Exception as e:
        data_summary[tf] = 0
        print(f"✗ {tf:4s}: FAILED - {e}")

print("\n" + "=" * 80)
print("DATA SUFFICIENCY ANALYSIS")
print("=" * 80)

# Minimum requirements for indicators
requirements = {
    '5m': 28,   # 2× ADX period (14)
    '15m': 28,  # 2× ADX period (14)
    '1h': 28,   # 2× ADX period (14)
    '4h': 28    # 2× ADX period (14)
}

print("\nTimeframe | Fetched | Required | Status")
print("-" * 50)

all_sufficient = True
for tf in ['5m', '15m', '1h', '4h']:
    fetched = data_summary.get(tf, 0)
    required = requirements[tf]
    status = "✓ SUFFICIENT" if fetched >= required else "✗ INSUFFICIENT"
    multiplier = f"({fetched/required:.1f}x)" if fetched >= required else ""
    
    print(f"{tf:9s} | {fetched:7d} | {required:8d} | {status} {multiplier}")
    
    if fetched < required:
        all_sufficient = False

print("\n" + "=" * 80)

if all_sufficient:
    print("✓ ALL TIMEFRAMES HAVE SUFFICIENT DATA")
    print("\nMulti-timeframe analysis will work correctly:")
    print(f"  - Requires {config.min_timeframe_alignment} out of 4 timeframes to align")
    print(f"  - All 4 timeframes have enough data for indicator calculation")
    print(f"  - Bot is ready for multi-timeframe trading")
else:
    print("✗ SOME TIMEFRAMES HAVE INSUFFICIENT DATA")
    print("\nRecommendation: Increase 'days' parameter when fetching data")

print("=" * 80)
