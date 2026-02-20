"""Tests for Scaled Take Profit Analytics Module"""

import pytest
from src.scaled_tp_analytics import (
    ScaledTPAnalytics,
    TPLevelMetrics,
    ScaledTPPerformance,
    StrategyComparison
)


class TestScaledTPAnalytics:
    """Test suite for ScaledTPAnalytics class."""
    
    @pytest.fixture
    def analytics(self):
        """Create analytics instance."""
        return ScaledTPAnalytics()
    
    @pytest.fixture
    def sample_scaled_trades(self):
        """Create sample trades with scaled TP data."""
        return [
            {
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'pnl': 150.0,
                'tp_levels_hit': [1, 2, 3],
                'partial_exits': [
                    {'tp_level': 1, 'profit': 40.0, 'profit_pct': 0.03, 'quantity_closed': 0.04},
                    {'tp_level': 2, 'profit': 50.0, 'profit_pct': 0.05, 'quantity_closed': 0.03},
                    {'tp_level': 3, 'profit': 60.0, 'profit_pct': 0.08, 'quantity_closed': 0.03}
                ]
            },
            {
                'symbol': 'ETHUSDT',
                'side': 'LONG',
                'pnl': 80.0,
                'tp_levels_hit': [1, 2],
                'partial_exits': [
                    {'tp_level': 1, 'profit': 30.0, 'profit_pct': 0.03, 'quantity_closed': 0.04},
                    {'tp_level': 2, 'profit': 50.0, 'profit_pct': 0.05, 'quantity_closed': 0.03}
                ]
            },
            {
                'symbol': 'BTCUSDT',
                'side': 'SHORT',
                'pnl': 100.0,
                'tp_levels_hit': [1],
                'partial_exits': [
                    {'tp_level': 1, 'profit': 35.0, 'profit_pct': 0.03, 'quantity_closed': 0.04}
                ]
            }
        ]
    
    @pytest.fixture
    def sample_single_trades(self):
        """Create sample trades with single TP (no partial exits)."""
        return [
            {
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'pnl': 120.0,
                'exit_reason': 'TAKE_PROFIT'
            },
            {
                'symbol': 'ETHUSDT',
                'side': 'SHORT',
                'pnl': -50.0,
                'exit_reason': 'STOP_LOSS'
            },
            {
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'pnl': 90.0,
                'exit_reason': 'TAKE_PROFIT'
            }
        ]
    
    def test_calculate_tp_level_metrics(self, analytics, sample_scaled_trades):
        """Test calculation of TP level metrics."""
        metrics = analytics.calculate_tp_level_metrics(sample_scaled_trades, num_tp_levels=3)
        
        assert len(metrics) == 3
        
        # Check TP1 metrics
        tp1 = metrics[0]
        assert tp1.level == 1
        assert tp1.hit_count == 3  # All 3 trades hit TP1
        assert tp1.hit_rate == 100.0  # 3/3 = 100%
        assert tp1.total_profit == 105.0  # 40 + 30 + 35
        assert tp1.avg_profit == 35.0  # 105 / 3
        
        # Check TP2 metrics
        tp2 = metrics[1]
        assert tp2.level == 2
        assert tp2.hit_count == 2  # 2 trades hit TP2
        assert tp2.hit_rate == pytest.approx(66.67, rel=0.1)  # 2/3 = 66.67%
        assert tp2.total_profit == 100.0  # 50 + 50
        assert tp2.avg_profit == 50.0  # 100 / 2
        
        # Check TP3 metrics
        tp3 = metrics[2]
        assert tp3.level == 3
        assert tp3.hit_count == 1  # Only 1 trade hit TP3
        assert tp3.hit_rate == pytest.approx(33.33, rel=0.1)  # 1/3 = 33.33%
        assert tp3.total_profit == 60.0
        assert tp3.avg_profit == 60.0
    
    def test_calculate_tp_level_metrics_empty_trades(self, analytics):
        """Test TP level metrics with no trades."""
        metrics = analytics.calculate_tp_level_metrics([], num_tp_levels=3)
        
        assert len(metrics) == 0
    
    def test_calculate_tp_level_metrics_no_scaled_trades(self, analytics, sample_single_trades):
        """Test TP level metrics with only single TP trades."""
        metrics = analytics.calculate_tp_level_metrics(sample_single_trades, num_tp_levels=3)
        
        assert len(metrics) == 0
    
    def test_calculate_scaled_tp_performance(self, analytics, sample_scaled_trades):
        """Test calculation of overall scaled TP performance."""
        performance = analytics.calculate_scaled_tp_performance(sample_scaled_trades, num_tp_levels=3)
        
        assert performance is not None
        assert performance.total_trades == 3
        assert performance.total_profit == 330.0  # 150 + 80 + 100
        assert performance.avg_profit_per_trade == 110.0  # 330 / 3
        
        # Check average TP levels hit: (3 + 2 + 1) / 3 = 2.0
        assert performance.avg_tp_levels_hit == 2.0
        
        # Check full exit rate: 1 out of 3 hit all TPs = 33.33%
        assert performance.full_exit_rate == pytest.approx(33.33, rel=0.1)
        
        # Check TP level metrics are included
        assert len(performance.tp_level_metrics) == 3
    
    def test_calculate_scaled_tp_performance_no_scaled_trades(self, analytics, sample_single_trades):
        """Test scaled TP performance with no scaled trades."""
        performance = analytics.calculate_scaled_tp_performance(sample_single_trades, num_tp_levels=3)
        
        assert performance is None
    
    def test_compare_strategies(self, analytics, sample_scaled_trades, sample_single_trades):
        """Test strategy comparison between scaled and single TP."""
        all_trades = sample_scaled_trades + sample_single_trades
        comparison = analytics.compare_strategies(all_trades)
        
        assert comparison is not None
        
        # Check trade counts
        assert comparison.scaled_tp_trades == 3
        assert comparison.single_tp_trades == 3
        
        # Check scaled TP metrics
        assert comparison.scaled_tp_profit == 330.0  # 150 + 80 + 100
        assert comparison.scaled_tp_avg_profit == 110.0  # 330 / 3
        assert comparison.scaled_tp_win_rate == 100.0  # All 3 scaled trades are profitable
        
        # Check single TP metrics
        assert comparison.single_tp_profit == 160.0  # 120 + (-50) + 90
        assert comparison.single_tp_avg_profit == pytest.approx(53.33, rel=0.1)  # 160 / 3
        assert comparison.single_tp_win_rate == pytest.approx(66.67, rel=0.1)  # 2 out of 3 profitable
        
        # Check improvement calculation
        # (110 - 53.33) / 53.33 * 100 = 106.25%
        assert comparison.profit_improvement > 100.0
    
    def test_compare_strategies_no_scaled_trades(self, analytics, sample_single_trades):
        """Test strategy comparison with no scaled trades."""
        comparison = analytics.compare_strategies(sample_single_trades)
        
        assert comparison is None
    
    def test_compare_strategies_no_single_trades(self, analytics, sample_scaled_trades):
        """Test strategy comparison with no single TP trades."""
        comparison = analytics.compare_strategies(sample_scaled_trades)
        
        assert comparison is None
    
    def test_tp_level_metrics_with_varying_hits(self, analytics):
        """Test TP level metrics with trades hitting different levels."""
        trades = [
            {
                'pnl': 100.0,
                'tp_levels_hit': [1, 2, 3],
                'partial_exits': [
                    {'tp_level': 1, 'profit': 30.0, 'profit_pct': 0.03},
                    {'tp_level': 2, 'profit': 30.0, 'profit_pct': 0.05},
                    {'tp_level': 3, 'profit': 40.0, 'profit_pct': 0.08}
                ]
            },
            {
                'pnl': 60.0,
                'tp_levels_hit': [1, 2],
                'partial_exits': [
                    {'tp_level': 1, 'profit': 30.0, 'profit_pct': 0.03},
                    {'tp_level': 2, 'profit': 30.0, 'profit_pct': 0.05}
                ]
            },
            {
                'pnl': 30.0,
                'tp_levels_hit': [1],
                'partial_exits': [
                    {'tp_level': 1, 'profit': 30.0, 'profit_pct': 0.03}
                ]
            },
            {
                'pnl': 30.0,
                'tp_levels_hit': [1],
                'partial_exits': [
                    {'tp_level': 1, 'profit': 30.0, 'profit_pct': 0.03}
                ]
            }
        ]
        
        metrics = analytics.calculate_tp_level_metrics(trades, num_tp_levels=3)
        
        # TP1: 4 hits (100% hit rate)
        assert metrics[0].hit_count == 4
        assert metrics[0].hit_rate == 100.0
        
        # TP2: 2 hits (50% hit rate)
        assert metrics[1].hit_count == 2
        assert metrics[1].hit_rate == 50.0
        
        # TP3: 1 hit (25% hit rate)
        assert metrics[2].hit_count == 1
        assert metrics[2].hit_rate == 25.0
    
    def test_profit_improvement_calculation(self, analytics):
        """Test profit improvement calculation in strategy comparison."""
        trades = [
            # Scaled TP trades with higher avg profit
            {'pnl': 200.0, 'partial_exits': [{'tp_level': 1, 'profit': 200.0}]},
            {'pnl': 200.0, 'partial_exits': [{'tp_level': 1, 'profit': 200.0}]},
            # Single TP trades with lower avg profit
            {'pnl': 100.0},
            {'pnl': 100.0}
        ]
        
        comparison = analytics.compare_strategies(trades)
        
        assert comparison is not None
        assert comparison.scaled_tp_avg_profit == 200.0
        assert comparison.single_tp_avg_profit == 100.0
        # (200 - 100) / 100 * 100 = 100% improvement
        assert comparison.profit_improvement == 100.0
