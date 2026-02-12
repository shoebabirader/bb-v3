"""Check if position PnL is being updated correctly."""

from binance.client import Client
from src.config import Config
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer
from src.data_manager import DataManager

config = Config.load_from_file()
client = Client(config.api_key, config.api_secret)

# Initialize components
data_manager = DataManager(config, client)
position_sizer = PositionSizer(config)
risk_manager = RiskManager(config, position_sizer)

print("=" * 80)
print("POSITION PNL UPDATE CHECK")
print("=" * 80)
print()

# Get active positions
positions = risk_manager.get_all_active_positions()

print(f"Active Positions: {len(positions)}")
print()

if not positions:
    print("❌ No active positions found")
    print()
    print("This means:")
    print("  1. Bot hasn't opened any positions yet")
    print("  2. Or positions were closed")
    print("  3. Or bot is running but not in the same process")
    print()
    print("To check if bot is running:")
    print("  python check_if_bot_running.py")
else:
    for pos in positions:
        print(f"Position: {pos.symbol}")
        print("-" * 80)
        print(f"  Side: {pos.side}")
        print(f"  Entry Price: ${pos.entry_price:.4f}")
        print(f"  Quantity: {pos.quantity:.4f}")
        print(f"  Stop Loss: ${pos.stop_loss:.4f}")
        print(f"  Trailing Stop: ${pos.trailing_stop:.4f}")
        print(f"  Unrealized PnL: ${pos.unrealized_pnl:.2f}")
        print()
        
        # Try to get current price for this symbol
        try:
            candles = data_manager.fetch_historical_data(days=1, timeframe="15m", symbol=pos.symbol)
            if candles:
                current_price = candles[-1].close
                print(f"  Current Price: ${current_price:.4f}")
                
                # Calculate what PnL should be
                if pos.side == "LONG":
                    expected_pnl = (current_price - pos.entry_price) * pos.quantity
                else:
                    expected_pnl = (pos.entry_price - current_price) * pos.quantity
                
                print(f"  Expected PnL: ${expected_pnl:.2f}")
                print()
                
                if abs(pos.unrealized_pnl - expected_pnl) > 0.01:
                    print("  ⚠️  WARNING: Stored PnL doesn't match calculated PnL!")
                    print("     This means PnL is not being updated in real-time")
                else:
                    print("  ✓ PnL is correct")
            else:
                print("  ❌ Could not fetch current price")
        except Exception as e:
            print(f"  ❌ Error fetching price: {e}")
        
        print()

print("=" * 80)
print("DIAGNOSIS")
print("=" * 80)
print()

if not positions:
    print("No positions to check.")
    print()
    print("If you see a position in the UI but not here:")
    print("  1. The UI might be showing stale data")
    print("  2. The position might be in a different process")
    print("  3. Try restarting the bot")
else:
    print("Positions found. Check above for PnL accuracy.")
    print()
    print("If PnL is not updating in UI:")
    print("  1. Check if bot is actually running (not frozen)")
    print("  2. Check if WebSocket is connected")
    print("  3. Check if data is being received")
    print("  4. Try restarting the bot")

print()
print("To check bot status:")
print("  python check_if_bot_running.py")
print()
print("To check WebSocket connection:")
print("  Check bot logs for 'WebSocket' messages")
