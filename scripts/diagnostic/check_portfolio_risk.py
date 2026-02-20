"""Check if portfolio risk limits are blocking trades."""
import json
from binance.client import Client
from src.config import Config
from src.portfolio_manager import PortfolioManager

print("="*70)
print("PORTFOLIO RISK CHECK")
print("="*70)

# Load config
config = Config.load_from_file('config/config.json')

print(f"\n1. Configuration:")
print(f"   Portfolio Management: {config.enable_portfolio_management}")
print(f"   Max Total Risk: {config.portfolio_max_total_risk * 100}%")
print(f"   Risk per Trade: {config.risk_per_trade * 100}%")
print(f"   Max Symbols: {config.portfolio_max_symbols}")

if not config.enable_portfolio_management:
    print("\n⚠ Portfolio management is DISABLED")
    exit(0)

# Initialize portfolio manager
portfolio_mgr = PortfolioManager(config)

# Get wallet balance
client = Client(config.api_key, config.api_secret)
try:
    account = client.futures_account()
    wallet_balance = float(account['totalWalletBalance'])
    print(f"\n2. Wallet Balance: ${wallet_balance:.2f}")
except Exception as e:
    print(f"\n✗ Error getting wallet balance: {e}")
    wallet_balance = 10000.0  # Default
    print(f"   Using default: ${wallet_balance:.2f}")

# Check current positions
print(f"\n3. Checking open positions...")
try:
    positions = client.futures_position_information()
    open_positions = [p for p in positions if float(p['positionAmt']) != 0]
    
    if open_positions:
        print(f"   Found {len(open_positions)} open positions:")
        total_risk = 0
        for pos in open_positions:
            symbol = pos['symbol']
            amt = float(pos['positionAmt'])
            entry = float(pos['entryPrice'])
            unrealized = float(pos['unRealizedProfit'])
            
            # Calculate risk
            position_value = abs(amt * entry)
            risk_pct = (position_value / wallet_balance) * 100
            total_risk += risk_pct
            
            print(f"     {symbol}: {amt} @ ${entry:.4f}")
            print(f"       Value: ${position_value:.2f}")
            print(f"       Risk: {risk_pct:.2f}%")
            print(f"       Unrealized PnL: ${unrealized:.2f}")
        
        print(f"\n   Total Risk: {total_risk:.2f}%")
        print(f"   Max Allowed: {config.portfolio_max_total_risk * 100}%")
        
        if total_risk >= config.portfolio_max_total_risk * 100:
            print(f"   ✗ RISK LIMIT EXCEEDED - New trades blocked!")
        else:
            remaining = (config.portfolio_max_total_risk * 100) - total_risk
            print(f"   ✓ Risk OK - {remaining:.2f}% remaining")
    else:
        print(f"   No open positions")
        print(f"   ✓ Risk OK - Can open new trades")
        
except Exception as e:
    print(f"   ✗ Error checking positions: {e}")

# Check if we can open a new trade
print(f"\n4. Can open new trade?")
can_trade = portfolio_mgr.check_total_risk(wallet_balance)
if can_trade:
    print(f"   ✓ YES - Portfolio risk check passed")
else:
    print(f"   ✗ NO - Portfolio risk limit exceeded")

print(f"\n{'='*70}")
print("CHECK COMPLETE")
print(f"{'='*70}")
