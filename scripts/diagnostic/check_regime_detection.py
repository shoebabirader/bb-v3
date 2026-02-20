"""Check if data is sufficient for regime detection and explain usage."""

from src.config import Config
from src.data_manager import DataManager
from src.indicators import IndicatorCalculator
from src.market_regime_detector import MarketRegimeDetector
from binance.client import Client

print("=" * 80)
print("REGIME DETECTION DATA VERIFICATION & USAGE GUIDE")
print("=" * 80)

# Load config
config = Config.load_from_file('config/config.json')
print(f"\nRegime Detection Status: {'ENABLED' if config.enable_regime_detection else 'DISABLED'}")
print(f"Update Interval: {config.regime_update_interval}s ({config.regime_update_interval/60:.1f} minutes)")
print(f"Stability Required: {config.regime_stability_minutes} minutes")

# Create client and data manager
client = Client(config.api_key, config.api_secret)
data_manager = DataManager(config, client)

print(f"\n" + "=" * 80)
print("DATA REQUIREMENTS FOR REGIME DETECTION")
print("=" * 80)

# Minimum data requirements
min_candles = 30  # Minimum required by detect_regime()
recommended_candles = 50  # Recommended for accurate detection

print(f"\nMinimum candles required: {min_candles}")
print(f"Recommended candles: {recommended_candles}")
print(f"\nFetching data for {config.symbol}...")

# Fetch data for regime detection (using 15m timeframe)
try:
    candles = data_manager.fetch_historical_data(days=2, timeframe="15m")
    print(f"✓ Fetched {len(candles)} candles (15m timeframe)")
    
    if len(candles) >= recommended_candles:
        print(f"✓ SUFFICIENT DATA ({len(candles)/recommended_candles:.1f}x recommended)")
    elif len(candles) >= min_candles:
        print(f"⚠ MINIMAL DATA ({len(candles)} candles, {recommended_candles} recommended)")
    else:
        print(f"✗ INSUFFICIENT DATA (need {min_candles}, have {len(candles)})")
        exit(1)
        
except Exception as e:
    print(f"✗ FAILED to fetch data: {e}")
    exit(1)

print(f"\n" + "=" * 80)
print("REGIME DETECTION TEST")
print("=" * 80)

# Test regime detection
try:
    indicator_calc = IndicatorCalculator()
    regime_detector = MarketRegimeDetector(config, indicator_calc)
    
    regime = regime_detector.detect_regime(candles)
    regime_params = regime_detector.get_regime_parameters(regime)
    
    print(f"\n✓ Regime Detection Working")
    print(f"\nCurrent Market Regime: {regime}")
    print(f"Strategy Type: {regime_params.strategy_type}")
    print(f"Stop Loss Multiplier: {regime_params.stop_multiplier}x ATR")
    print(f"Position Size Multiplier: {regime_params.position_size_multiplier}x")
    print(f"Threshold Multiplier: {regime_params.threshold_multiplier}x")
    
    # Calculate indicators used for regime detection
    adx = indicator_calc.calculate_adx(candles, config.adx_period)
    atr = indicator_calc.calculate_atr(candles, config.atr_period)
    vwap = indicator_calc.calculate_vwap(candles, candles[0].timestamp)
    current_price = candles[-1].close
    
    print(f"\nRegime Indicators:")
    print(f"  ADX: {adx:.2f}")
    print(f"  ATR: {atr:.6f}")
    print(f"  Price: ${current_price:.4f}")
    print(f"  VWAP: ${vwap:.4f}")
    print(f"  Price vs VWAP: {'ABOVE' if current_price > vwap else 'BELOW'}")
    
except Exception as e:
    print(f"✗ FAILED: {e}")
    exit(1)

print(f"\n" + "=" * 80)
print("HOW REGIME DETECTION WORKS")
print("=" * 80)

print("""
Regime detection classifies the market into 5 states:

1. TRENDING_BULLISH
   - Strong uptrend (ADX > 30, Price > VWAP)
   - Uses: Trend-following strategy
   - Stop: 2.5x ATR (wider stops)
   - Position: 100% normal size

2. TRENDING_BEARISH
   - Strong downtrend (ADX > 30, Price < VWAP)
   - Uses: Trend-following strategy
   - Stop: 2.5x ATR (wider stops)
   - Position: 100% normal size

3. RANGING
   - Sideways market (ADX < 20, Low volatility)
   - Uses: Mean-reversion strategy
   - Stop: 1.0x ATR (tighter stops)
   - Position: 100% normal size

4. VOLATILE
   - High volatility (ATR > 80th percentile)
   - Uses: Trend-following with caution
   - Stop: 2.5x ATR (wider stops)
   - Position: 50% size (reduced risk)
   - Thresholds: 30% higher (more selective)

5. UNCERTAIN
   - Unclear conditions
   - Uses: No trading or very conservative
   - Stop: 2.0x ATR (default)
   - Position: 50% size (reduced risk)
""")

print("=" * 80)
print("HOW TO USE REGIME DETECTION")
print("=" * 80)

print(f"""
Current Status: {'ENABLED' if config.enable_regime_detection else 'DISABLED'}

To ENABLE regime detection:
1. Edit config/config.json
2. Set "enable_regime_detection": true
3. Restart the bot

Configuration Parameters:
- regime_update_interval: {config.regime_update_interval}s (how often to check)
- regime_stability_minutes: {config.regime_stability_minutes} (confirmation time)
- regime_trending_adx_threshold: {config.regime_trending_adx_threshold} (trend strength)
- regime_ranging_adx_threshold: {config.regime_ranging_adx_threshold} (ranging threshold)
- regime_volatile_atr_percentile: {config.regime_volatile_atr_percentile} (volatility threshold)

Benefits of Regime Detection:
✓ Adapts strategy to market conditions
✓ Reduces risk in volatile/uncertain markets
✓ Uses wider stops in trending markets
✓ Uses tighter stops in ranging markets
✓ Automatically adjusts position sizes

When to Use:
✓ Markets with changing conditions
✓ Want adaptive risk management
✓ Need automatic strategy switching

When NOT to Use:
✗ Very stable trending markets
✗ Want consistent strategy
✗ Prefer manual control
""")

print("=" * 80)
print("INTEGRATION WITH CURRENT BOT")
print("=" * 80)

print(f"""
Your bot currently has:
- Multi-timeframe: {'ENABLED' if config.enable_multi_timeframe else 'DISABLED'}
- Volume Profile: {'ENABLED' if config.enable_volume_profile else 'DISABLED'}
- Adaptive Thresholds: {'ENABLED' if config.enable_adaptive_thresholds else 'DISABLED'}
- Portfolio Management: {'ENABLED' if config.enable_portfolio_management else 'DISABLED'}
- Advanced Exits: {'ENABLED' if config.enable_advanced_exits else 'DISABLED'}
- Regime Detection: {'ENABLED' if config.enable_regime_detection else 'DISABLED'}

If you enable regime detection:
1. Bot will check market regime every {config.regime_update_interval/60:.1f} minutes
2. Regime must be stable for {config.regime_stability_minutes} minutes before applying
3. Stop-loss and position sizes will adjust automatically
4. Strategy will switch between trend-following and mean-reversion

Data is SUFFICIENT for regime detection ✓
""")

print("=" * 80)
