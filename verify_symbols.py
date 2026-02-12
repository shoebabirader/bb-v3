"""Verify which symbols are valid on Binance Futures."""

from binance.client import Client
from src.config import Config

config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)

print("=" * 80)
print("VERIFYING BINANCE FUTURES SYMBOLS")
print("=" * 80)

# Get all valid futures symbols
print("\nFetching all valid Binance Futures symbols...")
exchange_info = client.futures_exchange_info()
valid_symbols = {s['symbol'] for s in exchange_info['symbols'] if s['status'] == 'TRADING'}

print(f"Total valid symbols: {len(valid_symbols)}\n")

# Check configured symbols
print("Checking configured portfolio symbols:")
print("=" * 80)

for symbol in config.portfolio_symbols:
    if symbol in valid_symbols:
        print(f"✓ {symbol} - VALID")
    else:
        print(f"✗ {symbol} - INVALID (not found on Binance Futures)")
        
        # Try to find similar symbols
        similar = [s for s in valid_symbols if symbol[:4] in s or symbol[:-4] in s]
        if similar:
            print(f"  Similar symbols: {', '.join(list(similar)[:5])}")

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)

invalid_symbols = [s for s in config.portfolio_symbols if s not in valid_symbols]

if invalid_symbols:
    print(f"\n❌ FOUND {len(invalid_symbols)} INVALID SYMBOL(S): {', '.join(invalid_symbols)}")
    print("\nYou need to remove these from config.json portfolio_symbols")
    print("\nValid alternatives you might want:")
    
    # Suggest some popular futures symbols
    popular = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"]
    available_popular = [s for s in popular if s in valid_symbols and s not in config.portfolio_symbols]
    
    if available_popular:
        print(f"  {', '.join(available_popular)}")
else:
    print("\n✓ ALL SYMBOLS ARE VALID!")
