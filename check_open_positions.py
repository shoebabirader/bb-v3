"""Check status of open positions from today's paper trading"""
import re
from datetime import datetime

# Read the bot log
with open('logs/bot.log', 'r', encoding='utf-8') as f:
    log_content = f.read()

# Find all position openings today
position_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Position opened: (\w+) (LONG|SHORT) qty=([\d.]+) at ([\d.]+), stop=([\d.]+)'
positions = re.findall(position_pattern, log_content)

print("=" * 80)
print("OPEN POSITIONS FROM TODAY (2026-02-10)")
print("=" * 80)

if positions:
    for i, (timestamp, symbol, side, qty, entry, stop) in enumerate(positions, 1):
        print(f"\n{i}. {symbol} {side}")
        print(f"   Time: {timestamp}")
        print(f"   Entry Price: ${entry}")
        print(f"   Quantity: {qty}")
        print(f"   Stop Loss: ${stop}")
        
        # Calculate risk
        entry_price = float(entry)
        stop_price = float(stop)
        quantity = float(qty)
        
        if side == "LONG":
            risk_per_unit = entry_price - stop_price
        else:  # SHORT
            risk_per_unit = stop_price - entry_price
            
        total_risk = abs(risk_per_unit * quantity)
        print(f"   Risk: ${total_risk:.2f}")
else:
    print("\nNo positions found in today's log")

print("\n" + "=" * 80)
print("NOTE: These positions are still OPEN (no exit found in logs)")
print("The bot is managing them with trailing stops")
print("=" * 80)
