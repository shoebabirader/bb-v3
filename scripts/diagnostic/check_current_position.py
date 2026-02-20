import sys
sys.path.append('src')

from binance.client import Client
from config import Config
import json

config = Config()
client = Client(config.api_key, config.api_secret, testnet=False)

print("\n" + "="*80)
print("CHECKING CURRENT POSITIONS")
print("="*80 + "\n")

# Get account info
account = client.futures_account()
print(f"Wallet Balance: ${float(account['totalWalletBalance']):.2f}")
print(f"Available Balance: ${float(account['availableBalance']):.2f}")
print(f"Total Unrealized PnL: ${float(account['totalUnrealizedProfit']):.2f}")

# Get positions
positions = client.futures_position_information()

print("\n--- OPEN POSITIONS ---")
open_positions = [p for p in positions if float(p['positionAmt']) != 0]

if not open_positions:
    print("No open positions")
else:
    for pos in open_positions:
        symbol = pos['symbol']
        side = "LONG" if float(pos['positionAmt']) > 0 else "SHORT"
        entry_price = float(pos['entryPrice'])
        quantity = abs(float(pos['positionAmt']))
        unrealized_pnl = float(pos['unRealizedProfit'])
        mark_price = float(pos['markPrice'])
        
        print(f"\n{symbol}:")
        print(f"  Side: {side}")
        print(f"  Entry Price: ${entry_price:.4f}")
        print(f"  Current Price: ${mark_price:.4f}")
        print(f"  Quantity: {quantity}")
        print(f"  Unrealized PnL: ${unrealized_pnl:.2f}")

print("\n" + "="*80 + "\n")
