"""Test script to verify momentum continuation filter works correctly."""

from src.config import Config
from src.strategy import StrategyEngine
from src.models import Candle
import time

def create_test_candles_exhausted_short():
    """Create candles showing an exhausted SHORT move (should be rejected)."""
    base_time = int(time.time() * 1000)
    candles = []
    
    # Simulate a strong drop that's now reversing
    prices = [
        (4.00, 4.05, 3.95, 4.00),  # -20: neutral
        (4.00, 4.02, 3.98, 3.99),  # -19: slight red
        (3.99, 4.00, 3.90, 3.92),  # -18: strong red (drop)
        (3.92, 3.95, 3.85, 3.87),  # -17: strong red (drop)
        (3.87, 3.90, 3.80, 3.82),  # -16: strong red (drop)
        (3.82, 3.88, 3.80, 3.86),  # -15: green (bounce)
        (3.86, 3.90, 3.84, 3.89),  # -14: green (bounce)
        (3.89, 3.92, 3.87, 3.90),  # -13: green (bounce)
        (3.90, 3.93, 3.88, 3.91),  # -12: green (consolidation)
        (3.91, 3.94, 3.89, 3.92),  # -11: green (consolidation)
    ]
    
    # Add more candles for EMA calculation
    for i in range(20):
        candles.append(Candle(
            timestamp=base_time - (30 - i) * 900000,
            open=4.00,
            high=4.05,
            low=3.95,
            close=4.00,
            volume=1000000
        ))
    
    # Add the test sequence
    for i, (open_p, high, low, close) in enumerate(prices):
        candles.append(Candle(
            timestamp=base_time - (10 - i) * 900000,
            open=open_p,
            high=high,
            low=low,
            close=close,
            volume=2000000  # High volume
        ))
    
    return candles

def create_test_candles_continuing_short():
    """Create candles showing a continuing SHORT move (should be accepted)."""
    base_time = int(time.time() * 1000)
    candles = []
    
    # Simulate a continuing downtrend
    prices = [
        (4.00, 4.05, 3.95, 4.00),  # -20: neutral
        (4.00, 4.02, 3.98, 3.99),  # -19: slight red
        (3.99, 4.00, 3.94, 3.95),  # -18: red
        (3.95, 3.96, 3.90, 3.91),  # -17: red
        (3.91, 3.92, 3.86, 3.87),  # -16: red
        (3.87, 3.88, 3.82, 3.83),  # -15: red
        (3.83, 3.85, 3.80, 3.81),  # -14: red
        (3.81, 3.82, 3.77, 3.78),  # -13: red (continuing)
        (3.78, 3.79, 3.74, 3.75),  # -12: red (continuing)
        (3.75, 3.76, 3.72, 3.73),  # -11: red (continuing)
    ]
    
    # Add more candles for EMA calculation
    for i in range(20):
        candles.append(Candle(
            timestamp=base_time - (30 - i) * 900000,
            open=4.00,
            high=4.05,
            low=3.95,
            close=4.00,
            volume=1000000
        ))
    
    # Add the test sequence
    for i, (open_p, high, low, close) in enumerate(prices):
        candles.append(Candle(
            timestamp=base_time - (10 - i) * 900000,
            open=open_p,
            high=high,
            low=low,
            close=close,
            volume=2000000  # High volume
        ))
    
    return candles

def test_momentum_filter():
    """Test the momentum continuation filter."""
    print("=" * 60)
    print("Testing Momentum Continuation Filter")
    print("=" * 60)
    
    # Create config and strategy
    config = Config()
    strategy = StrategyEngine(config)
    
    # Test 1: Exhausted SHORT move (should reject)
    print("\n[TEST 1] Exhausted SHORT move (should REJECT)")
    print("-" * 60)
    candles_exhausted = create_test_candles_exhausted_short()
    result_exhausted = strategy._check_momentum_continuation(candles_exhausted, "SHORT")
    
    print(f"Last 3 candles:")
    for i in range(-3, 0):
        c = candles_exhausted[i]
        color = "🟢 GREEN" if c.close > c.open else "🔴 RED"
        print(f"  Candle {i}: O={c.open:.2f} C={c.close:.2f} {color}")
    
    print(f"\nResult: {'✅ ACCEPTED' if result_exhausted else '❌ REJECTED'}")
    print(f"Expected: ❌ REJECTED (move is exhausted)")
    
    if not result_exhausted:
        print("✅ TEST PASSED - Correctly rejected exhausted move")
    else:
        print("❌ TEST FAILED - Should have rejected exhausted move")
    
    # Test 2: Continuing SHORT move (should accept)
    print("\n[TEST 2] Continuing SHORT move (should ACCEPT)")
    print("-" * 60)
    candles_continuing = create_test_candles_continuing_short()
    result_continuing = strategy._check_momentum_continuation(candles_continuing, "SHORT")
    
    print(f"Last 3 candles:")
    for i in range(-3, 0):
        c = candles_continuing[i]
        color = "🟢 GREEN" if c.close > c.open else "🔴 RED"
        print(f"  Candle {i}: O={c.open:.2f} C={c.close:.2f} {color}")
    
    print(f"\nResult: {'✅ ACCEPTED' if result_continuing else '❌ REJECTED'}")
    print(f"Expected: ✅ ACCEPTED (move is continuing)")
    
    if result_continuing:
        print("✅ TEST PASSED - Correctly accepted continuing move")
    else:
        print("❌ TEST FAILED - Should have accepted continuing move")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 2
    
    if not result_exhausted:
        tests_passed += 1
        print("✅ Test 1: PASSED (rejected exhausted move)")
    else:
        print("❌ Test 1: FAILED (should reject exhausted move)")
    
    if result_continuing:
        tests_passed += 1
        print("✅ Test 2: PASSED (accepted continuing move)")
    else:
        print("❌ Test 2: FAILED (should accept continuing move)")
    
    print(f"\nTotal: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("\n🎉 ALL TESTS PASSED! Momentum filter is working correctly.")
    else:
        print(f"\n⚠️  {tests_total - tests_passed} test(s) failed. Review the logic.")

if __name__ == "__main__":
    test_momentum_filter()
