"""Pre-flight check script for paper trading.

This script verifies:
1. Binance API connection
2. Real-time price fetching
3. Historical data retrieval
4. Signal generation with live data
5. All advanced features initialization
"""

import sys
import time
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException

from src.config import Config
from src.data_manager import DataManager
from src.strategy import StrategyEngine
from src.indicators import IndicatorCalculator


def print_header(text):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_status(text, status="INFO"):
    """Print a status message."""
    symbols = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️"
    }
    print(f"{symbols.get(status, 'ℹ️')} {text}")


def test_binance_connection(config):
    """Test connection to Binance API."""
    print_header("1. Testing Binance API Connection")
    
    try:
        client = Client(config.api_key, config.api_secret)
        
        # Test connection
        print_status("Connecting to Binance API...", "INFO")
        server_time = client.get_server_time()
        server_datetime = datetime.fromtimestamp(server_time['serverTime'] / 1000)
        
        print_status(f"Connected successfully!", "SUCCESS")
        print_status(f"Server time: {server_datetime}", "INFO")
        
        # Test API permissions
        print_status("Checking API permissions...", "INFO")
        account = client.futures_account()
        
        print_status("API permissions verified!", "SUCCESS")
        print_status(f"Account type: Futures", "INFO")
        
        return client, True
        
    except BinanceAPIException as e:
        print_status(f"Binance API Error: {e.message}", "ERROR")
        print_status(f"Error code: {e.code}", "ERROR")
        return None, False
        
    except Exception as e:
        print_status(f"Connection error: {str(e)}", "ERROR")
        return None, False


def test_live_price_fetch(client, symbol):
    """Test fetching live price data."""
    print_header("2. Testing Live Price Fetching")
    
    try:
        # Get current price
        print_status(f"Fetching current price for {symbol}...", "INFO")
        ticker = client.futures_symbol_ticker(symbol=symbol)
        current_price = float(ticker['price'])
        
        print_status(f"Current {symbol} price: ${current_price:,.4f}", "SUCCESS")
        
        # Get 24h stats
        print_status("Fetching 24h statistics...", "INFO")
        stats = client.futures_ticker(symbol=symbol)
        
        price_change = float(stats['priceChangePercent'])
        volume = float(stats['volume'])
        high_24h = float(stats['highPrice'])
        low_24h = float(stats['lowPrice'])
        
        print_status(f"24h Change: {price_change:+.2f}%", "INFO")
        print_status(f"24h Volume: {volume:,.0f}", "INFO")
        print_status(f"24h High: ${high_24h:,.4f}", "INFO")
        print_status(f"24h Low: ${low_24h:,.4f}", "INFO")
        
        return True
        
    except Exception as e:
        print_status(f"Error fetching live price: {str(e)}", "ERROR")
        return False


