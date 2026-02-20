"""
Streamlit Trading Dashboard - Main Entry Point

This is the main entry point for the Streamlit-based trading bot dashboard.
It provides real-time monitoring, bot control, and configuration management.
"""

import time
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from src.streamlit_data_provider import StreamlitDataProvider


def main():
    """Main dashboard entry point."""
    st.set_page_config(
        page_title="Trading Bot Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed"  # Collapse sidebar since we're using top navigation
    )
    
    # Auto-refresh every 5 seconds (5000 milliseconds)
    st_autorefresh(interval=5000, key="datarefresh")
    
    # Top navigation toolbar using tabs
    st.title("📈 Trading Bot Dashboard")
    
    # Create horizontal navigation tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🏠 Dashboard",
        "📊 Positions", 
        "📉 Market Data",
        "📈 Charts",
        "📜 Trade History",
        "📊 Analytics",
        "⚙️ Settings",
        "🎮 Controls"
    ])
    
    # Route to appropriate page based on active tab
    with tab1:
        show_dashboard_page()
    
    with tab2:
        show_positions_page()
    
    with tab3:
        show_market_data_page()
    
    with tab4:
        show_chart_page()
    
    with tab5:
        show_trade_history_page()
    
    with tab6:
        show_analytics_page()
    
    with tab7:
        show_settings_page()
    
    with tab8:
        show_controls_page()


