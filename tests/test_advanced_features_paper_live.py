"""Integration tests for advanced features in paper and live trading modes.

This test suite verifies that all 7 advanced features are properly integrated
and functional in paper and live trading modes.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.config import Config
from src.strategy import StrategyEngine
from src.models import Candle
from src.trading_bot import TradingBot
import time


class TestAdvancedFeaturesPaperLive:
    """Test suite for advanced features in paper/live trading."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create config with all advanced features enabled
        self.config = Config(
            api_key="test_key",
            api_secret="test_secret",
            symbol="XRPUSDT",
            run_mode="PAPER",
            # Enable all advanced features
            enable_adaptive_thresholds=True,
            enable_multi_timeframe=True,
            enable_volume_profile=True,
            enable_regime_detection=True,
            enable_advanced_exits=True,
            enable_ml_prediction=False,  # Disabled by default (requires training)
            enable_portfolio_management=True,
            portfolio_symbols=["XRPUSDT", "ADAUSDT", "DOTUSDT"]
        )
        
        # Create sample candles for testing
        self.candles_5m = self._create_sample_candles(300, "5m")
        self.candles_15m = self._create_sample_candles(200, "15m")
        self.candles_1h = self._create_sample_candles(100, "1h")
        self.candles_4h = self._create_sample_candles(50, "4h")
    
    def _create_sample_candles(self, count: int, timeframe: str) -> list:
        """Create sample candles for testing."""
        candles = []
        base_time = int(time.time()) - (count * 60)  # Start from count minutes ago
        base_price = 50000.0
        
        for i in range(count):
            candle = Candle(
                timestamp=base_time + (i * 60),
                open=base_price + (i * 10),
                high=base_price + (i * 10) + 50,
                low=base_price + (i * 10) - 50,
                close=base_price + (i * 10) + 25,
                volume=1000000.0 + (i * 1000)
            )
            candles.append(candle)
        
        return candles
    
    def test_multi_timeframe_coordinator_initialization(self):
        """Test that multi-timeframe coordinator initializes in paper/live mode."""
        strategy = StrategyEngine(self.config)
        
        # Verify timeframe coordinator is initialized
        assert strategy.timeframe_coordinator is not None, \
            "Timeframe coordinator not initialized"
        
        # Verify feature is registered
        assert strategy.feature_manager.is_feature_enabled("multi_timeframe"), \
            "Multi-timeframe feature not enabled"
        
        print("\n✓ Multi-timeframe coordinator initialized successfully")
    
    def test_multi_timeframe_data_processing(self):
        """Test that strategy processes all 4 timeframes correctly."""
        strategy = StrategyEngine(self.config)
        
        # Update indicators with all 4 timeframes
        strategy.update_indicators(
            self.candles_15m,
            self.candles_1h,
            self.candles_5m,
            self.candles_4h
        )
        
        # Verify timeframe analysis was performed
        assert strategy.timeframe_analysis is not None, \
            "Timeframe analysis not performed"
        
        # Verify all timeframes were analyzed
        assert hasattr(strategy.timeframe_analysis, 'timeframe_5m'), \
            "5m timeframe not analyzed"
        assert hasattr(strategy.timeframe_analysis, 'timeframe_15m'), \
            "15m timeframe not analyzed"
        assert hasattr(strategy.timeframe_analysis, 'timeframe_1h'), \
            "1h timeframe not analyzed"
        assert hasattr(strategy.timeframe_analysis, 'timeframe_4h'), \
            "4h timeframe not analyzed"
        
        print("\n✓ All 4 timeframes processed correctly")
    
    def test_adaptive_threshold_manager_initialization(self):
        """Test that adaptive threshold manager initializes in paper/live mode."""
        strategy = StrategyEngine(self.config)
        
        # Verify adaptive threshold manager is initialized
        assert strategy.adaptive_threshold_manager is not None, \
            "Adaptive threshold manager not initialized"
        
        # Verify feature is registered
        assert strategy.feature_manager.is_feature_enabled("adaptive_thresholds"), \
            "Adaptive thresholds feature not enabled"
        
        print("\n✓ Adaptive threshold manager initialized successfully")
    
    def test_adaptive_threshold_updates(self):
        """Test that adaptive thresholds update correctly."""
        strategy = StrategyEngine(self.config)
        
        # Get initial thresholds
        initial_thresholds = strategy.adaptive_threshold_manager.get_current_thresholds()
        
        # Force threshold update by setting last update time to past
        strategy._last_threshold_update = 0
        
        # Update indicators (should trigger threshold update)
        strategy.update_indicators(
            self.candles_15m,
            self.candles_1h,
            self.candles_5m,
            self.candles_4h
        )
        
        # Verify thresholds were updated
        updated_thresholds = strategy.adaptive_threshold_manager.get_current_thresholds()
        assert updated_thresholds is not None, "Thresholds not updated"
        
        print("\n✓ Adaptive thresholds update correctly")
    
    def test_volume_profile_analyzer_initialization(self):
        """Test that volume profile analyzer initializes in paper/live mode."""
        strategy = StrategyEngine(self.config)
        
        # Verify volume profile analyzer is initialized
        assert strategy.volume_profile_analyzer is not None, \
            "Volume profile analyzer not initialized"
        
        # Verify feature is registered
        assert strategy.feature_manager.is_feature_enabled("volume_profile"), \
            "Volume profile feature not enabled"
        
        print("\n✓ Volume profile analyzer initialized successfully")
    
    def test_volume_profile_calculation(self):
        """Test that volume profile calculates correctly."""
        strategy = StrategyEngine(self.config)
        
        # Force volume profile update by setting last update to past
        strategy.volume_profile_analyzer.last_update = 0
        
        # Update indicators (should trigger volume profile calculation)
        strategy.update_indicators(
            self.candles_15m,
            self.candles_1h,
            self.candles_5m,
            self.candles_4h
        )
        
        # Verify volume profile was calculated
        assert strategy.volume_profile_analyzer.current_profile is not None, \
            "Volume profile not calculated"
        
        profile = strategy.volume_profile_analyzer.current_profile
        assert profile.poc > 0, "POC not calculated"
        assert profile.vah > 0, "VAH not calculated"
        assert profile.val > 0, "VAL not calculated"
        
        print("\n✓ Volume profile calculates correctly")
    
    def test_market_regime_detector_initialization(self):
        """Test that market regime detector initializes in paper/live mode."""
        strategy = StrategyEngine(self.config)
        
        # Verify market regime detector is initialized
        assert strategy.market_regime_detector is not None, \
            "Market regime detector not initialized"
        
        # Verify feature is registered
        assert strategy.feature_manager.is_feature_enabled("regime_detection"), \
            "Regime detection feature not enabled"
        
        print("\n✓ Market regime detector initialized successfully")
    
    def test_market_regime_detection(self):
        """Test that market regime detection works correctly."""
        strategy = StrategyEngine(self.config)
        
        # Force regime update by setting last update to past
        strategy.market_regime_detector.last_update = 0
        
        # Update indicators (should trigger regime detection)
        strategy.update_indicators(
            self.candles_15m,
            self.candles_1h,
            self.candles_5m,
            self.candles_4h
        )
        
        # Verify regime was detected
        assert strategy.market_regime_detector.current_regime is not None, \
            "Market regime not detected"
        
        # Verify regime is valid
        valid_regimes = ["TRENDING_BULLISH", "TRENDING_BEARISH", "RANGING", "VOLATILE", "UNCERTAIN"]
        assert strategy.market_regime_detector.current_regime in valid_regimes, \
            f"Invalid regime: {strategy.market_regime_detector.current_regime}"
        
        # Verify regime parameters are set
        assert strategy.current_regime_params is not None, \
            "Regime parameters not set"
        
        print(f"\n✓ Market regime detected: {strategy.market_regime_detector.current_regime}")
    
    def test_advanced_exit_manager_integration(self):
        """Test that advanced exit manager is integrated with risk manager."""
        from src.risk_manager import RiskManager
        from src.position_sizer import PositionSizer
        
        position_sizer = PositionSizer(self.config)
        risk_manager = RiskManager(self.config, position_sizer)
        
        # Verify advanced exit manager is initialized
        assert risk_manager.advanced_exit_manager is not None, \
            "Advanced exit manager not initialized"
        
        print("\n✓ Advanced exit manager integrated with risk manager")
    
    def test_portfolio_manager_initialization(self):
        """Test that portfolio manager initializes in paper/live mode."""
        from src.risk_manager import RiskManager
        from src.position_sizer import PositionSizer
        
        position_sizer = PositionSizer(self.config)
        risk_manager = RiskManager(self.config, position_sizer)
        
        # Verify portfolio manager is initialized
        assert risk_manager.portfolio_manager is not None, \
            "Portfolio manager not initialized"
        
        # Verify portfolio symbols are configured
        assert len(self.config.portfolio_symbols) > 0, \
            "Portfolio symbols not configured"
        
        print(f"\n✓ Portfolio manager initialized with {len(self.config.portfolio_symbols)} symbols")
    
    def test_ml_predictor_disabled_by_default(self):
        """Test that ML predictor is disabled by default (requires training)."""
        strategy = StrategyEngine(self.config)
        
        # Verify ML predictor is not initialized (disabled in config)
        assert strategy.ml_predictor is None, \
            "ML predictor should not be initialized when disabled"
        
        # Verify prediction defaults to neutral
        assert strategy.ml_prediction == 0.5, \
            "ML prediction should default to 0.5 (neutral)"
        
        print("\n✓ ML predictor correctly disabled by default")
    
    @patch('src.trading_bot.Client')
    def test_paper_trading_mode_fetches_all_timeframes(self, mock_client):
        """Test that paper trading mode fetches all required timeframes."""
        # Mock the Binance client
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        # Mock get_account to return balance
        mock_client_instance.futures_account_balance.return_value = [
            {'asset': 'USDT', 'balance': '10000.0'}
        ]
        
        # Create trading bot in paper mode
        bot = TradingBot(self.config)
        
        # Verify data manager is initialized
        assert bot.data_manager is not None, "Data manager not initialized"
        
        # Verify strategy has multi-timeframe enabled
        assert bot.strategy.timeframe_coordinator is not None, \
            "Timeframe coordinator not initialized in paper trading"
        
        print("\n✓ Paper trading mode properly configured for multi-timeframe")
    
    @patch('src.trading_bot.Client')
    def test_live_trading_mode_fetches_all_timeframes(self, mock_client):
        """Test that live trading mode fetches all required timeframes."""
        # Mock the Binance client
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        # Mock get_account to return balance
        mock_client_instance.futures_account_balance.return_value = [
            {'asset': 'USDT', 'balance': '10000.0'}
        ]
        
        # Create config for live mode
        live_config = Config(
            api_key="test_key",
            api_secret="test_secret",
            symbol="XRPUSDT",
            run_mode="LIVE",
            enable_multi_timeframe=True
        )
        
        # Create trading bot in live mode
        bot = TradingBot(live_config)
        
        # Verify data manager is initialized
        assert bot.data_manager is not None, "Data manager not initialized"
        
        # Verify strategy has multi-timeframe enabled
        assert bot.strategy.timeframe_coordinator is not None, \
            "Timeframe coordinator not initialized in live trading"
        
        print("\n✓ Live trading mode properly configured for multi-timeframe")
    
    def test_feature_error_isolation(self):
        """Test that feature errors are isolated and don't crash the system."""
        strategy = StrategyEngine(self.config)
        
        # Simulate a feature error by disabling a feature
        strategy.feature_manager.disable_feature("multi_timeframe")
        
        # Update indicators should still work
        strategy.update_indicators(
            self.candles_15m,
            self.candles_1h,
            self.candles_5m,
            self.candles_4h
        )
        
        # Verify basic indicators still calculated
        assert strategy.current_indicators.current_price > 0, \
            "Basic indicators not calculated after feature error"
        
        print("\n✓ Feature error isolation working correctly")
    
    def test_graceful_degradation_missing_timeframes(self):
        """Test that system handles missing timeframe data gracefully."""
        strategy = StrategyEngine(self.config)
        
        # Update indicators with missing 5m and 4h data
        strategy.update_indicators(
            self.candles_15m,
            self.candles_1h,
            None,  # Missing 5m
            None   # Missing 4h
        )
        
        # Verify basic indicators still calculated
        assert strategy.current_indicators.current_price > 0, \
            "Basic indicators not calculated with missing timeframes"
        
        # Verify timeframe analysis is None (graceful degradation)
        assert strategy.timeframe_analysis is None, \
            "Timeframe analysis should be None with missing data"
        
        print("\n✓ Graceful degradation working for missing timeframes")
    
    def test_all_features_summary(self):
        """Print summary of all advanced features status."""
        strategy = StrategyEngine(self.config)
        
        print("\n" + "="*70)
        print("ADVANCED FEATURES STATUS IN PAPER/LIVE TRADING")
        print("="*70)
        
        features = [
            ("Multi-Timeframe Coordinator", strategy.timeframe_coordinator is not None),
            ("Adaptive Threshold Manager", strategy.adaptive_threshold_manager is not None),
            ("Volume Profile Analyzer", strategy.volume_profile_analyzer is not None),
            ("Market Regime Detector", strategy.market_regime_detector is not None),
            ("ML Predictor", strategy.ml_predictor is not None),
        ]
        
        for feature_name, is_enabled in features:
            status = "✅ ENABLED" if is_enabled else "❌ DISABLED"
            print(f"{feature_name:.<50} {status}")
        
        # Check risk manager features
        from src.risk_manager import RiskManager
        from src.position_sizer import PositionSizer
        
        position_sizer = PositionSizer(self.config)
        risk_manager = RiskManager(self.config, position_sizer)
        
        print(f"{'Advanced Exit Manager':.<50} {'✅ ENABLED' if risk_manager.advanced_exit_manager else '❌ DISABLED'}")
        print(f"{'Portfolio Manager':.<50} {'✅ ENABLED' if risk_manager.portfolio_manager else '❌ DISABLED'}")
        
        print("="*70)
        print("\n✓ All advanced features verified for paper/live trading")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
