"""Explain how leverage and position sizing works with current balance."""

import json

print("=" * 80)
print("LEVERAGE & POSITION SIZING EXPLANATION")
print("=" * 80)

# Load config and current state
with open('config/config.json', 'r') as f:
    config = json.load(f)

with open('binance_results.json', 'r') as f:
    state = json.load(f)

# Key parameters
initial_balance = 15.07
current_balance = state['balance']
leverage = config['leverage']
risk_per_trade = config['risk_per_trade']
take_profit_pct = config['take_profit_pct']
portfolio_max_total_risk = config['portfolio_max_total_risk']
max_positions = config['max_positions']

print(f"\n📊 YOUR CONFIGURATION:")
print(f"   Initial Balance: ${initial_balance:.2f}")
print(f"   Current Balance: ${current_balance:.2f}")
print(f"   Leverage: {leverage}x")
print(f"   Risk per Trade: {risk_per_trade*100}% ({risk_per_trade})")
print(f"   Take Profit: {take_profit_pct*100}% ({take_profit_pct})")
print(f"   Max Total Risk: {portfolio_max_total_risk*100}%")
print(f"   Max Positions: {max_positions}")

print("\n" + "=" * 80)
print("🔍 HOW POSITION SIZING WORKS")
print("=" * 80)

print(f"\n1️⃣ RISK PER TRADE CALCULATION:")
print(f"   Your balance: ${initial_balance:.2f}")
print(f"   Risk per trade: {risk_per_trade*100}% = ${initial_balance * risk_per_trade:.2f}")
print(f"   ")
print(f"   This means you risk ${initial_balance * risk_per_trade:.2f} per trade")
print(f"   (This is the maximum you can LOSE, not the position size)")

print(f"\n2️⃣ PORTFOLIO RISK MANAGEMENT:")
print(f"   Max total risk: {portfolio_max_total_risk*100}%")
print(f"   Max positions: {max_positions}")
print(f"   ")
print(f"   With {max_positions} positions:")
print(f"   - Total risk exposure: {max_positions} × {risk_per_trade*100}% = {max_positions * risk_per_trade * 100}%")
print(f"   - But capped at: {portfolio_max_total_risk*100}%")
print(f"   ")
print(f"   So actual risk per trade is REDUCED:")
print(f"   - {portfolio_max_total_risk*100}% ÷ {max_positions} = {portfolio_max_total_risk/max_positions*100:.1f}% per trade")
print(f"   - Risk amount: ${initial_balance * (portfolio_max_total_risk/max_positions):.2f} per trade")

print(f"\n3️⃣ POSITION SIZE CALCULATION:")
print(f"   Risk per trade: ${initial_balance * (portfolio_max_total_risk/max_positions):.2f}")
print(f"   Stop loss distance: ~2% (based on ATR)")
print(f"   ")
print(f"   Position size = Risk ÷ Stop Loss %")
print(f"   Position size = ${initial_balance * (portfolio_max_total_risk/max_positions):.2f} ÷ 0.02")
print(f"   Position size = ${initial_balance * (portfolio_max_total_risk/max_positions) / 0.02:.2f}")
print(f"   ")
print(f"   This is your NOTIONAL position value (with leverage)")

print(f"\n4️⃣ MARGIN USED (COLLATERAL):")
print(f"   Position size: ${initial_balance * (portfolio_max_total_risk/max_positions) / 0.02:.2f}")
print(f"   Leverage: {leverage}x")
print(f"   ")
print(f"   Margin = Position Size ÷ Leverage")
print(f"   Margin = ${initial_balance * (portfolio_max_total_risk/max_positions) / 0.02:.2f} ÷ {leverage}")
print(f"   Margin = ${initial_balance * (portfolio_max_total_risk/max_positions) / 0.02 / leverage:.2f}")
print(f"   ")
print(f"   So each position uses ~${initial_balance * (portfolio_max_total_risk/max_positions) / 0.02 / leverage:.2f} of your balance")

print("\n" + "=" * 80)
print("📈 YOUR CURRENT POSITIONS")
print("=" * 80)

total_margin_used = 0
total_position_value = 0

for i, pos in enumerate(state['open_positions'], 1):
    symbol = pos['symbol']
    entry_price = pos['entry_price']
    quantity = pos['quantity']
    unrealized_pnl = pos['unrealized_pnl']
    
    position_value = entry_price * quantity
    margin_used = position_value / leverage
    
    total_margin_used += margin_used
    total_position_value += position_value
    
    print(f"\n{i}. {symbol}:")
    print(f"   Entry Price: ${entry_price}")
    print(f"   Quantity: {quantity:.2f}")
    print(f"   Position Value: ${position_value:.2f}")
    print(f"   Margin Used: ${margin_used:.2f}")
    print(f"   Unrealized PnL: ${unrealized_pnl:.2f}")