def show_dashboard_page():
    """Display main dashboard page."""
    # Initialize data provider
    data_provider = StreamlitDataProvider()
    
    # Get bot status
    bot_status = data_provider.get_bot_status()
    balance_pnl = data_provider.get_balance_and_pnl()
    
    # Display bot status with warning if stopped
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Bot Status")
        if bot_status["is_running"]:
            st.success(f"✅ {bot_status['status']}")
        else:
            st.error(f"⚠️ {bot_status['status']}")
            st.warning("Bot is not running! Go to Controls to start it.")
        
        if bot_status["last_update"]:
            st.caption(f"Last update: {bot_status['last_update'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.caption("Last update: N/A")
    
    with col2:
        st.subheader("Balance")
        balance = balance_pnl.get("balance", 0.0)
        st.metric("Current Balance", f"${balance:,.2f} USDT")
    
    with col3:
        st.subheader("Total PnL")
        total_pnl = balance_pnl.get("total_pnl", 0.0)
        total_pnl_percent = balance_pnl.get("total_pnl_percent", 0.0)
        
        # Color code based on PnL
        if total_pnl > 0:
            st.metric("Total PnL", f"${total_pnl:,.2f} USDT", f"+{total_pnl_percent:.2f}%")
        elif total_pnl < 0:
            st.metric("Total PnL", f"${total_pnl:,.2f} USDT", f"{total_pnl_percent:.2f}%")
        else:
            st.metric("Total PnL", f"${total_pnl:,.2f} USDT", f"{total_pnl_percent:.2f}%")
    
    st.divider()
    
    # Quick overview section
    st.subheader("Quick Overview")
    
    # Get open positions and results data
    positions = data_provider.get_open_positions()
    results = data_provider._read_cached_json(data_provider.results_path, "results")
    symbols_data = results.get('symbols_data', [])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Open Positions", len(positions))
    
    with col2:
        # Show total symbols being tracked
        st.metric("Symbols Tracked", len(symbols_data) if symbols_data else 1)
    
    with col3:
        # Count active signals across all symbols
        active_signals = sum(1 for s in symbols_data if s.get('signal', 'NONE') != 'NONE')
        st.metric("Active Signals", active_signals)
    
    with col4:
        # Show average ADX across all symbols
        if symbols_data:
            avg_adx = sum(s.get('adx', 0) for s in symbols_data) / len(symbols_data)
            st.metric("Avg ADX", f"{avg_adx:.2f}")
        else:
            market_data = data_provider.get_market_data()
            st.metric("ADX", f"{market_data.get('adx', 0.0):.2f}")
    
    st.divider()
    
    # Show per-symbol market data if available
    if symbols_data and len(symbols_data) > 1:
        st.subheader("Market Data by Symbol")
        
        # Create columns for each symbol (max 3 per row)
        for i in range(0, len(symbols_data), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(symbols_data):
                    symbol_info = symbols_data[i + j]
                    with col:
                        symbol = symbol_info.get('symbol', 'N/A')
                        price = symbol_info.get('current_price', 0.0)
                        signal = symbol_info.get('signal', 'NONE')
                        adx = symbol_info.get('adx', 0.0)
                        
                        # Color code based on signal
                        if signal == 'LONG':
                            st.success(f"**{symbol}**")
                            st.write(f"🟢 {signal}")
                        elif signal == 'SHORT':
                            st.error(f"**{symbol}**")
                            st.write(f"🔴 {signal}")
                        else:
                            st.info(f"**{symbol}**")
                            st.write(f"⚪ {signal}")
                        
                        st.write(f"${price:,.4f}")
                        st.caption(f"ADX: {adx:.1f}")
        
        st.divider()
    
    # Recent positions summary
    if positions:
        st.subheader("Open Positions Summary")
        
        # Get config for scaled TP info
        config = data_provider.get_config()
        scaled_tp_enabled = config.get('enable_scaled_take_profit', False)
        scaled_tp_levels = config.get('scaled_tp_levels', [])
        
        for pos in positions:
            symbol = pos.get('symbol', 'N/A')
            side = pos.get('side', 'N/A')
            entry_price = pos.get('entry_price', 0.0)
            current_price = pos.get('current_price', 0.0)
            quantity = pos.get('quantity', 0.0)
            unrealized_pnl = pos.get('unrealized_pnl', 0.0)
            stop_loss = pos.get('stop_loss', 0.0)
            trailing_stop = pos.get('trailing_stop', 0.0)
            
            # Scaled TP data
            tp_levels_hit = pos.get('tp_levels_hit', [])
            original_quantity = pos.get('original_quantity', quantity)
            
            # Calculate PnL percentage
            if entry_price > 0:
                if side == "LONG":
                    pnl_percent = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl_percent = ((entry_price - current_price) / entry_price) * 100
            else:
                pnl_percent = 0.0
            
            # Add TP progress to title if scaled TP is enabled
            title_suffix = ""
            if scaled_tp_enabled and tp_levels_hit:
                title_suffix = f" | TP: {len(tp_levels_hit)}/{len(scaled_tp_levels)} ✓"
            
            with st.expander(f"{symbol} - {side} | PnL: ${unrealized_pnl:,.2f} ({pnl_percent:+.2f}%){title_suffix}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Entry Price:** ${entry_price:,.6f}")
                    st.write(f"**Current Price:** ${current_price:,.6f}")
                    
                    # Show original vs remaining if scaled TP is active
                    if scaled_tp_enabled and original_quantity > 0 and original_quantity != quantity:
                        remaining_pct = (quantity / original_quantity) * 100
                        st.write(f"**Remaining:** {remaining_pct:.1f}% of original")
                
                with col2:
                    st.write(f"**Quantity:** {quantity:.4f}")
                    if unrealized_pnl > 0:
                        st.write(f"**Unrealized PnL:** :green[${unrealized_pnl:,.2f} (+{pnl_percent:.2f}%)]")
                    elif unrealized_pnl < 0:
                        st.write(f"**Unrealized PnL:** :red[${unrealized_pnl:,.2f} ({pnl_percent:.2f}%)]")
                    else:
                        st.write(f"**Unrealized PnL:** ${unrealized_pnl:,.2f} ({pnl_percent:.2f}%)")
                
                with col3:
                    st.write(f"**Stop Loss:** ${stop_loss:,.6f}")
                    st.write(f"**Trailing Stop:** ${trailing_stop:,.6f}")
                
                # Show TP progress if scaled TP is enabled
                if scaled_tp_enabled and scaled_tp_levels:
                    st.divider()
                    st.write("**Take Profit Progress:**")
                    
                    # Create a simple progress indicator
                    tp_status = []
                    for i in range(1, len(scaled_tp_levels) + 1):
                        if i in tp_levels_hit:
                            tp_status.append("✅")
                        else:
                            tp_status.append("⏳")
                    
                    st.write(" ".join([f"TP{i+1}: {status}" for i, status in enumerate(tp_status)]))
                    
                    # Show next target
                    if tp_levels_hit and len(tp_levels_hit) < len(scaled_tp_levels):
                        next_tp_idx = len(tp_levels_hit)
                        next_tp = scaled_tp_levels[next_tp_idx]
                        next_profit_pct = next_tp.get('profit_pct', 0.0)
                        
                        if side == "LONG":
                            next_target = entry_price * (1 + next_profit_pct)
                        else:
                            next_target = entry_price * (1 - next_profit_pct)
                        
                        st.caption(f"Next: TP{next_tp_idx + 1} at ${next_target:,.6f}")
    else:
        st.info("No open positions")
    
    st.divider()
    st.caption("Dashboard auto-refreshes every 5 seconds")


def show_positions_page():
    """Display positions page."""
    # Initialize data provider
    data_provider = StreamlitDataProvider()
    
    # Get open positions and balance
    positions = data_provider.get_open_positions()
    balance_pnl = data_provider.get_balance_and_pnl()
    config = data_provider.get_config()
    
    # Check if scaled TP is enabled
    scaled_tp_enabled = config.get('enable_scaled_take_profit', False)
    scaled_tp_levels = config.get('scaled_tp_levels', [])
    
    if not positions:
        st.info("No open positions")
        return
    
    # Calculate total unrealized PnL
    total_unrealized_pnl = sum(pos.get('unrealized_pnl', 0.0) for pos in positions)
    total_pnl = balance_pnl.get('total_pnl', 0.0)
    
    # Display summary metrics
    st.subheader("Portfolio Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Open Positions", len(positions))
    
    with col2:
        st.metric("Total Unrealized PnL", f"${total_unrealized_pnl:,.2f}", 
                 delta=f"{(total_unrealized_pnl / balance_pnl.get('balance', 1) * 100):+.2f}%")
    
    with col3:
        st.metric("Total Realized PnL", f"${total_pnl:,.2f}",
                 delta=f"{balance_pnl.get('total_pnl_percent', 0):+.2f}%")
    
    with col4:
        combined_pnl = total_unrealized_pnl + total_pnl
        st.metric("Combined PnL", f"${combined_pnl:,.2f}",
                 delta=f"{(combined_pnl / balance_pnl.get('balance', 1) * 100):+.2f}%")
    
    st.divider()
    
    # Display positions in a table format
    st.subheader(f"Position Details ({len(positions)} Open)")
    
    for idx, pos in enumerate(positions, 1):
        # Extract position data
        symbol = pos.get('symbol', 'N/A')
        side = pos.get('side', 'N/A')
        entry_price = pos.get('entry_price', 0.0)
        current_price = pos.get('current_price', 0.0)
        quantity = pos.get('quantity', 0.0)
        unrealized_pnl = pos.get('unrealized_pnl', 0.0)
        stop_loss = pos.get('stop_loss', 0.0)
        trailing_stop = pos.get('trailing_stop', 0.0)
        entry_time = pos.get('entry_time', '')
        
        # Scaled TP data
        original_quantity = pos.get('original_quantity', quantity)
        tp_levels_hit = pos.get('tp_levels_hit', [])
        partial_exits = pos.get('partial_exits', [])
        
        # Calculate PnL percentage
        if entry_price > 0:
            pnl_percent = (unrealized_pnl / (entry_price * quantity)) * 100
            price_change = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_percent = 0.0
            price_change = 0.0
        
        # Create expandable section for each position
        pnl_indicator = "🟢" if unrealized_pnl > 0 else "🔴" if unrealized_pnl < 0 else "⚪"
        
        # Add scaled TP indicator to title if enabled and has partial exits
        title_suffix = ""
        if scaled_tp_enabled and tp_levels_hit:
            title_suffix = f" | TP: {len(tp_levels_hit)}/{len(scaled_tp_levels)} ✓"
        
        with st.expander(f"Position {idx}: {symbol} {side} - {pnl_indicator} ${unrealized_pnl:,.2f} ({pnl_percent:+.2f}%){title_suffix}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**Position Info**")
                st.metric("Symbol", symbol)
                st.metric("Side", side)
                st.metric("Quantity", f"{quantity:.4f}")
                
                # Show original vs remaining if scaled TP is active
                if scaled_tp_enabled and original_quantity > 0 and original_quantity != quantity:
                    remaining_pct = (quantity / original_quantity) * 100
                    st.write(f"**Original Qty:** {original_quantity:.4f}")
                    st.write(f"**Remaining:** {remaining_pct:.1f}%")
                
                # Calculate position value
                position_value = entry_price * quantity
                st.write(f"**Position Value:** ${position_value:,.2f}")
            
            with col2:
                st.write("**Prices**")
                st.metric("Entry Price", f"${entry_price:,.6f}")
                st.metric("Current Price", f"${current_price:,.6f}", delta=f"{price_change:+.2f}%")
                st.metric("Stop Loss", f"${stop_loss:,.6f}")
                st.metric("Trailing Stop", f"${trailing_stop:,.6f}")
            
            with col3:
                st.write("**Performance**")
                
                # Unrealized PnL with color coding
                if unrealized_pnl > 0:
                    st.metric("Unrealized PnL", f"${unrealized_pnl:,.2f}", 
                             delta=f"+{pnl_percent:.2f}%", delta_color="normal")
                elif unrealized_pnl < 0:
                    st.metric("Unrealized PnL", f"${unrealized_pnl:,.2f}", 
                             delta=f"{pnl_percent:.2f}%", delta_color="inverse")
                else:
                    st.metric("Unrealized PnL", f"${unrealized_pnl:,.2f}", 
                             delta=f"{pnl_percent:.2f}%", delta_color="off")
                
                # Calculate distance to stops
                if current_price > 0:
                    stop_distance = abs(current_price - stop_loss) / current_price * 100
                    trailing_distance = abs(current_price - trailing_stop) / current_price * 100
                    st.write(f"**Stop Distance:** {stop_distance:.2f}%")
                    st.write(f"**Trailing Distance:** {trailing_distance:.2f}%")
            
            # Scaled Take Profit Progress (if enabled)
            if scaled_tp_enabled and scaled_tp_levels:
                st.divider()
                st.write("**📊 Scaled Take Profit Progress**")
                
                # Calculate TP target prices
                for i, tp_level in enumerate(scaled_tp_levels, 1):
                    profit_pct = tp_level.get('profit_pct', 0.0)
                    close_pct = tp_level.get('close_pct', 0.0)
                    
                    # Calculate target price
                    if side == "LONG":
                        target_price = entry_price * (1 + profit_pct)
                    else:
                        target_price = entry_price * (1 - profit_pct)
                    
                    # Check if this level has been hit
                    is_hit = i in tp_levels_hit
                    
                    # Create columns for TP level display
                    col_a, col_b, col_c, col_d = st.columns([1, 2, 2, 1])
                    
                    with col_a:
                        if is_hit:
                            st.write(f"✅ **TP{i}**")
                        else:
                            st.write(f"⏳ **TP{i}**")
                    
                    with col_b:
                        st.write(f"${target_price:,.6f}")
                        st.caption(f"+{profit_pct*100:.1f}%")
                    
                    with col_c:
                        st.write(f"Close {close_pct*100:.0f}%")
                        if is_hit:
                            st.caption("✓ Executed")
                        else:
                            # Calculate distance to target
                            if side == "LONG":
                                distance_pct = ((target_price - current_price) / current_price) * 100
                            else:
                                distance_pct = ((current_price - target_price) / current_price) * 100
                            
                            if distance_pct > 0:
                                st.caption(f"{distance_pct:.2f}% away")
                            else:
                                st.caption("Price reached!")
                    
                    with col_d:
                        # Progress indicator
                        if is_hit:
                            st.progress(1.0)
                        else:
                            # Calculate progress to this TP level
                            if side == "LONG":
                                progress = (current_price - entry_price) / (target_price - entry_price)
                            else:
                                progress = (entry_price - current_price) / (entry_price - target_price)
                            progress = max(0.0, min(1.0, progress))
                            st.progress(progress)
                
                # Show next TP target
                if tp_levels_hit and len(tp_levels_hit) < len(scaled_tp_levels):
                    next_tp_idx = len(tp_levels_hit)
                    next_tp = scaled_tp_levels[next_tp_idx]
                    next_profit_pct = next_tp.get('profit_pct', 0.0)
                    
                    if side == "LONG":
                        next_target = entry_price * (1 + next_profit_pct)
                    else:
                        next_target = entry_price * (1 - next_profit_pct)
                    
                    st.info(f"🎯 Next Target: TP{next_tp_idx + 1} at ${next_target:,.6f} (+{next_profit_pct*100:.1f}%)")
                elif len(tp_levels_hit) == len(scaled_tp_levels):
                    st.success("🎉 All take profit levels hit!")
            
            # Additional position details
            st.divider()
            
            # Risk metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if entry_price > 0 and stop_loss > 0:
                    risk_distance = abs(entry_price - stop_loss)
                    risk_percent = (risk_distance / entry_price) * 100
                    risk_amount = risk_distance * quantity
                    st.write(f"**Risk Distance:** ${risk_distance:,.6f} ({risk_percent:.2f}%)")
                    st.write(f"**Risk Amount:** ${risk_amount:,.2f}")
            
            with col2:
                # Calculate potential profit to trailing stop
                if entry_price > 0 and trailing_stop > 0:
                    if side == "LONG":
                        potential_profit = (trailing_stop - entry_price) * quantity
                    else:
                        potential_profit = (entry_price - trailing_stop) * quantity
                    profit_percent = (potential_profit / (entry_price * quantity)) * 100
                    st.write(f"**Potential Profit:** ${potential_profit:,.2f}")
                    st.write(f"**Profit %:** {profit_percent:+.2f}%")
            
            with col3:
                # Calculate hold time
                if entry_time:
                    try:
                        from datetime import datetime
                        entry_timestamp = int(entry_time) / 1000
                        entry_dt = datetime.fromtimestamp(entry_timestamp)
                        hold_time = datetime.now() - entry_dt
                        hours = hold_time.total_seconds() / 3600
                        if hours < 1:
                            st.write(f"**Hold Time:** {hold_time.total_seconds() / 60:.0f} minutes")
                        else:
                            st.write(f"**Hold Time:** {hours:.1f} hours")
                        st.write(f"**Entry Time:** {entry_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    except:
                        pass
            
            # Show partial exits history if any
            if partial_exits:
                st.divider()
                st.write("**📝 Partial Exit History**")
                
                for exit_data in partial_exits:
                    tp_level = exit_data.get('tp_level', 0)
                    exit_price = exit_data.get('exit_price', 0.0)
                    quantity_closed = exit_data.get('quantity_closed', 0.0)
                    profit = exit_data.get('profit', 0.0)
                    profit_pct = exit_data.get('profit_pct', 0.0)
                    
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.write(f"**TP{tp_level}:** ${exit_price:,.6f}")
                    
                    with col_b:
                        st.write(f"Qty: {quantity_closed:.4f}")
                    
                    with col_c:
                        if profit > 0:
                            st.write(f":green[+${profit:,.2f} (+{profit_pct*100:.2f}%)]")
                        else:
                            st.write(f":red[${profit:,.2f} ({profit_pct*100:.2f}%)]")
    
    st.divider()
    st.caption("Positions auto-refresh every 5 seconds")


def show_market_data_page():
    """Display market data page."""
    # Initialize data provider
    data_provider = StreamlitDataProvider()
    
    # Get market data, config, and per-symbol data
    results = data_provider._read_cached_json(data_provider.results_path, "results")
    config = data_provider.get_config()
    symbols_data = results.get('symbols_data', [])
    
    # Get thresholds from config
    adx_threshold = config.get('adx_threshold', 25.0)
    rvol_threshold = config.get('rvol_threshold', 1.5)
    
    # If we have per-symbol data, show it
    if symbols_data and len(symbols_data) > 0:
        st.subheader("Market Data - All Symbols")
        
        for symbol_info in symbols_data:
            symbol = symbol_info.get('symbol', 'N/A')
            current_price = symbol_info.get('current_price', 0.0)
            signal = symbol_info.get('signal', 'NONE')
            adx = symbol_info.get('adx', 0.0)
            rvol = symbol_info.get('rvol', 0.0)
            atr = symbol_info.get('atr', 0.0)
            
            with st.expander(f"**{symbol}** - ${current_price:,.4f} | Signal: {signal}", expanded=(signal != 'NONE')):
                # Display current price and signal
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.metric("Price", f"${current_price:,.4f}", help=f"Current price for {symbol}")
                with col2:
                    if signal == 'LONG':
                        st.success(f"🟢 Signal: {signal}")
                    elif signal == 'SHORT':
                        st.error(f"🔴 Signal: {signal}")
                    else:
                        st.info(f"⚪ Signal: {signal}")
                
                st.divider()
                
                # Display indicators
                st.write("**Technical Indicators**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**ADX (Trend Strength)**")
                    # Highlight if meets threshold
                    if adx >= adx_threshold:
                        st.success(f"✅ {adx:.2f}")
                        st.caption(f"Above threshold ({adx_threshold})")
                    else:
                        st.warning(f"⚠️ {adx:.2f}")
                        st.caption(f"Below threshold ({adx_threshold})")
                    
                    # Progress bar
                    st.progress(min(adx / 100.0, 1.0))
                
                with col2:
                    st.write("**RVOL (Relative Volume)**")
                    # Highlight if meets threshold
                    if rvol >= rvol_threshold:
                        st.success(f"✅ {rvol:.2f}")
                        st.caption(f"Above threshold ({rvol_threshold})")
                    else:
                        st.warning(f"⚠️ {rvol:.2f}")
                        st.caption(f"Below threshold ({rvol_threshold})")
                    
                    # Progress bar (normalized to 0-3 range)
                    st.progress(min(rvol / 3.0, 1.0))
                
                with col3:
                    st.write("**ATR (Volatility)**")
                    st.info(f"📊 ${atr:.4f}")
                    st.caption("Average True Range")
                    
                    # Show ATR as percentage of price
                    if current_price > 0:
                        atr_percent = (atr / current_price) * 100
                        st.caption(f"{atr_percent:.2f}% of price")
                
                # Signal conditions summary
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Current Status:**")
                    conditions = []
                    
                    if adx >= adx_threshold:
                        conditions.append("✅ ADX meets threshold")
                    else:
                        conditions.append("❌ ADX below threshold")
                    
                    if rvol >= rvol_threshold:
                        conditions.append("✅ RVOL meets threshold")
                    else:
                        conditions.append("❌ RVOL below threshold")
                    
                    for condition in conditions:
                        st.write(condition)
                
                with col2:
                    st.write("**Market Context:**")
                    if adx >= 50:
                        st.write("• Trend: Very Strong")
                    elif adx >= 25:
                        st.write("• Trend: Strong")
                    else:
                        st.write("• Trend: Weak/Ranging")
                    
                    if rvol >= 2.0:
                        st.write("• Volume: Very High")
                    elif rvol >= 1.5:
                        st.write("• Volume: High")
                    elif rvol >= 1.0:
                        st.write("• Volume: Normal")
                    else:
                        st.write("• Volume: Low")
    
    else:
        # Fallback to single symbol display
        market_data = data_provider.get_market_data()
        symbol = config.get('symbol', 'N/A')
        
        # Display current price
        st.subheader("Current Market Price")
        current_price = market_data.get('current_price', 0.0)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.metric("Price", f"${current_price:,.2f}", help=f"Current price for {symbol}")
        with col2:
            signal = market_data.get('signal', 'NONE')
            if signal == 'LONG':
                st.success(f"🟢 Signal: {signal}")
            elif signal == 'SHORT':
                st.error(f"🔴 Signal: {signal}")
            else:
                st.info(f"⚪ Signal: {signal}")
        
        st.divider()
        
        # Display indicators
        st.subheader("Technical Indicators")
        
        adx = market_data.get('adx', 0.0)
        rvol = market_data.get('rvol', 0.0)
        atr = market_data.get('atr', 0.0)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("ADX (Trend Strength)")
            # Highlight if meets threshold
            if adx >= adx_threshold:
                st.success(f"✅ {adx:.2f}")
                st.caption(f"Above threshold ({adx_threshold})")
            else:
                st.warning(f"⚠️ {adx:.2f}")
                st.caption(f"Below threshold ({adx_threshold})")
            
            # Progress bar
            st.progress(min(adx / 100.0, 1.0))
        
        with col2:
            st.subheader("RVOL (Relative Volume)")
            # Highlight if meets threshold
            if rvol >= rvol_threshold:
                st.success(f"✅ {rvol:.2f}")
                st.caption(f"Above threshold ({rvol_threshold})")
            else:
                st.warning(f"⚠️ {rvol:.2f}")
                st.caption(f"Below threshold ({rvol_threshold})")
            
            # Progress bar (normalized to 0-3 range)
            st.progress(min(rvol / 3.0, 1.0))
        
        with col3:
            st.subheader("ATR (Volatility)")
            st.info(f"📊 ${atr:.2f}")
            st.caption("Average True Range")
            
            # Show ATR as percentage of price
            if current_price > 0:
                atr_percent = (atr / current_price) * 100
                st.caption(f"{atr_percent:.2f}% of price")
        
        st.divider()
        
        # Signal conditions summary
        st.subheader("Signal Conditions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Current Status:**")
            conditions = []
            
            if adx >= adx_threshold:
                conditions.append("✅ ADX meets threshold")
            else:
                conditions.append("❌ ADX below threshold")
            
            if rvol >= rvol_threshold:
                conditions.append("✅ RVOL meets threshold")
            else:
                conditions.append("❌ RVOL below threshold")
            
            for condition in conditions:
                st.write(condition)
        
        with col2:
            st.write("**Configured Thresholds:**")
            st.write(f"• ADX Threshold: {adx_threshold}")
            st.write(f"• RVOL Threshold: {rvol_threshold}")
            st.write(f"• Symbol: {symbol}")
        
        st.divider()
        
        # Additional market info
        st.subheader("Market Context")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if adx >= 50:
                st.write("**Trend:** Very Strong")
            elif adx >= 25:
                st.write("**Trend:** Strong")
            else:
                st.write("**Trend:** Weak/Ranging")
        
        with col2:
            if rvol >= 2.0:
                st.write("**Volume:** Very High")
            elif rvol >= 1.5:
                st.write("**Volume:** High")
            elif rvol >= 1.0:
                st.write("**Volume:** Normal")
            else:
                st.write("**Volume:** Low")
        
        with col3:
            if current_price > 0 and atr > 0:
                atr_percent = (atr / current_price) * 100
                if atr_percent >= 3.0:
                    st.write("**Volatility:** Very High")
                elif atr_percent >= 2.0:
                    st.write("**Volatility:** High")
                elif atr_percent >= 1.0:
                    st.write("**Volatility:** Normal")
                else:
                    st.write("**Volatility:** Low")
    
    st.divider()
    st.caption("Market data auto-refreshes every 5 seconds")


def show_chart_page():
    """Display chart page."""
    # Initialize data provider and chart generator
    data_provider = StreamlitDataProvider()
    
    # Import chart generator here to avoid circular imports
    from src.streamlit_charts import ChartGenerator
    chart_generator = ChartGenerator()
    
    # Get config for symbol
    config = data_provider.get_config()
    symbol = config.get('symbol', 'N/A')
    
    st.subheader(f"Chart for {symbol}")
    
    # Timeframe selector
    col1, col2 = st.columns([1, 3])
    
    with col1:
        timeframe = st.selectbox(
            "Select Timeframe",
            ["5m", "15m", "1h", "4h"],
            index=1  # Default to 15m
        )
    
    with col2:
        st.info(f"Displaying {timeframe} candlesticks")
    
    # Get positions for marking entries
    positions = data_provider.get_open_positions()
    
    # For now, create sample candle data since we don't have historical data access
    # In a real implementation, this would fetch from Binance API or cached data
    st.warning("⚠️ Chart functionality requires historical data access. Displaying placeholder.")
    
    # Create placeholder candles for demonstration
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Generate sample data
    current_price = data_provider.get_market_data().get('current_price', 50000.0)
    
    if current_price > 0:
        # Generate 100 sample candles
        candles = []
        base_time = datetime.now() - timedelta(hours=100)
        
        for i in range(100):
            # Simple random walk for demo
            import random
            variation = random.uniform(-0.02, 0.02)
            open_price = current_price * (1 + variation)
            close_price = current_price * (1 + random.uniform(-0.02, 0.02))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
            
            candles.append({
                'timestamp': base_time + timedelta(hours=i),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': random.uniform(100, 1000)
            })
            
            current_price = close_price
        
        # Create price chart
        fig = chart_generator.create_price_chart(
            candles=candles,
            positions=positions,
            atr_bands=None  # Could add ATR bands if we calculate them
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Unable to load price data")
    
    st.divider()
    
    # Chart information
    st.subheader("Chart Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Timeframe:**", timeframe)
        st.write("**Symbol:**", symbol)
    
    with col2:
        st.write("**Candles Displayed:**", "100")
        st.write("**Chart Type:**", "Candlestick")
    
    with col3:
        if positions:
            st.write("**Position Markers:**", f"{len(positions)} shown")
        else:
            st.write("**Position Markers:**", "None")
    
    st.divider()
    
    # Legend
    st.subheader("Chart Legend")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("🟢 **Green Triangle Up:** Long position entry")
        st.write("🔴 **Red Triangle Down:** Short position entry")
    
    with col2:
        st.write("**Gray Dashed Lines:** ATR bands (when available)")
        st.write("**Candlesticks:** Green = bullish, Red = bearish")
    
    st.divider()
    st.caption("Chart auto-refreshes every 5 seconds")
    
    # Note about implementation
    st.info("""
    **Note:** Full chart functionality requires integration with historical data source.
    Current implementation shows sample data for demonstration purposes.
    To enable real data:
    1. Add historical data fetching to StreamlitDataProvider
    2. Connect to Binance API or use cached candle data
    3. Implement ATR band calculations
    """)


def show_trade_history_page():
    """Display trade history page with separate views for backtest, paper, and live trades."""
    # Initialize data provider
    data_provider = StreamlitDataProvider()
    
    # Create tabs for different trading modes
    tab1, tab2, tab3 = st.tabs(["📊 Backtest Trades", "📝 Paper Trading Trades", "💰 Live Trading Trades"])
    
    # Tab 1: Backtest Trades
    with tab1:
        st.subheader("Backtest Trade History")
        backtest_trades = _load_trades_by_mode("backtest")
        _display_trade_table(backtest_trades, "BACKTEST")
    
    # Tab 2: Paper Trading Trades
    with tab2:
        st.subheader("Paper Trading History")
        paper_trades = _load_trades_by_mode("paper")
        _display_trade_table(paper_trades, "PAPER")
    
    # Tab 3: Live Trading Trades
    with tab3:
        st.subheader("Live Trading History")
        live_trades = _load_trades_by_mode("live")
        _display_trade_table(live_trades, "LIVE")


def _load_trades_by_mode(mode: str) -> list:
    """Load trades from mode-specific log file.
    
    Args:
        mode: Trading mode ('backtest', 'paper', or 'live')
        
    Returns:
        List of trade dictionaries
    """
    import json
    from pathlib import Path
    
    trades = []
    logs_path = Path("logs")
    
    if not logs_path.exists():
        return trades
    
    # Get log files for this mode
    mode_log_file = f"trades_{mode}.log"
    trade_files = []
    
    # Add current log file
    current_log = logs_path / mode_log_file
    if current_log.exists():
        trade_files.append(current_log)
    
    # Add rotated log files
    trade_files.extend(sorted(logs_path.glob(f"{mode_log_file}.*")))
    
    # Parse all log files
    for trade_file in trade_files:
        try:
            with open(trade_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if "TRADE_EXECUTED:" in line:
                        try:
                            json_start = line.find("TRADE_EXECUTED:") + len("TRADE_EXECUTED:")
                            json_str = line[json_start:].strip()
                            trade_data = json.loads(json_str)
                            trades.append(trade_data)
                        except (json.JSONDecodeError, ValueError):
                            continue
        except Exception:
            continue
    
    return trades


def _display_trade_table(trades: list, mode: str):
    """Display trades in a formatted table with filters and sorting.
    
    Args:
        trades: List of trade dictionaries
        mode: Trading mode name for display
    """
    if not trades:
        st.info(f"No {mode.lower()} trades found")
        return
    
    # Date filter
    st.markdown("### Filters")
    col1, col2 = st.columns([1, 3])
    
    with col1:
        time_filter = st.selectbox(
            "Time Period",
            ["All Time", "Today", "Last 7 Days", "Last 30 Days", "Custom Date"],
            index=0,
            key=f"time_filter_{mode}"
        )
    
    # Apply date filter
    from datetime import datetime, timedelta, date
    
    filtered_trades = []
    
    if time_filter == "All Time":
        filtered_trades = trades
    else:
        now = datetime.now()
        
        if time_filter == "Today":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_filter == "Last 7 Days":
            cutoff = now - timedelta(days=7)
        elif time_filter == "Last 30 Days":
            cutoff = now - timedelta(days=30)
        elif time_filter == "Custom Date":
            with col2:
                selected_date = st.date_input("Select Date", value=date.today(), key=f"date_input_{mode}")
                cutoff = datetime.combine(selected_date, datetime.min.time())
        
        # Filter trades by date
        for trade in trades:
            exit_time = trade.get('exit_time', trade.get('timestamp', 0))
            
            # Parse exit time
            if isinstance(exit_time, str):
                try:
                    trade_time = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
                except:
                    continue
            elif isinstance(exit_time, (int, float)):
                trade_time = datetime.fromtimestamp(exit_time / 1000)
            else:
                continue
            
            if trade_time >= cutoff:
                filtered_trades.append(trade)
    
    # Limit to last 100 trades for display
    display_trades = filtered_trades[-100:] if len(filtered_trades) > 100 else filtered_trades
    
    if not display_trades:
        st.warning(f"No trades found for the selected time period ({time_filter})")
        return
    
    # Calculate win rate
    winning_trades = sum(1 for t in display_trades if t.get('pnl', 0) > 0)
    total_trades = len(display_trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    total_pnl = sum(t.get('pnl', 0) for t in display_trades)
    
    # Display summary metrics
    st.markdown("### Trade Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Trades", total_trades)
    
    with col2:
        st.metric("Winning Trades", winning_trades)
    
    with col3:
        losing_trades = sum(1 for t in display_trades if t.get('pnl', 0) < 0)
        st.metric("Losing Trades", losing_trades)
    
    with col4:
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    with col5:
        pnl_color = "normal" if total_pnl >= 0 else "inverse"
        st.metric("Total PnL", f"${total_pnl:.2f}", delta=None if total_pnl == 0 else f"${total_pnl:.2f}")
    
    st.divider()
    
    # Sorting options
    st.markdown(f"### Trade Details ({len(display_trades)} Trades)")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        sort_by = st.selectbox(
            "Sort by",
            ["Date (Newest First)", "Date (Oldest First)", "PnL (Highest First)", "PnL (Lowest First)"],
            key=f"sort_by_{mode}"
        )
    
    # Sort trades based on selection
    # Helper function to safely get sortable timestamp
    def get_sortable_time(trade):
        """Get a sortable timestamp value, handling both int and str formats."""
        exit_time = trade.get('exit_time', trade.get('timestamp', 0))
        
        # If it's already an int/float, return it
        if isinstance(exit_time, (int, float)):
            return exit_time
        
        # If it's a string, try to parse it
        if isinstance(exit_time, str) and exit_time:
            try:
                from datetime import datetime
                # Try ISO format first
                dt = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
                return dt.timestamp() * 1000  # Convert to milliseconds
            except:
                pass
        
        # Default to 0 if we can't parse it
        return 0
    
    if sort_by == "Date (Newest First)":
        sorted_trades = sorted(display_trades, key=get_sortable_time, reverse=True)
    elif sort_by == "Date (Oldest First)":
        sorted_trades = sorted(display_trades, key=get_sortable_time)
    elif sort_by == "PnL (Highest First)":
        sorted_trades = sorted(display_trades, key=lambda t: t.get('pnl', 0), reverse=True)
    else:  # PnL (Lowest First)
        sorted_trades = sorted(display_trades, key=lambda t: t.get('pnl', 0))
    
    # Display trades in a table
    for idx, trade in enumerate(sorted_trades, 1):
        # Extract trade data
        symbol = trade.get('symbol', 'N/A')
        side = trade.get('side', 'N/A')
        entry_time = trade.get('entry_time', 0)
        exit_time = trade.get('exit_time', trade.get('timestamp', 0))
        entry_price = trade.get('entry_price', 0.0)
        exit_price = trade.get('exit_price', 0.0)
        quantity = trade.get('quantity', 0.0)
        pnl = trade.get('pnl', 0.0)
        pnl_percent = trade.get('pnl_percent', trade.get('return_percentage', 0.0))
        exit_reason = trade.get('exit_reason', 'N/A')
        
        # Scaled TP data
        partial_exits = trade.get('partial_exits', [])
        original_quantity = trade.get('original_quantity', quantity)
        
        # Format timestamps
        if isinstance(exit_time, str):
            exit_time_str = exit_time
        elif exit_time == 0:
            exit_time_str = 'N/A'
        else:
            from datetime import datetime
            exit_time_str = datetime.fromtimestamp(exit_time / 1000).strftime('%Y-%m-%d %H:%M:%S') if exit_time else 'N/A'
        
        if isinstance(entry_time, str):
            entry_time_str = entry_time
        else:
            from datetime import datetime
            entry_time_str = datetime.fromtimestamp(entry_time / 1000).strftime('%Y-%m-%d %H:%M:%S') if entry_time else 'N/A'
        
        # Calculate total PnL and average exit price if there are partial exits
        if partial_exits:
            # Calculate total PnL from all partial exits plus final exit
            total_pnl_from_partials = sum(pe.get('profit', 0.0) for pe in partial_exits)
            
            # Calculate final exit PnL (if there was a remaining quantity)
            if quantity > 0:
                final_exit_pnl = pnl  # This should be the PnL from the final exit
                total_trade_pnl = total_pnl_from_partials + final_exit_pnl
            else:
                # All quantity was closed via partials
                total_trade_pnl = total_pnl_from_partials
            
            # Calculate average exit price across all exits
            total_quantity_exited = sum(pe.get('quantity_closed', 0.0) for pe in partial_exits)
            weighted_price_sum = sum(pe.get('exit_price', 0.0) * pe.get('quantity_closed', 0.0) for pe in partial_exits)
            
            if quantity > 0:
                # Add final exit to average
                total_quantity_exited += quantity
                weighted_price_sum += exit_price * quantity
            
            avg_exit_price = weighted_price_sum / total_quantity_exited if total_quantity_exited > 0 else exit_price
            
            # Calculate overall return percentage
            if entry_price > 0 and original_quantity > 0:
                total_pnl_percent = (total_trade_pnl / (entry_price * original_quantity)) * 100
            else:
                total_pnl_percent = pnl_percent
            
            # Add indicator for scaled TP trades
            pnl_indicator = "🟢" if total_trade_pnl > 0 else "🔴" if total_trade_pnl < 0 else "⚪"
            scaled_indicator = f" [📊 {len(partial_exits)} Partials]"
        else:
            # No partial exits - regular trade
            total_trade_pnl = pnl
            total_pnl_percent = pnl_percent
            avg_exit_price = exit_price
            pnl_indicator = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
            scaled_indicator = ""
        
        # Create expandable section for each trade
        with st.expander(f"Trade {idx}: {symbol} {side} - {pnl_indicator} ${total_trade_pnl:,.2f} ({total_pnl_percent:+.2f}%){scaled_indicator}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**Trade Details**")
                st.write(f"Symbol: {symbol}")
                st.write(f"Side: {side}")
                
                # Show original vs final quantity if there were partials
                if partial_exits:
                    st.write(f"Original Qty: {original_quantity:.4f}")
                    if quantity > 0:
                        st.write(f"Final Exit Qty: {quantity:.4f}")
                    else:
                        st.write(f"Final Exit Qty: 0.0000 (all closed via partials)")
                else:
                    st.write(f"Quantity: {quantity:.4f}")
                
                st.write(f"Exit Reason: {exit_reason}")
            
            with col2:
                st.write("**Timing**")
                st.write(f"Entry Time: {entry_time_str}")
                st.write(f"Exit Time: {exit_time_str}")
                
                # Calculate duration if possible
                if isinstance(entry_time, (int, float)) and isinstance(exit_time, (int, float)):
                    duration_ms = exit_time - entry_time
                    duration_minutes = duration_ms / 1000 / 60
                    if duration_minutes < 60:
                        st.write(f"Duration: {duration_minutes:.1f} minutes")
                    else:
                        duration_hours = duration_minutes / 60
                        st.write(f"Duration: {duration_hours:.1f} hours")
            
            with col3:
                st.write("**Performance**")
                st.write(f"Entry Price: ${entry_price:,.2f}")
                
                # Show average exit price if there were partials
                if partial_exits:
                    st.write(f"Avg Exit Price: ${avg_exit_price:,.2f}")
                else:
                    st.write(f"Exit Price: ${exit_price:,.2f}")
                
                # Color-coded total PnL
                if total_trade_pnl > 0:
                    st.write(f"Total PnL: :green[${total_trade_pnl:,.2f}]")
                    st.write(f"Total Return: :green[+{total_pnl_percent:.2f}%]")
                elif total_trade_pnl < 0:
                    st.write(f"Total PnL: :red[${total_trade_pnl:,.2f}]")
                    st.write(f"Total Return: :red[{total_pnl_percent:.2f}%]")
                else:
                    st.write(f"Total PnL: ${total_trade_pnl:,.2f}")
                    st.write(f"Total Return: {total_pnl_percent:.2f}%")
            
            # Show partial exits breakdown if any
            if partial_exits:
                st.divider()
                st.write("**📊 Partial Exit Breakdown**")
                
                # Create a table for partial exits
                for pe_idx, pe in enumerate(partial_exits, 1):
                    tp_level = pe.get('tp_level', pe_idx)
                    pe_exit_price = pe.get('exit_price', 0.0)
                    pe_quantity = pe.get('quantity_closed', 0.0)
                    pe_profit = pe.get('profit', 0.0)
                    pe_profit_pct = pe.get('profit_pct', 0.0) * 100  # Convert to percentage
                    pe_exit_time = pe.get('exit_time', 0)
                    
                    # Format exit time
                    if isinstance(pe_exit_time, (int, float)) and pe_exit_time > 0:
                        from datetime import datetime
                        pe_exit_time_str = datetime.fromtimestamp(pe_exit_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        pe_exit_time_str = 'N/A'
                    
                    col_a, col_b, col_c, col_d = st.columns([1, 2, 2, 2])
                    
                    with col_a:
                        st.write(f"**TP{tp_level}**")
                    
                    with col_b:
                        st.write(f"${pe_exit_price:,.2f}")
                        st.caption(f"Qty: {pe_quantity:.4f}")
                    
                    with col_c:
                        if pe_profit > 0:
                            st.write(f":green[+${pe_profit:,.2f}]")
                            st.caption(f":green[+{pe_profit_pct:.2f}%]")
                        elif pe_profit < 0:
                            st.write(f":red[${pe_profit:,.2f}]")
                            st.caption(f":red[{pe_profit_pct:.2f}%]")
                        else:
                            st.write(f"${pe_profit:,.2f}")
                            st.caption(f"{pe_profit_pct:.2f}%")
                    
                    with col_d:
                        st.caption(pe_exit_time_str)
                
                # Show final exit if there was remaining quantity
                if quantity > 0:
                    st.divider()
                    st.write("**Final Exit (Remaining Position)**")
                    
                    col_a, col_b, col_c, col_d = st.columns([1, 2, 2, 2])
                    
                    with col_a:
                        st.write(f"**Final**")
                    
                    with col_b:
                        st.write(f"${exit_price:,.2f}")
                        st.caption(f"Qty: {quantity:.4f}")
                    
                    with col_c:
                        if pnl > 0:
                            st.write(f":green[+${pnl:,.2f}]")
                            st.caption(f":green[+{pnl_percent:.2f}%]")
                        elif pnl < 0:
                            st.write(f":red[${pnl:,.2f}]")
                            st.caption(f":red[{pnl_percent:.2f}%]")
                        else:
                            st.write(f"${pnl:,.2f}")
                            st.caption(f"{pnl_percent:.2f}%")
                    
                    with col_d:
                        st.caption(exit_time_str)
    
    st.divider()
    st.caption(f"Showing {len(trades)} trades • Filtered by: {time_filter} • Auto-refreshes every 5 seconds")


def show_analytics_page():
    """Display analytics page."""
    # Initialize data provider and chart generator
    data_provider = StreamlitDataProvider()
    from src.streamlit_charts import ChartGenerator
    chart_generator = ChartGenerator()
    
    # Time period filter
    col1, col2 = st.columns([1, 3])
    with col1:
        time_period = st.selectbox(
            "Time Period",
            ["24h", "7d", "30d", "All"],
            index=3  # Default to "All"
        )
    
    # Get all trades
    all_trades = data_provider.get_trade_history(limit=1000)  # Get more trades for analytics
    
    if not all_trades:
        st.info("No trade data available for analytics")
        return
    
    # Filter trades by time period
    from datetime import datetime, timedelta
    
    filtered_trades = []
    if time_period != "All":
        now = datetime.now()
        
        if time_period == "24h":
            cutoff = now - timedelta(hours=24)
        elif time_period == "7d":
            cutoff = now - timedelta(days=7)
        elif time_period == "30d":
            cutoff = now - timedelta(days=30)
        
        for trade in all_trades:
            exit_time = trade.get('exit_time', trade.get('timestamp', 0))
            
            # Parse exit time
            if isinstance(exit_time, str):
                try:
                    trade_time = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
                except:
                    continue
            elif isinstance(exit_time, (int, float)):
                trade_time = datetime.fromtimestamp(exit_time / 1000)
            else:
                continue
            
            if trade_time >= cutoff:
                filtered_trades.append(trade)
    else:
        filtered_trades = all_trades
    
    if not filtered_trades:
        st.warning(f"No trades found in the selected time period ({time_period})")
        return
    
    # Calculate metrics
    total_trades = len(filtered_trades)
    winning_trades = sum(1 for t in filtered_trades if t.get('pnl', 0) > 0)
    losing_trades = sum(1 for t in filtered_trades if t.get('pnl', 0) < 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    total_pnl = sum(t.get('pnl', 0) for t in filtered_trades)
    avg_profit = total_pnl / total_trades if total_trades > 0 else 0.0
    
    avg_win = sum(t.get('pnl', 0) for t in filtered_trades if t.get('pnl', 0) > 0) / winning_trades if winning_trades > 0 else 0.0
    avg_loss = sum(t.get('pnl', 0) for t in filtered_trades if t.get('pnl', 0) < 0) / losing_trades if losing_trades > 0 else 0.0
    
    # Calculate Sharpe ratio
    returns = [t.get('pnl_percent', t.get('return_percentage', 0)) for t in filtered_trades]
    if returns and len(returns) > 1:
        import statistics
        mean_return = statistics.mean(returns)
        std_dev = statistics.stdev(returns)
        risk_free_rate = 0.0  # Assuming 0% risk-free rate
        sharpe_ratio = (mean_return - risk_free_rate) / std_dev if std_dev > 0 else 0.0
    else:
        sharpe_ratio = 0.0
    
    # Calculate maximum drawdown
    cumulative_pnl = []
    running_total = 0
    for trade in filtered_trades:
        running_total += trade.get('pnl', 0)
        cumulative_pnl.append(running_total)
    
    max_drawdown = 0.0
    if cumulative_pnl:
        peak = cumulative_pnl[0]
        for value in cumulative_pnl:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    
    # Display key metrics
    st.subheader(f"Performance Metrics ({time_period})")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if total_pnl > 0:
            st.metric("Total PnL", f"${total_pnl:,.2f}", delta=f"+{total_pnl:,.2f}", delta_color="normal")
        elif total_pnl < 0:
            st.metric("Total PnL", f"${total_pnl:,.2f}", delta=f"{total_pnl:,.2f}", delta_color="inverse")
        else:
            st.metric("Total PnL", f"${total_pnl:,.2f}")
    
    with col2:
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    with col3:
        st.metric("Avg Profit/Trade", f"${avg_profit:,.2f}")
    
    with col4:
        st.metric("Total Trades", total_trades)
    
    st.divider()
    
    # Additional metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
    
    with col2:
        st.metric("Max Drawdown", f"${max_drawdown:,.2f}")
    
    with col3:
        st.metric("Avg Win", f"${avg_win:,.2f}")
    
    with col4:
        st.metric("Avg Loss", f"${avg_loss:,.2f}")
    
    st.divider()
    
    # Cumulative PnL chart
    st.subheader("Cumulative PnL Over Time")
    pnl_chart = chart_generator.create_pnl_chart(filtered_trades)
    st.plotly_chart(pnl_chart, use_container_width=True)
    
    st.divider()
    
    # Win/Loss distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Win/Loss Distribution")
        win_loss_chart = chart_generator.create_win_rate_chart(filtered_trades)
        st.plotly_chart(win_loss_chart, use_container_width=True)
    
    with col2:
        st.subheader("Trade Statistics")
        st.write(f"**Winning Trades:** {winning_trades}")
        st.write(f"**Losing Trades:** {losing_trades}")
        st.write(f"**Breakeven Trades:** {total_trades - winning_trades - losing_trades}")
        st.write("")
        st.write(f"**Best Trade:** ${max(t.get('pnl', 0) for t in filtered_trades):,.2f}")
        st.write(f"**Worst Trade:** ${min(t.get('pnl', 0) for t in filtered_trades):,.2f}")
        st.write("")
        
        if avg_loss != 0:
            profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if losing_trades > 0 else float('inf')
            st.write(f"**Profit Factor:** {profit_factor:.2f}")
        
        if losing_trades > 0 and winning_trades > 0:
            expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * abs(avg_loss))
            st.write(f"**Expectancy:** ${expectancy:.2f}")
    
    st.divider()
    
    # Performance breakdown
    st.subheader("Performance Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**By Side:**")
        long_trades = [t for t in filtered_trades if t.get('side', '').upper() == 'LONG']
        short_trades = [t for t in filtered_trades if t.get('side', '').upper() == 'SHORT']
        
        if long_trades:
            long_pnl = sum(t.get('pnl', 0) for t in long_trades)
            long_win_rate = sum(1 for t in long_trades if t.get('pnl', 0) > 0) / len(long_trades) * 100
            st.write(f"Long: {len(long_trades)} trades, ${long_pnl:,.2f} PnL, {long_win_rate:.1f}% win rate")
        
        if short_trades:
            short_pnl = sum(t.get('pnl', 0) for t in short_trades)
            short_win_rate = sum(1 for t in short_trades if t.get('pnl', 0) > 0) / len(short_trades) * 100
            st.write(f"Short: {len(short_trades)} trades, ${short_pnl:,.2f} PnL, {short_win_rate:.1f}% win rate")
    
    with col2:
        st.write("**By Exit Reason:**")
        exit_reasons = {}
        for trade in filtered_trades:
            reason = trade.get('exit_reason', 'UNKNOWN')
            if reason not in exit_reasons:
                exit_reasons[reason] = {'count': 0, 'pnl': 0}
            exit_reasons[reason]['count'] += 1
            exit_reasons[reason]['pnl'] += trade.get('pnl', 0)
        
        for reason, data in sorted(exit_reasons.items(), key=lambda x: x[1]['count'], reverse=True):
            st.write(f"{reason}: {data['count']} trades, ${data['pnl']:,.2f} PnL")
    
    # Scaled Take Profit Analytics Section
    st.divider()
    st.subheader("📊 Scaled Take Profit Analytics")
    
    # Import analytics module
    from src.scaled_tp_analytics import ScaledTPAnalytics
    analytics = ScaledTPAnalytics()
    
    # Get configuration to determine number of TP levels
    config = data_provider.get_config()
    num_tp_levels = len(config.get('scaled_tp_levels', []))
    scaled_tp_enabled = config.get('enable_scaled_take_profit', False)
    
    # Check if we have any scaled TP trades
    scaled_trades = [t for t in filtered_trades if t.get('partial_exits')]
    
    if not scaled_tp_enabled:
        st.info("ℹ️ Scaled Take Profit is currently disabled in configuration. Enable it to see analytics.")
    elif not scaled_trades:
        st.info("ℹ️ No trades with scaled take profit found in the selected time period.")
    else:
        # Calculate scaled TP performance
        scaled_performance = analytics.calculate_scaled_tp_performance(filtered_trades, num_tp_levels)
        
        if scaled_performance:
            # Display overall scaled TP metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Scaled TP Trades", scaled_performance.total_trades)
            
            with col2:
                st.metric("Total Profit", f"${scaled_performance.total_profit:,.2f}")
            
            with col3:
                st.metric("Avg Profit/Trade", f"${scaled_performance.avg_profit_per_trade:,.2f}")
            
            with col4:
                st.metric("Avg TPs Hit", f"{scaled_performance.avg_tp_levels_hit:.2f}")
            
            st.divider()
            
            # Display TP level metrics
            st.write("**Performance by Take Profit Level:**")
            
            # Create columns for each TP level
            tp_cols = st.columns(num_tp_levels)
            
            for idx, tp_metric in enumerate(scaled_performance.tp_level_metrics):
                with tp_cols[idx]:
                    st.write(f"**TP{tp_metric.level}**")
                    st.metric("Hit Rate", f"{tp_metric.hit_rate:.1f}%")
                    st.metric("Hits", tp_metric.hit_count)
                    st.metric("Avg Profit", f"${tp_metric.avg_profit:,.2f}")
                    st.metric("Avg Profit %", f"{tp_metric.avg_profit_pct:.2f}%")
                    st.metric("Total Profit", f"${tp_metric.total_profit:,.2f}")
            
            st.divider()
            
            # Additional insights
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Scaled TP Insights:**")
                st.write(f"• {scaled_performance.full_exit_rate:.1f}% of trades hit all TP levels")
                st.write(f"• Average {scaled_performance.avg_tp_levels_hit:.2f} TP levels hit per trade")
                
                # Calculate cascade effect
                if len(scaled_performance.tp_level_metrics) >= 2:
                    tp1_hit_rate = scaled_performance.tp_level_metrics[0].hit_rate
                    tp2_hit_rate = scaled_performance.tp_level_metrics[1].hit_rate
                    if tp1_hit_rate > 0:
                        cascade_rate = (tp2_hit_rate / tp1_hit_rate) * 100
                        st.write(f"• {cascade_rate:.1f}% of TP1 hits reached TP2")
            
            with col2:
                st.write("**Profit Distribution:**")
                # Calculate profit contribution by TP level
                total_tp_profit = sum(m.total_profit for m in scaled_performance.tp_level_metrics)
                
                if total_tp_profit > 0:
                    for tp_metric in scaled_performance.tp_level_metrics:
                        contribution = (tp_metric.total_profit / total_tp_profit) * 100
                        st.write(f"• TP{tp_metric.level}: {contribution:.1f}% of total profit")
        
        st.divider()
        
        # Strategy Comparison (if we have both scaled and single TP trades)
        comparison = analytics.compare_strategies(filtered_trades)
        
        if comparison:
            st.write("**📈 Strategy Comparison: Scaled TP vs Single TP**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**Trade Count:**")
                st.write(f"Scaled TP: {comparison.scaled_tp_trades} trades")
                st.write(f"Single TP: {comparison.single_tp_trades} trades")
            
            with col2:
                st.write("**Win Rate:**")
                st.write(f"Scaled TP: {comparison.scaled_tp_win_rate:.1f}%")
                st.write(f"Single TP: {comparison.single_tp_win_rate:.1f}%")
                
                win_rate_diff = comparison.scaled_tp_win_rate - comparison.single_tp_win_rate
                if win_rate_diff > 0:
                    st.write(f"✅ +{win_rate_diff:.1f}% improvement")
                elif win_rate_diff < 0:
                    st.write(f"⚠️ {win_rate_diff:.1f}% decrease")
            
            with col3:
                st.write("**Avg Profit/Trade:**")
                st.write(f"Scaled TP: ${comparison.scaled_tp_avg_profit:,.2f}")
                st.write(f"Single TP: ${comparison.single_tp_avg_profit:,.2f}")
                
                if comparison.profit_improvement > 0:
                    st.write(f"✅ +{comparison.profit_improvement:.1f}% improvement")
                elif comparison.profit_improvement < 0:
                    st.write(f"⚠️ {comparison.profit_improvement:.1f}% decrease")
            
            st.divider()
            
            # Summary recommendation
            if comparison.profit_improvement > 5 and comparison.scaled_tp_win_rate >= comparison.single_tp_win_rate:
                st.success("✅ Scaled TP is performing significantly better than single TP strategy!")
            elif comparison.profit_improvement > 0:
                st.info("ℹ️ Scaled TP shows modest improvement over single TP strategy.")
            elif comparison.profit_improvement < -5:
                st.warning("⚠️ Single TP is currently outperforming scaled TP. Consider reviewing TP level configuration.")
            else:
                st.info("ℹ️ Both strategies are performing similarly.")
    
    st.divider()
    st.caption(f"Analytics for {total_trades} trades in {time_period} period • Auto-refreshes every 5 seconds")


def show_settings_page():
    """Display settings page."""
    # Initialize config editor
    from src.streamlit_config_editor import ConfigEditor
    config_editor = ConfigEditor()
    
    # Load current configuration
    config = config_editor.load_config()
    
    if not config:
        st.error("Failed to load configuration file. Please ensure config/config.json exists.")
        return
    
    st.subheader("Bot Configuration")
    st.info("⚠️ Stop the bot before changing settings. Changes take effect on next bot start.")
    
    # Create tabs for different setting categories
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Trading Parameters", 
        "Risk Management", 
        "Indicators", 
        "Advanced Features",
        "Portfolio Management",
        "System"
    ])
    
    # Trading Parameters Tab
    with tab1:
        st.subheader("Trading Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input(
                "Trading Symbol",
                value=config.get("symbol", "BTCUSDT"),
                help="The trading pair symbol (e.g., BTCUSDT, ETHUSDT)"
            )
            
            timeframe = st.selectbox(
                "Timeframe",
                options=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
                index=["1m", "5m", "15m", "30m", "1h", "4h", "1d"].index(config.get("timeframe", "15m")),
                help="The timeframe for candle data"
            )
            
            leverage = st.number_input(
                "Leverage",
                min_value=1,
                max_value=125,
                value=int(config.get("leverage", 10)),
                help="Trading leverage (1-125)"
            )
        
        with col2:
            mode = st.selectbox(
                "Trading Mode",
                options=["BACKTEST", "PAPER", "LIVE"],
                index=["BACKTEST", "PAPER", "LIVE"].index(config.get("run_mode", "PAPER").upper()),
                help="BACKTEST (historical data), PAPER (simulation), or LIVE (real trading)"
            )
            
            max_positions = st.number_input(
                "Max Open Positions",
                min_value=1,
                max_value=10,
                value=int(config.get("max_positions", 3)),
                help="Maximum number of concurrent open positions"
            )
    
    # Risk Management Tab
    with tab2:
        st.subheader("Risk Management")
        
        # Take Profit Info Box
        st.info("🎯 **Take Profit Feature Active:** Positions will automatically close when they reach your profit target (works for both LONG and SHORT trades)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            risk_per_trade = st.number_input(
                "Risk Per Trade",
                min_value=0.001,
                max_value=1.0,
                value=float(config.get("risk_per_trade", 0.02)),
                step=0.001,
                format="%.3f",
                help="Percentage of account to risk per trade (0.001-1.0)"
            )
            
            stop_loss_pct = st.number_input(
                "Stop Loss %",
                min_value=0.001,
                max_value=1.0,
                value=float(config.get("stop_loss_pct", 0.02)),
                step=0.001,
                format="%.3f",
                help="Stop loss as percentage of entry price (0.001-1.0)"
            )
            
            trailing_stop_activation = st.number_input(
                "Trailing Stop Activation %",
                min_value=0.0,
                max_value=1.0,
                value=float(config.get("trailing_stop_activation", 0.015)),
                step=0.001,
                format="%.3f",
                help="Profit % to activate trailing stop"
            )
        
        with col2:
            take_profit_pct = st.number_input(
                "Take Profit %",
                min_value=0.001,
                max_value=10.0,
                value=float(config.get("take_profit_pct", 0.04)),
                step=0.001,
                format="%.3f",
                help="Take profit target (works for both LONG and SHORT). Position closes when profit reaches this % (e.g., 0.04 = 4% profit)"
            )
            
            trailing_stop_distance = st.number_input(
                "Trailing Stop Distance %",
                min_value=0.001,
                max_value=1.0,
                value=float(config.get("trailing_stop_distance", 0.01)),
                step=0.001,
                format="%.3f",
                help="Distance to trail behind peak price"
            )
            
            max_daily_loss = st.number_input(
                "Max Daily Loss %",
                min_value=0.01,
                max_value=1.0,
                value=float(config.get("max_daily_loss", 0.05)),
                step=0.01,
                format="%.2f",
                help="Maximum daily loss before stopping (as % of account)"
            )
    
    # Indicators Tab
    with tab3:
        st.subheader("Technical Indicators")
        
        col1, col2 = st.columns(2)
        
        with col1:
            adx_threshold = st.number_input(
                "ADX Threshold",
                min_value=0.0,
                max_value=100.0,
                value=float(config.get("adx_threshold", 25.0)),
                step=1.0,
                help="Minimum ADX value for trend strength (0-100)"
            )
            
            adx_period = st.number_input(
                "ADX Period",
                min_value=5,
                max_value=50,
                value=int(config.get("adx_period", 14)),
                help="Period for ADX calculation"
            )
            
            atr_period = st.number_input(
                "ATR Period",
                min_value=5,
                max_value=50,
                value=int(config.get("atr_period", 14)),
                help="Period for ATR calculation"
            )
        
        with col2:
            rvol_threshold = st.number_input(
                "RVOL Threshold",
                min_value=0.0,
                max_value=10.0,
                value=float(config.get("rvol_threshold", 1.5)),
                step=0.1,
                help="Minimum relative volume threshold"
            )
            
            rvol_period = st.number_input(
                "RVOL Period",
                min_value=5,
                max_value=100,
                value=int(config.get("rvol_period", 20)),
                help="Period for RVOL calculation"
            )
            
            ema_fast = st.number_input(
                "EMA Fast Period",
                min_value=5,
                max_value=100,
                value=int(config.get("ema_fast", 12)),
                help="Fast EMA period"
            )
    
    # Advanced Features Tab
    with tab4:
        st.subheader("Advanced Features")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Feature Toggles**")
            enable_adaptive_thresholds = st.checkbox(
                "Adaptive Thresholds",
                value=config.get("enable_adaptive_thresholds", False),
                help="Automatically adjust ADX and RVOL thresholds based on market conditions"
            )
            
            enable_multi_timeframe = st.checkbox(
                "Multi-Timeframe Analysis",
                value=config.get("enable_multi_timeframe", True),
                help="Analyze multiple timeframes for better signal confirmation"
            )
            
            enable_volume_profile = st.checkbox(
                "Volume Profile",
                value=config.get("enable_volume_profile", True),
                help="Use volume profile analysis for key price levels"
            )
            
            enable_ml_prediction = st.checkbox(
                "ML Predictions",
                value=config.get("enable_ml_prediction", False),
                help="Use machine learning model for price predictions"
            )
            
            enable_advanced_exits = st.checkbox(
                "Advanced Exits",
                value=config.get("enable_advanced_exits", True),
                help="Use partial exits and breakeven stops"
            )
            
            enable_regime_detection = st.checkbox(
                "Regime Detection",
                value=config.get("enable_regime_detection", False),
                help="Detect market regime (trending/ranging/volatile) and adjust strategy"
            )
        
        with col2:
            st.write("**Adaptive Thresholds Settings**")
            if enable_adaptive_thresholds:
                adaptive_threshold_min_adx = st.number_input(
                    "Min ADX",
                    min_value=10.0,
                    max_value=50.0,
                    value=float(config.get("adaptive_threshold_min_adx", 15.0)),
                    step=1.0,
                    help="Minimum ADX threshold"
                )
                
                adaptive_threshold_max_adx = st.number_input(
                    "Max ADX",
                    min_value=20.0,
                    max_value=100.0,
                    value=float(config.get("adaptive_threshold_max_adx", 35.0)),
                    step=1.0,
                    help="Maximum ADX threshold"
                )
                
                adaptive_threshold_min_rvol = st.number_input(
                    "Min RVOL",
                    min_value=0.5,
                    max_value=2.0,
                    value=float(config.get("adaptive_threshold_min_rvol", 0.8)),
                    step=0.1,
                    help="Minimum RVOL threshold"
                )
                
                adaptive_threshold_max_rvol = st.number_input(
                    "Max RVOL",
                    min_value=1.0,
                    max_value=5.0,
                    value=float(config.get("adaptive_threshold_max_rvol", 2.0)),
                    step=0.1,
                    help="Maximum RVOL threshold"
                )
            else:
                st.info("Enable Adaptive Thresholds to configure these settings")
        
        st.divider()
        
        # Multi-Timeframe Settings
        if enable_multi_timeframe:
            st.write("**Multi-Timeframe Settings**")
            col1, col2 = st.columns(2)
            
            with col1:
                timeframe_entry = st.selectbox(
                    "Entry Timeframe",
                    options=["5m", "15m", "30m", "1h"],
                    index=["5m", "15m", "30m", "1h"].index(config.get("timeframe_entry", "15m")),
                    help="Primary timeframe for entry signals"
                )
                
                timeframe_filter = st.selectbox(
                    "Filter Timeframe",
                    options=["15m", "1h", "4h", "1d"],
                    index=["15m", "1h", "4h", "1d"].index(config.get("timeframe_filter", "1h")),
                    help="Higher timeframe for trend filtering"
                )
            
            with col2:
                min_timeframe_alignment = st.number_input(
                    "Min Timeframe Alignment",
                    min_value=2,
                    max_value=4,
                    value=int(config.get("min_timeframe_alignment", 3)),
                    help="Minimum number of timeframes that must agree"
                )
        
        st.divider()
        
        # Advanced Exits Settings
        if enable_advanced_exits:
            st.write("**Advanced Exits Settings**")
            col1, col2 = st.columns(2)
            
            with col1:
                exit_partial_1_percentage = st.number_input(
                    "Partial Exit 1 %",
                    min_value=0.1,
                    max_value=0.5,
                    value=float(config.get("exit_partial_1_percentage", 0.33)),
                    step=0.01,
                    format="%.2f",
                    help="Percentage to exit at first target"
                )
                
                exit_partial_2_percentage = st.number_input(
                    "Partial Exit 2 %",
                    min_value=0.1,
                    max_value=0.5,
                    value=float(config.get("exit_partial_2_percentage", 0.33)),
                    step=0.01,
                    format="%.2f",
                    help="Percentage to exit at second target"
                )
            
            with col2:
                exit_partial_1_atr_multiplier = st.number_input(
                    "Exit 1 ATR Multiplier",
                    min_value=1.0,
                    max_value=5.0,
                    value=float(config.get("exit_partial_1_atr_multiplier", 1.5)),
                    step=0.1,
                    help="ATR multiplier for first exit"
                )
                
                exit_partial_2_atr_multiplier = st.number_input(
                    "Exit 2 ATR Multiplier",
                    min_value=2.0,
                    max_value=10.0,
                    value=float(config.get("exit_partial_2_atr_multiplier", 3.0)),
                    step=0.5,
                    help="ATR multiplier for second exit"
                )
    
    # Portfolio Management Tab
    with tab5:
        st.subheader("Portfolio Management")
        
        enable_portfolio_management = st.checkbox(
            "Enable Portfolio Management",
            value=config.get("enable_portfolio_management", False),
            help="Trade multiple symbols with correlation-based risk management"
        )
        
        if enable_portfolio_management:
            st.write("**Portfolio Symbols**")
            
            # Get current symbols
            current_symbols = config.get("portfolio_symbols", [])
            symbols_text = st.text_area(
                "Symbols (one per line)",
                value="\n".join(current_symbols),
                height=150,
                help="Enter trading symbols, one per line (e.g., BTCUSDT, ETHUSDT)"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                portfolio_max_symbols = st.number_input(
                    "Max Symbols",
                    min_value=1,
                    max_value=20,
                    value=int(config.get("portfolio_max_symbols", 5)),
                    help="Maximum number of symbols to trade simultaneously"
                )
                
                portfolio_max_total_risk = st.number_input(
                    "Max Total Risk %",
                    min_value=0.01,
                    max_value=0.5,
                    value=float(config.get("portfolio_max_total_risk", 0.05)),
                    step=0.01,
                    format="%.2f",
                    help="Maximum total portfolio risk (Warning: >0.3 is very aggressive)"
                )
                
                portfolio_max_single_allocation = st.number_input(
                    "Max Single Allocation %",
                    min_value=0.1,
                    max_value=1.0,
                    value=float(config.get("portfolio_max_single_allocation", 0.4)),
                    step=0.05,
                    format="%.2f",
                    help="Maximum allocation to single symbol"
                )
            
            with col2:
                portfolio_correlation_threshold = st.number_input(
                    "Correlation Threshold",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(config.get("portfolio_correlation_threshold", 0.7)),
                    step=0.05,
                    format="%.2f",
                    help="Maximum correlation between symbols"
                )
                
                portfolio_correlation_max_exposure = st.number_input(
                    "Max Correlated Exposure %",
                    min_value=0.1,
                    max_value=1.0,
                    value=float(config.get("portfolio_correlation_max_exposure", 0.5)),
                    step=0.05,
                    format="%.2f",
                    help="Maximum exposure to correlated symbols"
                )
                
                portfolio_correlation_lookback_days = st.number_input(
                    "Correlation Lookback Days",
                    min_value=7,
                    max_value=90,
                    value=int(config.get("portfolio_correlation_lookback_days", 30)),
                    help="Days to look back for correlation calculation"
                )
        else:
            st.info("Enable Portfolio Management to configure these settings")
            symbols_text = ""
            portfolio_max_symbols = config.get("portfolio_max_symbols", 5)
            portfolio_max_total_risk = config.get("portfolio_max_total_risk", 0.05)
            portfolio_max_single_allocation = config.get("portfolio_max_single_allocation", 0.4)
            portfolio_correlation_threshold = config.get("portfolio_correlation_threshold", 0.7)
            portfolio_correlation_max_exposure = config.get("portfolio_correlation_max_exposure", 0.5)
            portfolio_correlation_lookback_days = config.get("portfolio_correlation_lookback_days", 30)
    
    # System Tab
    with tab6:
        st.subheader("System Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input(
                "API Key",
                value="*" * 20 if config.get("api_key") else "",
                disabled=True,
                help="API key is hidden for security. Edit config.json directly to change."
            )
            
            st.text_input(
                "API Secret",
                value="*" * 20 if config.get("api_secret") else "",
                disabled=True,
                help="API secret is hidden for security. Edit config.json directly to change."
            )
        
        with col2:
            log_level = st.selectbox(
                "Log Level",
                options=["DEBUG", "INFO", "WARNING", "ERROR"],
                index=["DEBUG", "INFO", "WARNING", "ERROR"].index(config.get("log_level", "INFO")),
                help="Logging verbosity level"
            )
            
            enable_ml = st.checkbox(
                "Enable ML Predictions",
                value=config.get("enable_ml", False),
                help="Use machine learning model for predictions"
            )
    
    st.divider()
    
    # Save button with validation
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col2:
        if st.button("💾 Save Configuration", type="primary", use_container_width=True):
            # Build updated config
            updated_config = config.copy()
            
            # Update with new values - Trading Parameters
            updated_config["symbol"] = symbol
            updated_config["timeframe"] = timeframe
            updated_config["leverage"] = leverage
            updated_config["run_mode"] = mode
            updated_config["max_positions"] = max_positions
            
            # Risk Management
            updated_config["risk_per_trade"] = risk_per_trade
            updated_config["stop_loss_pct"] = stop_loss_pct
            updated_config["take_profit_pct"] = take_profit_pct
            updated_config["trailing_stop_activation"] = trailing_stop_activation
            updated_config["trailing_stop_distance"] = trailing_stop_distance
            updated_config["max_daily_loss"] = max_daily_loss
            
            # Indicators
            updated_config["adx_threshold"] = adx_threshold
            updated_config["adx_period"] = adx_period
            updated_config["atr_period"] = atr_period
            updated_config["rvol_threshold"] = rvol_threshold
            updated_config["rvol_period"] = rvol_period
            updated_config["ema_fast"] = ema_fast
            
            # Advanced Features
            updated_config["enable_adaptive_thresholds"] = enable_adaptive_thresholds
            updated_config["enable_multi_timeframe"] = enable_multi_timeframe
            updated_config["enable_volume_profile"] = enable_volume_profile
            updated_config["enable_ml_prediction"] = enable_ml_prediction
            updated_config["enable_advanced_exits"] = enable_advanced_exits
            updated_config["enable_regime_detection"] = enable_regime_detection
            
            if enable_adaptive_thresholds:
                updated_config["adaptive_threshold_min_adx"] = adaptive_threshold_min_adx
                updated_config["adaptive_threshold_max_adx"] = adaptive_threshold_max_adx
                updated_config["adaptive_threshold_min_rvol"] = adaptive_threshold_min_rvol
                updated_config["adaptive_threshold_max_rvol"] = adaptive_threshold_max_rvol
            
            if enable_multi_timeframe:
                updated_config["timeframe_entry"] = timeframe_entry
                updated_config["timeframe_filter"] = timeframe_filter
                updated_config["min_timeframe_alignment"] = min_timeframe_alignment
            
            if enable_advanced_exits:
                updated_config["exit_partial_1_percentage"] = exit_partial_1_percentage
                updated_config["exit_partial_2_percentage"] = exit_partial_2_percentage
                updated_config["exit_partial_1_atr_multiplier"] = exit_partial_1_atr_multiplier
                updated_config["exit_partial_2_atr_multiplier"] = exit_partial_2_atr_multiplier
            
            # Portfolio Management
            updated_config["enable_portfolio_management"] = enable_portfolio_management
            if enable_portfolio_management and symbols_text:
                portfolio_symbols = [s.strip() for s in symbols_text.split("\n") if s.strip()]
                updated_config["portfolio_symbols"] = portfolio_symbols
                updated_config["portfolio_max_symbols"] = portfolio_max_symbols
                updated_config["portfolio_max_total_risk"] = portfolio_max_total_risk
                updated_config["portfolio_max_single_allocation"] = portfolio_max_single_allocation
                updated_config["portfolio_correlation_threshold"] = portfolio_correlation_threshold
                updated_config["portfolio_correlation_max_exposure"] = portfolio_correlation_max_exposure
                updated_config["portfolio_correlation_lookback_days"] = portfolio_correlation_lookback_days
            
            # System
            updated_config["log_level"] = log_level
            updated_config["enable_ml"] = enable_ml
            
            # Save configuration
            success, message = config_editor.save_config(updated_config)
            
            if success:
                st.success(f"✅ {message}")
                st.info("⚠️ Restart the bot for changes to take effect.")
            else:
                st.error(f"❌ {message}")
    
    with col3:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            st.warning("Reset functionality would restore default values. Implement if needed.")
    
    st.divider()
    
    # Display current configuration summary
    with st.expander("📋 View Current Configuration (JSON)", expanded=False):
        st.json(config)


def show_controls_page():
    """Display controls page."""
    # Initialize bot controller and data provider
    from src.streamlit_bot_controller import BotController
    from src.streamlit_data_provider import StreamlitDataProvider
    
    bot_controller = BotController()
    data_provider = StreamlitDataProvider()
    
    # Initialize session state variables at the top
    if 'confirm_stop' not in st.session_state:
        st.session_state.confirm_stop = False
    if 'confirm_restart' not in st.session_state:
        st.session_state.confirm_restart = False
    if 'confirm_emergency' not in st.session_state:
        st.session_state.confirm_emergency = False
    
    # Get current bot status
    bot_status = data_provider.get_bot_status()
    is_running = bot_status["is_running"]
    
    # Display current status
    st.subheader("Current Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if is_running:
            st.success("✅ Bot is Running")
        else:
            st.error("⚠️ Bot is Stopped")
    
    with col2:
        if bot_status["last_update"]:
            st.info(f"Last Update: {bot_status['last_update'].strftime('%H:%M:%S')}")
        else:
            st.info("Last Update: N/A")
    
    with col3:
        positions = data_provider.get_open_positions()
        st.info(f"Open Positions: {len(positions)}")
    
    st.divider()
    
    # Control buttons section
    st.subheader("Bot Control Actions")
    
    col1, col2, col3 = st.columns(3)
    
    # Start Bot Button
    with col1:
        st.markdown("### Start Bot")
        st.write("Launch the trading bot process.")
        
        if is_running:
            st.button("▶️ Start Bot", disabled=True, use_container_width=True)
            st.caption("Bot is already running")
        else:
            if st.button("▶️ Start Bot", type="primary", use_container_width=True):
                with st.spinner("Starting bot..."):
                    success, message = bot_controller.start_bot()
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
    
    # Stop Bot Button
    with col2:
        st.markdown("### Stop Bot")
        st.write("Gracefully stop the trading bot.")
        
        if not is_running:
            st.button("⏹️ Stop Bot", disabled=True, use_container_width=True)
            st.caption("Bot is not running")
        else:
            if not st.session_state.confirm_stop:
                if st.button("⏹️ Stop Bot", use_container_width=True):
                    st.session_state.confirm_stop = True
                    st.rerun()
            else:
                st.warning("⚠️ Are you sure you want to stop the bot?")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✅ Yes, Stop", type="primary", use_container_width=True):
                        with st.spinner("Stopping bot..."):
                            success, message = bot_controller.stop_bot()
                            
                            if success:
                                st.success(f"✅ {message}")
                                st.session_state.confirm_stop = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                                st.session_state.confirm_stop = False
                
                with col_b:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.confirm_stop = False
                        st.rerun()
    
    # Emergency Close All Button
    with col3:
        st.markdown("### Emergency Close")
        st.write("⚠️ Close all positions immediately.")
        
        positions = data_provider.get_open_positions()
        
        if not positions:
            st.button("🚨 Emergency Close All", disabled=True, use_container_width=True)
            st.caption("No open positions")
        else:
            if not st.session_state.confirm_emergency:
                if st.button("🚨 Emergency Close All", use_container_width=True):
                    st.session_state.confirm_emergency = True
                    st.rerun()
            else:
                st.error(f"⚠️ This will close {len(positions)} position(s) at market price!")
                st.warning("This action cannot be undone!")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✅ Yes, Close All", type="primary", use_container_width=True):
                        with st.spinner("Closing all positions..."):
                            success, message = bot_controller.emergency_close_all(require_confirmation=False)
                            
                            if success:
                                st.success(f"✅ {message}")
                                st.session_state.confirm_emergency = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                                st.session_state.confirm_emergency = False
                
                with col_b:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.confirm_emergency = False
                        st.rerun()
    
    st.divider()
    
    # Additional controls section
    st.subheader("Additional Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Restart Bot")
        st.write("Stop and restart the bot.")
        
        if not st.session_state.confirm_restart:
            if st.button("🔄 Restart Bot", use_container_width=True):
                st.session_state.confirm_restart = True
                st.rerun()
        else:
            st.warning("⚠️ Restart the bot?")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Yes, Restart", type="primary", use_container_width=True):
                    with st.spinner("Restarting bot..."):
                        success, message = bot_controller.restart_bot()
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.session_state.confirm_restart = False
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                            st.session_state.confirm_restart = False
            
            with col_b:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.confirm_restart = False
                    st.rerun()
    
    with col2:
        st.markdown("### View Logs")
        st.write("Open the logs directory.")
        
        if st.button("📋 Open Logs Folder", use_container_width=True):
            import os
            import subprocess
            import platform
            
            logs_dir = os.path.abspath("logs")
            
            try:
                if platform.system() == "Windows":
                    os.startfile(logs_dir)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.Popen(["open", logs_dir])
                else:  # Linux
                    subprocess.Popen(["xdg-open", logs_dir])
                
                st.success("✅ Logs folder opened")
            except Exception as e:
                st.error(f"❌ Failed to open logs folder: {str(e)}")
                st.info(f"Logs location: {logs_dir}")
    
    with col3:
        st.markdown("### Refresh Data")
        st.write("Force refresh dashboard data.")
        
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.success("✅ Data refreshed")
            st.rerun()
    
    st.divider()
    
    # Safety warnings
    st.subheader("⚠️ Safety Information")
    
    with st.expander("Important Safety Guidelines", expanded=False):
        st.markdown("""
        ### Control Actions Safety
        
        **Start Bot:**
        - Ensure configuration is correct before starting
        - Verify API keys are properly set
        - Check that risk parameters are appropriate
        
        **Stop Bot:**
        - Bot will stop taking new positions
        - Existing positions remain open
        - Use this for configuration changes
        
        **Emergency Close All:**
        - ⚠️ **USE WITH EXTREME CAUTION**
        - Closes all positions at market price
        - May result in slippage
        - Cannot be undone
        - Only use in true emergencies
        
        **Restart Bot:**
        - Equivalent to Stop + Start
        - Useful after configuration changes
        - Existing positions remain open
        
        ### Best Practices
        
        1. Always monitor the bot during live trading
        2. Start with paper trading to test strategies
        3. Use appropriate position sizing and risk management
        4. Keep API keys secure and never share them
        5. Regularly review logs and performance metrics
        6. Have a plan for handling unexpected market conditions
        """)
    
    st.divider()
    st.caption("Controls page auto-refreshes every 5 seconds")


if __name__ == "__main__":
    main()
