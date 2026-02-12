"""Comprehensive check of ALL signal conditions for all portfolio symbols."""

from binance.client import Client
from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine

config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)
data_manager = DataManager(config, client)
strategy = StrategyEngine(config)

print("=" * 80)
print("COMPREHENSIVE SIGNAL CONDITION CHECK")
print("=" * 80)
print()

print(f"Configuration:")
print(f"  RVOL Threshold: {config.rvol_threshold}")
print(f"  ADX Threshold: {config.adx_threshold}")
print(f"  Portfolio Symbols: {config.portfolio_symbols}")
print()

def check_long_conditions(indicators, symbol):
    """Check all long entry conditions and return detailed status."""
    conditions = {
        'price_vs_vwap': {
            'required': 'ABOVE',
            'actual': indicators['price_vs_vwap'],
            'pass': indicators['price_vs_vwap'] == 'ABOVE'
        },
        'trend_15m': {
            'required': 'BULLISH',
            'actual': indicators['trend_15m'],
            'pass': indicators['trend_15m'] == 'BULLISH'
        },
        'trend_1h': {
            'required': 'BULLISH',
            'actual': indicators['trend_1h'],
            'pass': indicators['trend_1h'] == 'BULLISH'
        },
        'squeeze_momentum': {
            'required': '> 0',
            'actual': f"{indicators['squeeze_value']:.4f}",
            'pass': indicators['squeeze_value'] > 0
        },
        'squeeze_color': {
            'required': 'green',
            'actual': indicators['squeeze_color'],
            'pass': indicators['squeeze_color'] == 'green'
        },
        'adx': {
            'required': f'> {config.adx_threshold}',
            'actual': f"{indicators['adx']:.2f}",
            'pass': indicators['adx'] > config.adx_threshold
        },
        'rvol': {
            'required': f'> {config.rvol_threshold}',
            'actual': f"{indicators['rvol']:.4f}",
            'pass': indicators['rvol'] > config.rvol_threshold
        }
    }
    return conditions

def check_short_conditions(indicators, symbol):
    """Check all short entry conditions and return detailed status."""
    conditions = {
        'price_vs_vwap': {
            'required': 'BELOW',
            'actual': indicators['price_vs_vwap'],
            'pass': indicators['price_vs_vwap'] == 'BELOW'
        },
        'trend_15m': {
            'required': 'BEARISH',
            'actual': indicators['trend_15m'],
            'pass': indicators['trend_15m'] == 'BEARISH'
        },
        'trend_1h': {
            'required': 'BEARISH',
            'actual': indicators['trend_1h'],
            'pass': indicators['trend_1h'] == 'BEARISH'
        },
        'squeeze_momentum': {
            'required': '< 0',
            'actual': f"{indicators['squeeze_value']:.4f}",
            'pass': indicators['squeeze_value'] < 0
        },
        'squeeze_color': {
            'required': 'maroon',
            'actual': indicators['squeeze_color'],
            'pass': indicators['squeeze_color'] == 'maroon'
        },
        'adx': {
            'required': f'> {config.adx_threshold}',
            'actual': f"{indicators['adx']:.2f}",
            'pass': indicators['adx'] > config.adx_threshold
        },
        'rvol': {
            'required': f'> {config.rvol_threshold}',
            'actual': f"{indicators['rvol']:.4f}",
            'pass': indicators['rvol'] > config.rvol_threshold
        }
    }
    return conditions

for symbol in config.portfolio_symbols:
    print("=" * 80)
    print(f"SYMBOL: {symbol}")
    print("=" * 80)
    print()
    
    try:
        # Fetch recent data
        candles_15m = data_manager.fetch_historical_data(days=2, timeframe="15m", symbol=symbol)
        candles_1h = data_manager.fetch_historical_data(days=2, timeframe="1h", symbol=symbol)
        candles_5m = data_manager.fetch_historical_data(days=2, timeframe="5m", symbol=symbol)
        candles_4h = data_manager.fetch_historical_data(days=2, timeframe="4h", symbol=symbol)
        
        # Update indicators
        strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
        
        # Get indicator snapshot
        indicators = strategy.get_indicator_snapshot()
        
        print(f"Current Price: ${indicators['current_price']:.4f}")
        print()
        
        # Check LONG conditions
        print("LONG ENTRY CONDITIONS:")
        print("-" * 80)
        long_conditions = check_long_conditions(indicators, symbol)
        
        all_long_pass = True
        for name, condition in long_conditions.items():
            status = "✓ PASS" if condition['pass'] else "✗ FAIL"
            print(f"  {name:20s}: {condition['actual']:15s} (need {condition['required']:15s}) {status}")
            if not condition['pass']:
                all_long_pass = False
        
        if all_long_pass:
            print()
            print("  🎯 ALL LONG CONDITIONS MET - SIGNAL GENERATED!")
        else:
            print()
            print("  ❌ Long signal blocked")
        
        print()
        
        # Check SHORT conditions
        print("SHORT ENTRY CONDITIONS:")
        print("-" * 80)
        short_conditions = check_short_conditions(indicators, symbol)
        
        all_short_pass = True
        for name, condition in short_conditions.items():
            status = "✓ PASS" if condition['pass'] else "✗ FAIL"
            print(f"  {name:20s}: {condition['actual']:15s} (need {condition['required']:15s}) {status}")
            if not condition['pass']:
                all_short_pass = False
        
        if all_short_pass:
            print()
            print("  🎯 ALL SHORT CONDITIONS MET - SIGNAL GENERATED!")
        else:
            print()
            print("  ❌ Short signal blocked")
        
        print()
        
        # Show volume details
        print("VOLUME ANALYSIS:")
        print("-" * 80)
        if len(candles_15m) >= 21:
            current_vol = candles_15m[-1].volume
            avg_vol = sum(c.volume for c in candles_15m[-21:-1]) / 20
            print(f"  Current volume: {current_vol:15.2f}")
            print(f"  Average volume: {avg_vol:15.2f}")
            print(f"  RVOL: {current_vol / avg_vol if avg_vol > 0 else 0:.4f}")
        
        print()
        
    except Exception as e:
        print(f"  Error: {e}")
        print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print("Key Requirements for LONG Entry:")
print("  1. Price ABOVE VWAP")
print("  2. 15m trend BULLISH")
print("  3. 1h trend BULLISH")
print("  4. Squeeze momentum > 0 (positive)")
print("  5. Squeeze color = GREEN (increasing bullish momentum)")
print("  6. ADX > threshold (strong trend)")
print("  7. RVOL > threshold (high volume)")
print()
print("Key Requirements for SHORT Entry:")
print("  1. Price BELOW VWAP")
print("  2. 15m trend BEARISH")
print("  3. 1h trend BEARISH")
print("  4. Squeeze momentum < 0 (negative)")
print("  5. Squeeze color = MAROON (increasing bearish momentum)")
print("  6. ADX > threshold (strong trend)")
print("  7. RVOL > threshold (high volume)")
print()
print("Note: Squeeze color is CRITICAL for signal generation!")
print("  - GREEN = bullish momentum increasing (required for LONG)")
print("  - MAROON = bearish momentum increasing (required for SHORT)")
print("  - BLUE = momentum weakening (blocks signals)")
print("  - GRAY = no clear momentum (blocks signals)")
