"""Calculate config for 30% balance allocation per trade."""

print("=" * 80)
print("CALCULATE 30% BALANCE ALLOCATION PER TRADE")
print("=" * 80)

balance = 15.07
leverage = 20
desired_margin_per_trade = balance * 0.30  # 30% of balance
position_size = desired_margin_per_trade * leverage

print(f"\n🎯 YOUR GOAL:")
print(f"   Balance: ${balance:.2f}")
print(f"   Margin per trade: 30% = ${desired_margin_per_trade:.2f}")
print(f"   Leverage: {leverage}x")
print(f"   Position size: ${desired_margin_per_trade:.2f} × {leverage} = ${position_size:.2f}")

print(f"\n✅ This gives you ${position_size:.2f} position size per trade")

# Now calculate what config values achieve this
# The bot calculates position size based on risk and stop loss
# Position size = (Balance × Risk%) / Stop Loss%
# We want: Position size = $90
# So: $90 = ($15.07 × Risk%) / Stop Loss%
# Risk% = ($90 × Stop Loss%) / $15.07

# Typical stop loss is 2% (based on ATR)
stop_loss_pct = 0.02
required_risk_pct = (position_size * stop_loss_pct) / balance

print(f"\n📊 REQUIRED CONFIGURATION:")
print(f"   Stop loss: {stop_loss_pct*100}% (based on ATR)")
print(f"   Required risk per trade: {required_risk_pct*100:.1f}%")

# For portfolio mode with 3 positions
# portfolio_max_total_risk should be: risk_per_trade × max_positions
max_positions = 3
portfolio_max_total_risk = required_risk_pct * max_positions

print(f"\n🔧 CONFIG CHANGES NEEDED:")
print(f"   risk_per_trade: {required_risk_pct:.2f} ({required_risk_pct*100:.1f}%)")
print(f"   portfolio_max_total_risk: {portfolio_max_total_risk:.2f} ({portfolio_max_total_risk*100:.1f}%)")
print(f"   max_positions: {max_positions}")

print(f"\n⚠️  RISK WARNING:")
print(f"   With {max_positions} positions at 30% each:")
print(f"   - Total margin used: {max_positions * 30}% = 90% of balance")
print(f"   - Free balance: only 10%")
print(f"   - If all hit stop loss: -{max_positions * required_risk_pct * 100:.0f}% loss")
print(f"   - This is VERY AGGRESSIVE!")

print(f"\n💡 SAFER ALTERNATIVE:")
safer_margin_pct = 0.20  # 20% per trade
safer_position_size = balance * safer_margin_pct * leverage
safer_risk_pct = (safer_position_size * stop_loss_pct) / balance
safer_total_risk = safer_risk_pct * max_positions

print(f"   Margin per trade: 20% = ${balance * safer_margin_pct:.2f}")
print(f"   Position size: ${safer_position_size:.2f}")
print(f"   risk_per_trade: {safer_risk_pct:.2f}")
print(f"   portfolio_max_total_risk: {safer_total_risk:.2f}")
print(f"   Total margin used: 60%")
print(f"   Max loss if all stop: -{safer_total_risk*100:.0f}%")

print("\n" + "=" * 80)
print("📋 RECOMMENDED CONFIG VALUES")
print("=" * 80)

print(f"\n🎯 FOR YOUR GOAL (30% per trade, $90 positions):")
print(f'   "risk_per_trade": {required_risk_pct:.2f},')
print(f'   "portfolio_max_total_risk": {portfolio_max_total_risk:.2f},')
print(f'   "max_positions": {max_positions},')
print(f'   "take_profit_pct": 0.04,  // 4% for better profits')

print(f"\n⚠️  OR SAFER (20% per trade, $60 positions):")
print(f'   "risk_per_trade": {safer_risk_pct:.2f},')
print(f'   "portfolio_max_total_risk": {safer_total_risk:.2f},')
print(f'   "max_positions": {max_positions},')
print(f'   "take_profit_pct": 0.04,')

print("\n" + "=" * 80)