print(f"\n📊 TOTALS:")
print(f"   Total Position Value: ${total_position_value:.2f}")
print(f"   Total Margin Used: ${total_margin_used:.2f}")
print(f"   Free Balance: ${current_balance - total_margin_used:.2f}")
print(f"   Balance Utilization: {total_margin_used/current_balance*100:.1f}%")

print("\n" + "=" * 80)
print("💰 WHY PROFITS SEEM SMALL")
print("=" * 80)

print(f"\n❌ COMMON MISCONCEPTION:")
print(f"   \"I have {leverage}x leverage, so 1% price move = {leverage}% profit\"")
print(f"   ")
print(f"   This is WRONG! Here's why:")

print(f"\n✅ REALITY:")
print(f"   1. Your position size is LIMITED by risk management")
print(f"   2. Risk per trade: {portfolio_max_total_risk/max_positions*100:.1f}% of balance")
print(f"   3. Position size: ~${initial_balance * (portfolio_max_total_risk/max_positions) / 0.02:.2f}")
print(f"   4. Margin used: ~${initial_balance * (portfolio_max_total_risk/max_positions) / 0.02 / leverage:.2f}")
print(f"   ")
print(f"   With {take_profit_pct*100}% take profit:")
print(f"   - Position value: ${initial_balance * (portfolio_max_total_risk/max_positions) / 0.02:.2f}")
print(f"   - Price move: {take_profit_pct*100}%")
print(f"   - Profit: ${initial_balance * (portfolio_max_total_risk/max_positions) / 0.02:.2f} × {take_profit_pct}")
print(f"   - Profit: ${initial_balance * (portfolio_max_total_risk/max_positions) / 0.02 * take_profit_pct:.2f}")
print(f"   ")
print(f"   As % of balance: ${initial_balance * (portfolio_max_total_risk/max_positions) / 0.02 * take_profit_pct:.2f} ÷ ${initial_balance:.2f}")
print(f"   = {initial_balance * (portfolio_max_total_risk/max_positions) / 0.02 * take_profit_pct / initial_balance * 100:.2f}% per trade")

print("\n" + "=" * 80)
print("🎯 YOUR ACTUAL PERFORMANCE")
print("=" * 80)

total_trades = state['total_trades']
winning_trades = state['winning_trades']
total_pnl = state['total_pnl']
total_pnl_percent = state['total_pnl_percent']

print(f"\n📊 Results:")
print(f"   Total Trades: {total_trades}")
print(f"   Winning Trades: {winning_trades}")
print(f"   Win Rate: {winning_trades/total_trades*100:.0f}%")
print(f"   Total PnL: ${total_pnl:.2f}")
print(f"   Total Return: {total_pnl_percent:.2f}%")
print(f"   Avg per Trade: ${total_pnl/total_trades:.2f}")

print("\n" + "=" * 80)
print("💡 HOW TO INCREASE PROFITS")
print("=" * 80)

print(f"\n1️⃣ INCREASE TAKE PROFIT:")
print(f"   Current: {take_profit_pct*100}%")
print(f"   Suggestion: 2-4% (0.02-0.04)")
print(f"   Impact: 2-4x more profit per trade")

print(f"\n2️⃣ INCREASE RISK PER TRADE:")
print(f"   Current: {portfolio_max_total_risk/max_positions*100:.1f}% per trade")
print(f"   Suggestion: Increase portfolio_max_total_risk to 0.15 (15%)")
print(f"   Impact: 50% larger positions = 50% more profit")

print(f"\n3️⃣ REDUCE MAX POSITIONS:")
print(f"   Current: {max_positions} positions")
print(f"   Suggestion: 2 positions")
print(f"   Impact: Each position gets more capital")

print(f"\n4️⃣ INCREASE BALANCE:")
print(f"   Current: ${initial_balance:.2f}")
print(f"   Suggestion: $50-100")
print(f"   Impact: Larger positions = more profit in dollars")

print(f"\n⚠️  IMPORTANT:")
print(f"   - Leverage doesn't directly increase profits")
print(f"   - Leverage reduces margin requirements")
print(f"   - Profits come from: Position Size × Price Move")
print(f"   - Your position size is limited by risk management")
print(f"   - This is GOOD - it protects you from large losses")

print("\n" + "=" * 80)
print("📋 RECOMMENDED CHANGES")
print("=" * 80)

print(f"\nFor better profits while maintaining safety:")
print(f"   1. Change take_profit_pct: 0.01 → 0.04 (4%)")
print(f"   2. Change portfolio_max_total_risk: 0.1 → 0.15 (15%)")
print(f"   3. Keep max_positions: 3")
print(f"   ")
print(f"   Expected profit per trade: ~${initial_balance * 0.15 / 3 / 0.02 * 0.04:.2f}")
print(f"   Expected return per trade: ~{0.15 / 3 / 0.02 * 0.04 * 100:.1f}%")

print("\n" + "=" * 80)
