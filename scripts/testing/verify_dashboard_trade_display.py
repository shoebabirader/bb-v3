"""
Verify that the dashboard can display trade history correctly
"""

from src.streamlit_data_provider import StreamlitDataProvider

print("=" * 80)
print("DASHBOARD TRADE DISPLAY VERIFICATION")
print("=" * 80)

# Initialize data provider (same as dashboard does)
data_provider = StreamlitDataProvider()

# Get trade history (same as dashboard does)
print("\n1. Getting trade history (limit=20)...")
trades = data_provider.get_trade_history(limit=20)
print(f"   ✓ Retrieved {len(trades)} trades")

if not trades:
    print("\n   ✗ ERROR: No trades returned!")
    print("   This means the dashboard will show 'No trade history available'")
else:
    print("\n2. Trade summary:")
    winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
    losing_trades = sum(1 for t in trades if t.get('pnl', 0) < 0)
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    
    print(f"   Total Trades: {len(trades)}")
    print(f"   Winning Trades: {winning_trades}")
    print(f"   Losing Trades: {losing_trades}")
    print(f"   Total PnL: ${total_pnl:.2f}")
    print(f"   Win Rate: {(winning_trades / len(trades) * 100):.1f}%")
    
    print("\n3. Sample trades (first 5):")
    for i, trade in enumerate(trades[:5], 1):
        symbol = trade.get('symbol', 'N/A')
        side = trade.get('side', 'N/A')
        pnl = trade.get('pnl', 0)
        pnl_percent = trade.get('pnl_percent', 0)
        exit_reason = trade.get('exit_reason', 'N/A')
        
        pnl_indicator = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        print(f"   {i}. {pnl_indicator} {symbol} {side} - ${pnl:.2f} ({pnl_percent:+.2f}%) - {exit_reason}")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print("\nIf you see trades above, the dashboard SHOULD display them.")
print("If the dashboard is not showing trades, try:")
print("  1. Refresh the browser (Ctrl+F5 or Cmd+Shift+R)")
print("  2. Restart the Streamlit dashboard")
print("  3. Clear browser cache")
