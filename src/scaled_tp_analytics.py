"""Scaled Take Profit Analytics Module

This module provides analytics and performance metrics for the scaled take profit strategy.
It calculates metrics like average profit per TP level, hit rates, and comparisons between
scaled TP and single TP performance.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TPLevelMetrics:
    """Metrics for a single TP level.
    
    Attributes:
        level: TP level number (1, 2, 3, etc.)
        hit_count: Number of times this TP level was hit
        total_profit: Total profit from this TP level across all trades
        avg_profit: Average profit per hit for this TP level
        avg_profit_pct: Average profit percentage per hit
        hit_rate: Percentage of trades that reached this TP level
    """
    level: int
    hit_count: int
    total_profit: float
    avg_profit: float
    avg_profit_pct: float
    hit_rate: float


@dataclass
class ScaledTPPerformance:
    """Overall performance metrics for scaled TP strategy.
    
    Attributes:
        total_trades: Total number of trades with scaled TP
        total_profit: Total profit from all scaled TP trades
        avg_profit_per_trade: Average profit per trade
        tp_level_metrics: List of metrics for each TP level
        avg_tp_levels_hit: Average number of TP levels hit per trade
        full_exit_rate: Percentage of trades that hit all TP levels
    """
    total_trades: int
    total_profit: float
    avg_profit_per_trade: float
    tp_level_metrics: List[TPLevelMetrics]
    avg_tp_levels_hit: float
    full_exit_rate: float


@dataclass
class StrategyComparison:
    """Comparison between scaled TP and single TP strategies.
    
    Attributes:
        scaled_tp_trades: Number of trades using scaled TP
        single_tp_trades: Number of trades using single TP
        scaled_tp_profit: Total profit from scaled TP trades
        single_tp_profit: Total profit from single TP trades
        scaled_tp_win_rate: Win rate for scaled TP trades
        single_tp_win_rate: Win rate for single TP trades
        scaled_tp_avg_profit: Average profit per trade for scaled TP
        single_tp_avg_profit: Average profit per trade for single TP
        profit_improvement: Percentage improvement in profit (scaled vs single)
    """
    scaled_tp_trades: int
    single_tp_trades: int
    scaled_tp_profit: float
    single_tp_profit: float
    scaled_tp_win_rate: float
    single_tp_win_rate: float
    scaled_tp_avg_profit: float
    single_tp_avg_profit: float
    profit_improvement: float


class ScaledTPAnalytics:
    """Analytics calculator for scaled take profit strategy."""
    
    def __init__(self):
        """Initialize the analytics calculator."""
        pass
    
    def calculate_tp_level_metrics(
        self,
        trades: List[Dict],
        num_tp_levels: int = 3
    ) -> List[TPLevelMetrics]:
        """Calculate metrics for each TP level.
        
        Args:
            trades: List of trade dictionaries with partial_exits data
            num_tp_levels: Number of TP levels configured (default 3)
            
        Returns:
            List of TPLevelMetrics, one for each TP level
        """
        # Filter trades that have partial exits (scaled TP trades)
        scaled_trades = [t for t in trades if t.get('partial_exits')]
        
        if not scaled_trades:
            return []
        
        total_scaled_trades = len(scaled_trades)
        
        # Initialize metrics for each TP level
        tp_metrics = []
        
        for level in range(1, num_tp_levels + 1):
            hit_count = 0
            total_profit = 0.0
            total_profit_pct = 0.0
            
            # Count hits and sum profits for this TP level
            for trade in scaled_trades:
                partial_exits = trade.get('partial_exits', [])
                
                # Find this TP level in partial exits
                for exit_data in partial_exits:
                    if exit_data.get('tp_level') == level:
                        hit_count += 1
                        total_profit += exit_data.get('profit', 0.0)
                        total_profit_pct += exit_data.get('profit_pct', 0.0)
                        break
            
            # Calculate averages
            avg_profit = total_profit / hit_count if hit_count > 0 else 0.0
            avg_profit_pct = (total_profit_pct / hit_count * 100) if hit_count > 0 else 0.0
            hit_rate = (hit_count / total_scaled_trades * 100) if total_scaled_trades > 0 else 0.0
            
            tp_metrics.append(TPLevelMetrics(
                level=level,
                hit_count=hit_count,
                total_profit=total_profit,
                avg_profit=avg_profit,
                avg_profit_pct=avg_profit_pct,
                hit_rate=hit_rate
            ))
        
        return tp_metrics
    
    def calculate_scaled_tp_performance(
        self,
        trades: List[Dict],
        num_tp_levels: int = 3
    ) -> Optional[ScaledTPPerformance]:
        """Calculate overall performance metrics for scaled TP strategy.
        
        Args:
            trades: List of trade dictionaries
            num_tp_levels: Number of TP levels configured (default 3)
            
        Returns:
            ScaledTPPerformance object with metrics, or None if no scaled TP trades
        """
        # Filter trades that have partial exits (scaled TP trades)
        scaled_trades = [t for t in trades if t.get('partial_exits')]
        
        if not scaled_trades:
            return None
        
        total_trades = len(scaled_trades)
        
        # Calculate total profit from scaled TP trades
        total_profit = 0.0
        total_tp_levels_hit = 0
        full_exit_count = 0
        
        for trade in scaled_trades:
            # Sum profit from all partial exits
            partial_exits = trade.get('partial_exits', [])
            trade_profit = sum(pe.get('profit', 0.0) for pe in partial_exits)
            
            # Add final exit profit if there was remaining quantity
            final_pnl = trade.get('pnl', 0.0)
            if final_pnl != 0:
                # This includes the final exit
                total_profit += final_pnl
            else:
                # No final exit, just sum partials
                total_profit += trade_profit
            
            # Count TP levels hit
            tp_levels_hit = trade.get('tp_levels_hit', [])
            total_tp_levels_hit += len(tp_levels_hit)
            
            # Check if all TP levels were hit
            if len(tp_levels_hit) >= num_tp_levels:
                full_exit_count += 1
        
        # Calculate averages
        avg_profit_per_trade = total_profit / total_trades if total_trades > 0 else 0.0
        avg_tp_levels_hit = total_tp_levels_hit / total_trades if total_trades > 0 else 0.0
        full_exit_rate = (full_exit_count / total_trades * 100) if total_trades > 0 else 0.0
        
        # Get TP level metrics
        tp_level_metrics = self.calculate_tp_level_metrics(trades, num_tp_levels)
        
        return ScaledTPPerformance(
            total_trades=total_trades,
            total_profit=total_profit,
            avg_profit_per_trade=avg_profit_per_trade,
            tp_level_metrics=tp_level_metrics,
            avg_tp_levels_hit=avg_tp_levels_hit,
            full_exit_rate=full_exit_rate
        )
    
    def compare_strategies(
        self,
        trades: List[Dict]
    ) -> Optional[StrategyComparison]:
        """Compare performance between scaled TP and single TP strategies.
        
        Args:
            trades: List of all trade dictionaries
            
        Returns:
            StrategyComparison object with comparison metrics, or None if insufficient data
        """
        # Separate trades by strategy
        scaled_trades = [t for t in trades if t.get('partial_exits')]
        single_trades = [t for t in trades if not t.get('partial_exits')]
        
        # Need both types of trades for comparison
        if not scaled_trades or not single_trades:
            return None
        
        # Calculate metrics for scaled TP trades
        scaled_count = len(scaled_trades)
        scaled_profit = sum(t.get('pnl', 0.0) for t in scaled_trades)
        scaled_wins = sum(1 for t in scaled_trades if t.get('pnl', 0.0) > 0)
        scaled_win_rate = (scaled_wins / scaled_count * 100) if scaled_count > 0 else 0.0
        scaled_avg_profit = scaled_profit / scaled_count if scaled_count > 0 else 0.0
        
        # Calculate metrics for single TP trades
        single_count = len(single_trades)
        single_profit = sum(t.get('pnl', 0.0) for t in single_trades)
        single_wins = sum(1 for t in single_trades if t.get('pnl', 0.0) > 0)
        single_win_rate = (single_wins / single_count * 100) if single_count > 0 else 0.0
        single_avg_profit = single_profit / single_count if single_count > 0 else 0.0
        
        # Calculate improvement
        if single_avg_profit != 0:
            profit_improvement = ((scaled_avg_profit - single_avg_profit) / abs(single_avg_profit)) * 100
        else:
            profit_improvement = 0.0
        
        return StrategyComparison(
            scaled_tp_trades=scaled_count,
            single_tp_trades=single_count,
            scaled_tp_profit=scaled_profit,
            single_tp_profit=single_profit,
            scaled_tp_win_rate=scaled_win_rate,
            single_tp_win_rate=single_win_rate,
            scaled_tp_avg_profit=scaled_avg_profit,
            single_tp_avg_profit=single_avg_profit,
            profit_improvement=profit_improvement
        )
