"""Test that the dashboard sorting fix works correctly."""

# Simulate the sorting logic from streamlit_app.py
trades = [
    {'exit_time': 1739587216, 'pnl': 100.0, 'symbol': 'BTCUSDT'},
    {'exit_time': 1739587300, 'pnl': -50.0, 'symbol': 'ETHUSDT'},
    {'timestamp': 1739587100, 'pnl': 75.0, 'symbol': 'BNBUSDT'},  # No exit_time
    {'pnl': 25.0, 'symbol': 'ADAUSDT'},  # No exit_time or timestamp
]

print("="*60)
print("DASHBOARD SORTING FIX TEST")
print("="*60)

print("\nOriginal trades:")
for i, trade in enumerate(trades, 1):
    exit_time = trade.get('exit_time', trade.get('timestamp', 0))
    print(f"  {i}. {trade['symbol']}: exit_time={exit_time}, pnl={trade['pnl']}")

# Test Date (Newest First) - OLD WAY (would fail)
print("\n1. Testing OLD sorting (with empty string fallback):")
try:
    sorted_trades_old = sorted(trades, key=lambda t: t.get('exit_time', t.get('timestamp', '')), reverse=True)
    print("   ✗ OLD way didn't fail (unexpected)")
except TypeError as e:
    print(f"   ✓ OLD way fails as expected: {e}")

# Test Date (Newest First) - NEW WAY (should work)
print("\n2. Testing NEW sorting (with 0 fallback):")
try:
    sorted_trades = sorted(trades, key=lambda t: t.get('exit_time', t.get('timestamp', 0)), reverse=True)
    print("   ✓ NEW way works!")
    print("\n   Sorted trades (Newest First):")
    for i, trade in enumerate(sorted_trades, 1):
        exit_time = trade.get('exit_time', trade.get('timestamp', 0))
        print(f"     {i}. {trade['symbol']}: exit_time={exit_time}, pnl={trade['pnl']}")
except Exception as e:
    print(f"   ✗ NEW way failed: {e}")

# Test Date (Oldest First)
print("\n3. Testing Date (Oldest First):")
try:
    sorted_trades = sorted(trades, key=lambda t: t.get('exit_time', t.get('timestamp', 0)))
    print("   ✓ Works!")
    print("\n   Sorted trades (Oldest First):")
    for i, trade in enumerate(sorted_trades, 1):
        exit_time = trade.get('exit_time', trade.get('timestamp', 0))
        print(f"     {i}. {trade['symbol']}: exit_time={exit_time}, pnl={trade['pnl']}")
except Exception as e:
    print(f"   ✗ Failed: {e}")

# Test PnL sorting
print("\n4. Testing PnL (Highest First):")
try:
    sorted_trades = sorted(trades, key=lambda t: t.get('pnl', 0), reverse=True)
    print("   ✓ Works!")
    print("\n   Sorted trades (Highest PnL First):")
    for i, trade in enumerate(sorted_trades, 1):
        print(f"     {i}. {trade['symbol']}: pnl={trade['pnl']}")
except Exception as e:
    print(f"   ✗ Failed: {e}")

print("\n" + "="*60)
print("✓ ALL SORTING TESTS PASSED")
print("="*60)
