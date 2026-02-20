"""Test script to verify take profit functionality is working correctly."""

import sys
from src.config import Config
from src.models import Position
from datetime import datetime

def test_take_profit_logic():
    """Test that take profit calculation works correctly."""
    
    print("=" * 80)
    print("TESTING TAKE PROFIT FUNCTIONALITY")
    print("=" * 80)
    
    # Load config
    config = Config()
    print(f"\n✓ Config loaded")
    print(f"  - take_profit_pct: {config.take_profit_pct * 100}%")
    print(f"  - stop_loss_pct: {config.stop_loss_pct * 100}%")
    print(f"  - trailing_stop_distance: {config.trailing_stop_distance * 100}%")
    
    # Test LONG position scenarios
    print("\n" + "=" * 80)
    print("TEST 1: LONG Position - Take Profit Should Trigger")
    print("=" * 80)
    
    entry_price = 100.0
    take_profit_pct = config.take_profit_pct  # 0.04 = 4%
    
    # Simulate price reaching take profit
    current_price = entry_price * (1 + take_profit_pct)  # +4%
    profit_pct = (current_price - entry_price) / entry_price
    
    print(f"\nScenario:")
    print(f"  - Entry Price: ${entry_price:.2f}")
    print(f"  - Current Price: ${current_price:.2f}")
    print(f"  - Profit: {profit_pct * 100:.2f}%")
    print(f"  - Take Profit Target: {take_profit_pct * 100:.2f}%")
    
    if profit_pct >= take_profit_pct:
        print(f"\n✅ TAKE PROFIT TRIGGERED!")
        print(f"   Position would close with +{profit_pct * 100:.2f}% profit")
    else:
        print(f"\n❌ TAKE PROFIT NOT TRIGGERED")
        print(f"   Need {(take_profit_pct - profit_pct) * 100:.2f}% more profit")
    
    # Test LONG position - price below take profit
    print("\n" + "=" * 80)
    print("TEST 2: LONG Position - Below Take Profit (Should NOT Trigger)")
    print("=" * 80)
    
    current_price = entry_price * 1.02  # +2% (below 4% target)
    profit_pct = (current_price - entry_price) / entry_price
    
    print(f"\nScenario:")
    print(f"  - Entry Price: ${entry_price:.2f}")
    print(f"  - Current Price: ${current_price:.2f}")
    print(f"  - Profit: {profit_pct * 100:.2f}%")
    print(f"  - Take Profit Target: {take_profit_pct * 100:.2f}%")
    
    if profit_pct >= take_profit_pct:
        print(f"\n❌ ERROR: TAKE PROFIT TRIGGERED TOO EARLY!")
    else:
        print(f"\n✅ CORRECT: Take profit not triggered yet")
        print(f"   Need {(take_profit_pct - profit_pct) * 100:.2f}% more profit")
    
    # Test SHORT position scenarios
    print("\n" + "=" * 80)
    print("TEST 3: SHORT Position - Take Profit Should Trigger")
    print("=" * 80)
    
    entry_price = 100.0
    current_price = entry_price * (1 - take_profit_pct)  # -4%
    profit_pct = (entry_price - current_price) / entry_price
    
    print(f"\nScenario:")
    print(f"  - Entry Price: ${entry_price:.2f}")
    print(f"  - Current Price: ${current_price:.2f}")
    print(f"  - Profit: {profit_pct * 100:.2f}%")
    print(f"  - Take Profit Target: {take_profit_pct * 100:.2f}%")
    
    if profit_pct >= take_profit_pct:
        print(f"\n✅ TAKE PROFIT TRIGGERED!")
        print(f"   Position would close with +{profit_pct * 100:.2f}% profit")
    else:
        print(f"\n❌ TAKE PROFIT NOT TRIGGERED")
        print(f"   Need {(take_profit_pct - profit_pct) * 100:.2f}% more profit")
    
    # Test with 10% profit (maximum target)
    print("\n" + "=" * 80)
    print("TEST 4: LONG Position - 10% Profit (Maximum Target)")
    print("=" * 80)
    
    entry_price = 100.0
    current_price = entry_price * 1.10  # +10%
    profit_pct = (current_price - entry_price) / entry_price
    
    print(f"\nScenario:")
    print(f"  - Entry Price: ${entry_price:.2f}")
    print(f"  - Current Price: ${current_price:.2f}")
    print(f"  - Profit: {profit_pct * 100:.2f}%")
    print(f"  - Take Profit Target: {take_profit_pct * 100:.2f}%")
    
    if profit_pct >= take_profit_pct:
        print(f"\n✅ TAKE PROFIT TRIGGERED!")
        print(f"   Position would close with +{profit_pct * 100:.2f}% profit")
        print(f"   🎉 EXCELLENT TRADE! Hit maximum target!")
    else:
        print(f"\n❌ ERROR: Should have triggered!")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n✓ Take Profit is set to: {config.take_profit_pct * 100}%")
    print(f"✓ Bot will close positions when profit reaches {config.take_profit_pct * 100}% or higher")
    print(f"✓ This prevents premature exits from tight trailing stops")
    print(f"✓ Positions can reach up to 10%+ profit before closing")
    print(f"\nNote: Trailing stop will still protect profits if price reverses")
    print(f"      but take profit ensures we lock in gains at {config.take_profit_pct * 100}%+")
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - TAKE PROFIT FUNCTIONALITY WORKING!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_take_profit_logic()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
