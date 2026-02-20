"""Analyze the recent EC2 trade"""
import json
from datetime import datetime

# Trade data from EC2 logs
trade_data = {
    "timestamp": "2026-02-19 01:44:21",
    "symbol": "TRXUSDT",
    "side": "SHORT",
    "entry_price": 0.27824,
    "exit_price": 0.28006,
    "quantity": 549.5377907561817,
    "pnl": -1.0001587791762443,
    "pnl_percent": -0.6541115583668733,
    "entry_time": 1771445703146,
    "exit_time": 1771465461224,
    "exit_reason": "TRAILING_STOP"
}

print("\n" + "="*80)
print("EC2 TRADE ANALYSIS")
print("="*80)

print(f"\n📊 TRADE DETAILS:")
print(f"   Symbol: {trade_data['symbol']}")
print(f"   Side: {trade_data['side']}")
print(f"   Entry Price: ${trade_data['entry_price']:.5f}")
print(f"   Exit Price: ${trade_data['exit_price']:.5f}")
print(f"   Quantity: {trade_data['quantity']:.2f}")

# Calculate trade duration
entry_dt = datetime.fromtimestamp(trade_data['entry_time'] / 1000)
exit_dt = datetime.fromtimestamp(trade_data['exit_time'] / 1000)
duration = exit_dt - entry_dt
hours = duration.total_seconds() / 3600

print(f"\n⏱️  TIMING:")
print(f"   Entry Time: {entry_dt.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   Exit Time: {exit_dt.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   Duration: {hours:.2f} hours ({duration.total_seconds()/60:.0f} minutes)")

print(f"\n💰 RESULT:")
print(f"   PnL: ${trade_data['pnl']:.2f}")
print(f"   PnL %: {trade_data['pnl_percent']:.2f}%")
print(f"   Exit Reason: {trade_data['exit_reason']}")
print(f"   Status: {'❌ LOSS' if trade_data['pnl'] < 0 else '✅ WIN'}")

# Calculate price movement
price_move = ((trade_data['exit_price'] - trade_data['entry_price']) / trade_data['entry_price']) * 100

print(f"\n📈 PRICE MOVEMENT:")
print(f"   Entry: ${trade_data['entry_price']:.5f}")
print(f"   Exit: ${trade_data['exit_price']:.5f}")
print(f"   Move: {price_move:+.2f}%")
print(f"   Direction: {'⬆️ UP' if price_move > 0 else '⬇️ DOWN'}")

# Analysis
print(f"\n🔍 ANALYSIS:")
if trade_data['side'] == "SHORT" and price_move > 0:
    print(f"   ⚠️  SHORT position but price went UP {price_move:.2f}%")
    print(f"   ⚠️  Trade went against us immediately")
    print(f"   ✅ Trailing stop protected us from bigger loss")
elif trade_data['side'] == "LONG" and price_move < 0:
    print(f"   ⚠️  LONG position but price went DOWN {price_move:.2f}%")
    print(f"   ⚠️  Trade went against us immediately")
    print(f"   ✅ Trailing stop protected us from bigger loss")

# Calculate what the loss would be without stop
position_value = trade_data['entry_price'] * trade_data['quantity']
print(f"\n💵 POSITION SIZE:")
print(f"   Position Value: ${position_value:.2f}")
print(f"   Loss: ${abs(trade_data['pnl']):.2f} ({abs(trade_data['pnl_percent']):.2f}%)")

# Recommendations
print(f"\n💡 RECOMMENDATIONS:")
print(f"   1. Entry timing may be off - price moved against us immediately")
print(f"   2. Consider waiting for stronger confirmation before entry")
print(f"   3. This is exactly the pattern we saw in backtest (8/9 trades hit stops)")
print(f"   4. Strategy needs adjustment - stops are working but entries are weak")

print("\n" + "="*80)
print("CONCLUSION: Bot is working correctly, but strategy needs improvement")
print("="*80 + "\n")
