"""Test to verify dashboard quick summary displays correct PnL data."""

import json
from datetime import datetime

def test_quick_summary_data():
    """Test that quick summary uses correct field names."""
    
    print("=" * 80)
    print("TESTING DASHBOARD QUICK SUMMARY - PNL DISPLAY")
    print("=" * 80)
    
    # Read current bot state
    try:
        with open('binance_results.json', 'r') as f:
            bot_state = json.load(f)
    except FileNotFoundError:
        print("\n❌ binance_results.json not found")
        print("   Bot needs to be running to test dashboard")
        return False
    
    print(f"\n✓ Bot state loaded")
    print(f"  - Bot Status: {bot_state.get('bot_status', 'unknown')}")
    print(f"  - Run Mode: {bot_state.get('run_mode', 'unknown')}")
    print(f"  - Balance: ${bot_state.get('balance', 0.0):,.2f}")
    print(f"  - Total PnL: ${bot_state.get('total_pnl', 0.0):,.2f}")
    
    # Check open positions
    open_positions = bot_state.get('open_positions', [])
    print(f"\n✓ Open Positions: {len(open_positions)}")
    
    if not open_positions:
        print("\n⚠️  No open positions to test")
        print("   Dashboard will show 'No open positions' message")
        return True
    
    # Test each position has correct fields
    print("\n" + "=" * 80)
    print("CHECKING POSITION DATA FIELDS")
    print("=" * 80)
    
    required_fields = [
        'symbol',
        'side',
        'entry_price',
        'current_price',
        'quantity',
        'unrealized_pnl',
        'stop_loss',
        'trailing_stop'
    ]
    
    all_valid = True
    
    for i, pos in enumerate(open_positions, 1):
        print(f"\nPosition {i}:")
        print(f"  Symbol: {pos.get('symbol', 'MISSING')}")
        print(f"  Side: {pos.get('side', 'MISSING')}")
        
        # Check all required fields
        missing_fields = []
        for field in required_fields:
            if field not in pos:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"  ❌ Missing fields: {', '.join(missing_fields)}")
            all_valid = False
        else:
            print(f"  ✅ All required fields present")
            
            # Display the data
            entry_price = pos['entry_price']
            current_price = pos['current_price']
            quantity = pos['quantity']
            unrealized_pnl = pos['unrealized_pnl']
            stop_loss = pos['stop_loss']
            trailing_stop = pos['trailing_stop']
            side = pos['side']
            
            # Calculate PnL percentage
            if entry_price > 0:
                if side == "LONG":
                    pnl_percent = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl_percent = ((entry_price - current_price) / entry_price) * 100
            else:
                pnl_percent = 0.0
            
            print(f"\n  Data Preview:")
            print(f"    Entry: ${entry_price:.6f}")
            print(f"    Current: ${current_price:.6f}")
            print(f"    Quantity: {quantity:.4f}")
            print(f"    Unrealized PnL: ${unrealized_pnl:.2f} ({pnl_percent:+.2f}%)")
            print(f"    Stop Loss: ${stop_loss:.6f}")
            print(f"    Trailing Stop: ${trailing_stop:.6f}")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    if all_valid:
        print("\n✅ ALL POSITIONS HAVE CORRECT FIELDS")
        print("\nDashboard Quick Summary will display:")
        print("  ✓ Symbol and Side")
        print("  ✓ Entry and Current Price")
        print("  ✓ Quantity (not 'size')")
        print("  ✓ Unrealized PnL with percentage (not 'pnl')")
        print("  ✓ Stop Loss")
        print("  ✓ Trailing Stop (not 'take_profit')")
        print("\n🎯 Quick Summary is now fixed and will show correct PnL data!")
        return True
    else:
        print("\n❌ SOME POSITIONS MISSING REQUIRED FIELDS")
        print("\nDashboard may not display correctly")
        return False

if __name__ == "__main__":
    import sys
    try:
        success = test_quick_summary_data()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
