"""
Streamlit Chart Generator

Creates interactive charts for the dashboard using Plotly.
Provides price charts, PnL charts, and other visualizations.
"""

import plotly.graph_objects as go
from typing import List, Dict, Optional
from datetime import datetime


class ChartGenerator:
    """Generates charts for the dashboard."""
    
    def create_price_chart(
        self,
        candles: List[Dict],
        positions: Optional[List[Dict]] = None,
        atr_bands: Optional[Dict] = None
    ) -> go.Figure:
        """
        Create candlestick chart with overlays.
        
        Args:
            candles: List of candle dictionaries with OHLC data
            positions: Optional list of position dictionaries
            atr_bands: Optional dictionary with ATR band data
            
        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        
        if not candles:
            fig.add_annotation(
                text="No data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )
            return fig
        
        # Add candlesticks
        fig.add_trace(go.Candlestick(
            x=[c.get('timestamp', c.get('time', '')) for c in candles],
            open=[c['open'] for c in candles],
            high=[c['high'] for c in candles],
            low=[c['low'] for c in candles],
            close=[c['close'] for c in candles],
            name="Price"
        ))
        
        # Add ATR bands if provided
        if atr_bands and 'timestamps' in atr_bands:
            fig.add_trace(go.Scatter(
                x=atr_bands['timestamps'],
                y=atr_bands.get('upper', []),
                name="ATR Upper",
                line=dict(dash='dash', color='gray'),
                opacity=0.5
            ))
            fig.add_trace(go.Scatter(
                x=atr_bands['timestamps'],
                y=atr_bands.get('lower', []),
                name="ATR Lower",
                line=dict(dash='dash', color='gray'),
                opacity=0.5,
                fill='tonexty',
                fillcolor='rgba(128, 128, 128, 0.1)'
            ))
        
        # Mark position entries
        if positions:
            for pos in positions:
                entry_time = pos.get('entry_time', pos.get('timestamp', ''))
                entry_price = pos.get('entry_price', 0)
                side = pos.get('side', 'LONG')
                
                if entry_time and entry_price:
                    fig.add_trace(go.Scatter(
                        x=[entry_time],
                        y=[entry_price],
                        mode='markers',
                        marker=dict(
                            size=12,
                            symbol='triangle-up' if side == 'LONG' else 'triangle-down',
                            color='green' if side == 'LONG' else 'red',
                            line=dict(width=2, color='white')
                        ),
                        name=f"{side} Entry",
                        showlegend=True
                    ))
        
        fig.update_layout(
            title="Price Chart",
            xaxis_title="Time",
            yaxis_title="Price (USDT)",
            height=600,
            xaxis_rangeslider_visible=False,
            hovermode='x unified'
        )
        
        return fig
    
    def create_pnl_chart(self, trades: List[Dict]) -> go.Figure:
        """
        Create cumulative PnL chart.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        
        if not trades:
            fig.add_annotation(
                text="No trade data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )
            return fig
        
        cumulative_pnl = []
        running_total = 0
        timestamps = []
        
        for trade in trades:
            pnl = trade.get('pnl', 0)
            exit_time = trade.get('exit_time', trade.get('timestamp', ''))
            
            running_total += pnl
            cumulative_pnl.append(running_total)
            timestamps.append(exit_time)
        
        # Determine fill color based on final PnL
        fill_color = 'rgba(0, 255, 0, 0.2)' if running_total >= 0 else 'rgba(255, 0, 0, 0.2)'
        line_color = 'green' if running_total >= 0 else 'red'
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=cumulative_pnl,
            mode='lines',
            fill='tozeroy',
            fillcolor=fill_color,
            line=dict(color=line_color, width=2),
            name="Cumulative PnL"
        ))
        
        fig.update_layout(
            title="Cumulative PnL Over Time",
            xaxis_title="Time",
            yaxis_title="PnL (USDT)",
            height=400,
            hovermode='x unified'
        )
        
        return fig
    
    def create_win_rate_chart(self, trades: List[Dict]) -> go.Figure:
        """
        Create win rate visualization chart.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        
        if not trades:
            fig.add_annotation(
                text="No trade data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )
            return fig
        
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        losses = sum(1 for t in trades if t.get('pnl', 0) < 0)
        breakeven = len(trades) - wins - losses
        
        fig.add_trace(go.Pie(
            labels=['Wins', 'Losses', 'Breakeven'],
            values=[wins, losses, breakeven],
            marker=dict(colors=['green', 'red', 'gray']),
            hole=0.4
        ))
        
        fig.update_layout(
            title="Win/Loss Distribution",
            height=400
        )
        
        return fig