def test_historical_data_fetch(config, client):
    """Test fetching historical data for all timeframes."""
    print_header("3. Testing Historical Data Fetching")
    
    try:
        data_manager = DataManager(config, client)
        
        timeframes = ["5m", "15m", "1h", "4h"]
        candle_counts = {}
        
        for timeframe in timeframes:
            print_status(f"Fetching {timeframe} historical data (7 days)...", "INFO")
            candles = data_manager.fetch_historical_data(days=7, timeframe=timeframe)
            candle_counts[timeframe] = len(candles)
            
            if len(candles) > 0:
                latest = candles[-1]
                print_status(
                    f"✓ {timeframe}: {len(candles)} candles | "
                    f"Latest close: ${latest.close:,.4f}",
                    "SUCCESS"
                )
            else:
                print_status(f"✗ {timeframe}: No data received", "ERROR")
                return False
        
        # Verify we have enough data
        min_required = {"5m": 1000, "15m": 300, "1h": 100, "4h": 40}
        
        print_status("\nData sufficiency check:", "INFO")
        all_sufficient = True
        for tf, count in candle_counts.items():
            required = min_required.get(tf, 0)
            sufficient = count >= required
            status = "SUCCESS" if sufficient else "WARNING"
            print_status(
                f"{tf}: {count} candles (required: {required}) - "
                f"{'✓ Sufficient' if sufficient else '⚠ May be insufficient'}",
                status
            )
            if not sufficient:
                all_sufficient = False
        
        return all_sufficient
        
    except Exception as e:
        print_status(f"Error fetching historical data: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_indicator_calculation(config, client):
    """Test indicator calculation with live data."""
    print_header("4. Testing Indicator Calculation")
    
    try:
        # Fetch data
        data_manager = DataManager(config, client)
        
        print_status("Fetching data for indicator calculation...", "INFO")
        candles_5m = data_manager.fetch_historical_data(days=7, timeframe="5m")
        candles_15m = data_manager.fetch_historical_data(days=7, timeframe="15m")
        candles_1h = data_manager.fetch_historical_data(days=7, timeframe="1h")
        candles_4h = data_manager.fetch_historical_data(days=7, timeframe="4h")
        
        # Initialize strategy
        print_status("Initializing strategy engine...", "INFO")
        strategy = StrategyEngine(config)
        
        # Update indicators
        print_status("Calculating indicators...", "INFO")
        strategy.update_indicators(candles_15m, candles_1h, candles_5m, candles_4h)
        
        # Display indicator values
        indicators = strategy.get_indicator_snapshot()
        
        print_status("\nIndicator Values:", "SUCCESS")
        print(f"  Current Price: ${indicators['current_price']:,.4f}")
        print(f"  VWAP (15m): ${indicators['vwap_15m']:,.4f}")
        print(f"  VWAP (1h): ${indicators['vwap_1h']:,.4f}")
        print(f"  Price vs VWAP: {indicators['price_vs_vwap']}")
        print(f"  ATR (15m): ${indicators['atr_15m']:,.4f}")
        print(f"  ADX: {indicators['adx']:.2f}")
        print(f"  RVOL: {indicators['rvol']:.2f}")
        print(f"  Squeeze Value: {indicators['squeeze_value']:.4f}")
        print(f"  Squeeze Color: {indicators['squeeze_color']}")
        print(f"  Trend (15m): {indicators['trend_15m']}")
        print(f"  Trend (1h): {indicators['trend_1h']}")
        
        return strategy, True
        
    except Exception as e:
        print_status(f"Error calculating indicators: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return None, False


def test_signal_generation(strategy, config):
    """Test signal generation with current market conditions."""
    print_header("5. Testing Signal Generation")
    
    try:
        print_status("Checking for entry signals...", "INFO")
        
        # Check long signal
        long_signal = strategy.check_long_entry()
        if long_signal:
            print_status("LONG ENTRY SIGNAL DETECTED!", "SUCCESS")
            print(f"  Signal Type: {long_signal.type}")
            print(f"  Price: ${long_signal.price:,.4f}")
            print(f"  Timestamp: {datetime.fromtimestamp(long_signal.timestamp/1000)}")
            if hasattr(long_signal, 'confidence'):
                print(f"  Confidence: {long_signal.confidence:.2%}")
        else:
            print_status("No long entry signal", "INFO")
        
        # Check short signal
        short_signal = strategy.check_short_entry()
        if short_signal:
            print_status("SHORT ENTRY SIGNAL DETECTED!", "SUCCESS")
            print(f"  Signal Type: {short_signal.type}")
            print(f"  Price: ${short_signal.price:,.4f}")
            print(f"  Timestamp: {datetime.fromtimestamp(short_signal.timestamp/1000)}")
            if hasattr(short_signal, 'confidence'):
                print(f"  Confidence: {short_signal.confidence:.2%}")
        else:
            print_status("No short entry signal", "INFO")
        
        if not long_signal and not short_signal:
            print_status("\nNo signals at current market conditions", "INFO")
            print_status("This is normal - signals are only generated when all conditions align", "INFO")
        
        return True
        
    except Exception as e:
        print_status(f"Error generating signals: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_advanced_features(strategy):
    """Test advanced features initialization."""
    print_header("6. Testing Advanced Features")
    
    features_status = []
    
    # Multi-timeframe
    if strategy.timeframe_coordinator:
        print_status("Multi-Timeframe Coordinator: ENABLED", "SUCCESS")
        if strategy.timeframe_analysis:
            print(f"  Alignment Score: {strategy.timeframe_analysis.alignment_score}/4")
            print(f"  Overall Direction: {strategy.timeframe_analysis.overall_direction}")
            print(f"  Confidence: {strategy.timeframe_analysis.confidence:.2%}")
        features_status.append(True)
    else:
        print_status("Multi-Timeframe Coordinator: DISABLED", "WARNING")
        features_status.append(False)
    
    # Adaptive thresholds
    if strategy.adaptive_threshold_manager:
        print_status("Adaptive Threshold Manager: ENABLED", "SUCCESS")
        thresholds = strategy.adaptive_threshold_manager.get_current_thresholds()
        print(f"  ADX Threshold: {thresholds['adx']:.2f}")
        print(f"  RVOL Threshold: {thresholds['rvol']:.2f}")
        features_status.append(True)
    else:
        print_status("Adaptive Threshold Manager: DISABLED", "WARNING")
        features_status.append(False)
    
    # Volume profile
    if strategy.volume_profile_analyzer:
        print_status("Volume Profile Analyzer: ENABLED", "SUCCESS")
        if strategy.volume_profile_analyzer.current_profile:
            profile = strategy.volume_profile_analyzer.current_profile
            print(f"  POC: ${profile.poc:,.4f}")
            print(f"  VAH: ${profile.vah:,.4f}")
            print(f"  VAL: ${profile.val:,.4f}")
        features_status.append(True)
    else:
        print_status("Volume Profile Analyzer: DISABLED", "WARNING")
        features_status.append(False)
    
    # Market regime
    if strategy.market_regime_detector:
        print_status("Market Regime Detector: ENABLED", "SUCCESS")
        print(f"  Current Regime: {strategy.market_regime_detector.current_regime}")
        features_status.append(True)
    else:
        print_status("Market Regime Detector: DISABLED", "WARNING")
        features_status.append(False)
    
    # ML predictor
    if strategy.ml_predictor and strategy.ml_predictor.enabled:
        print_status("ML Predictor: ENABLED", "SUCCESS")
        print(f"  Prediction: {strategy.ml_prediction:.2%}")
        features_status.append(True)
    else:
        print_status("ML Predictor: DISABLED (requires training)", "WARNING")
        features_status.append(False)
    
    enabled_count = sum(features_status)
    total_count = len(features_status)
    
    print_status(f"\nAdvanced Features: {enabled_count}/{total_count} enabled", 
                 "SUCCESS" if enabled_count >= 4 else "WARNING")
    
    return True


def main():
    """Run all pre-flight checks."""
    print_header("🚀 PRE-FLIGHT CHECK FOR PAPER TRADING")
    print("This script will verify your system is ready for paper trading")
    
    try:
        # Load configuration
        print_status("Loading configuration...", "INFO")
        config = Config.load_from_file()
        
        # Verify we're in paper mode
        if config.run_mode != "PAPER":
            print_status(f"Warning: Config is set to {config.run_mode} mode", "WARNING")
            print_status("Switching to PAPER mode for testing...", "INFO")
            config.run_mode = "PAPER"
        
        print_status(f"Symbol: {config.symbol}", "INFO")
        print_status(f"Mode: {config.run_mode}", "INFO")
        
        # Run tests
        results = []
        
        # Test 1: Binance connection
        client, success = test_binance_connection(config)
        results.append(("Binance Connection", success))
        if not success:
            print_status("\n❌ Cannot proceed without Binance connection", "ERROR")
            return False
        
        # Test 2: Live price
        success = test_live_price_fetch(client, config.symbol)
        results.append(("Live Price Fetch", success))
        
        # Test 3: Historical data
        success = test_historical_data_fetch(config, client)
        results.append(("Historical Data Fetch", success))
        
        # Test 4: Indicators
        strategy, success = test_indicator_calculation(config, client)
        results.append(("Indicator Calculation", success))
        if not success:
            print_status("\n❌ Cannot test signals without indicators", "ERROR")
            return False
        
        # Test 5: Signal generation
        success = test_signal_generation(strategy, config)
        results.append(("Signal Generation", success))
        
        # Test 6: Advanced features
        success = test_advanced_features(strategy)
        results.append(("Advanced Features", success))
        
        # Summary
        print_header("📊 PRE-FLIGHT CHECK SUMMARY")
        
        all_passed = True
        for test_name, passed in results:
            status = "SUCCESS" if passed else "ERROR"
            print_status(f"{test_name}: {'PASSED' if passed else 'FAILED'}", status)
            if not passed:
                all_passed = False
        
        print("\n" + "="*70)
        if all_passed:
            print_status("✅ ALL CHECKS PASSED - READY FOR PAPER TRADING!", "SUCCESS")
            print("\nTo start paper trading, run:")
            print("  python start_paper_trading.py")
        else:
            print_status("❌ SOME CHECKS FAILED - PLEASE FIX ISSUES BEFORE PAPER TRADING", "ERROR")
            print("\nPlease review the errors above and fix them before proceeding.")
        print("="*70 + "\n")
        
        return all_passed
        
    except Exception as e:
        print_status(f"\n❌ Fatal error during pre-flight check: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
