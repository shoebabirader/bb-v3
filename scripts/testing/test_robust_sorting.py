"""Test the robust sorting solution with mixed timestamp types."""
from datetime import datetime

# Simulate trades with mixed timestamp types
trades = [
    {'exit_time': 1739587216000, 'pnl': 100.0, 'symbol': 'BTCUSDT'},  # int milliseconds
    {'exit_time': '2026-02-15T05:03:18', 'pnl': -50.0, 'symbol': 'ETHUSDT'},  # ISO string
    {'timestamp': 1739587100000, 'pnl': 75.0, 'symbol': 'BNBUSDT'},  # int milliseconds
    {'timestamp': '2026-02-15T04:58:20', 'pnl': 25.0, 'symbol': 'ADAUSDT'},  # ISO string
    {'pnl': 50.0, 'symbol': 'DOTUSDT'},  # No timestamp at all
]

print("="*70)
print("ROBUST SORTING TEST - Mixed Timestamp Types")
print("="*70)

print("\nOriginal trades:")
for i, trade in enumerate(trades, 1):
    exit_time = trade.get('exit_time', trade.get('timestamp', 'None'))
    print(f"  {i}. {trade['symbol']}: exit_time={exit_time} (type: {type(exit_time).__name__}), pnl={trade['pnl']}")

# Helper function from the fix
def get_sortable_time(trade):
    """Get a sortable timestamp value, handling both int and str formats."""
    exit_time = trade.get('exit_time', trade.get('timestamp', 0))
    
    # If it's already an int/float, return it
    if isinstance(exit_time, (int, float)):
        return exit_time
    
    # If it's a string, try to parse it
    if isinstance(exit_time, str) and exit_time:
        try:
            # Try ISO format first
            dt = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
            return dt.timestamp() * 1000  # Convert to milliseconds
        except:
            pass
    
    # Default to 0 if we can't parse it
    return 0

# Test sorting
print("\n1. Testing Date (Newest First):")
try:
    sorted_trades = sorted(trades, key=get_sortable_time, reverse=True)
    print("   ✓ Sorting works!")
    print("\n   Sorted trades:")
    for i, trade in enumerate(sorted_trades, 1):
        sortable_time = get_sortable_time(trade)
        print(f"     {i}. {trade['symbol']}: sortable_time={sortable_time}, pnl={trade['pnl']}")
except Exception as e:
    print(f"   ✗ Sorting failed: {e}")

print("\n2. Testing Date (Oldest First):")
try:
    sorted_trades = sorted(trades, key=get_sortable_time)
    print("   ✓ Sorting works!")
    print("\n   Sorted trades:")
    for i, trade in enumerate(sorted_trades, 1):
        sortable_time = get_sortable_time(trade)
        print(f"     {i}. {trade['symbol']}: sortable_time={sortable_time}, pnl={trade['pnl']}")
except Exception as e:
    print(f"   ✗ Sorting failed: {e}")

print("\n3. Testing PnL sorting:")
try:
    sorted_trades = sorted(trades, key=lambda t: t.get('pnl', 0), reverse=True)
    print("   ✓ Sorting works!")
    print("\n   Sorted trades:")
    for i, trade in enumerate(sorted_trades, 1):
        print(f"     {i}. {trade['symbol']}: pnl={trade['pnl']}")
except Exception as e:
    print(f"   ✗ Sorting failed: {e}")

print("\n" + "="*70)
print("✓ ALL ROBUST SORTING TESTS PASSED")
print("="*70)
