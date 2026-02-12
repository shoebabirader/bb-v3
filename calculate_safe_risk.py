"""Calculate safe risk percentage for current balance."""

balance = 14.15
leverage = 5
price = 81.42
atr_multiplier = 2.0

# We want margin_required <= balance
# margin_required = (price * quantity) / leverage
# quantity = (risk_amount / stop_distance) * leverage
# stop_distance = (price * 0.02) * atr_multiplier
# risk_amount = balance * risk_per_trade

# Solving for risk_per_trade:
# margin_required = (price * ((balance * risk_per_trade) / stop_distance) * leverage) / leverage
# margin_required = price * (balance * risk_per_trade) / stop_distance
# margin_required = price * balance * risk_per_trade / (price * 0.02 * atr_multiplier)
# margin_required = balance * risk_per_trade / (0.02 * atr_multiplier)
# margin_required = balance * risk_per_trade / 0.04

# For margin_required = balance:
# balance = balance * risk_per_trade / 0.04
# 1 = risk_per_trade / 0.04
# risk_per_trade = 0.04 (4%)

# But we want margin_required < balance (leave some buffer)
# Let's use 80% of balance as max margin
max_margin = balance * 0.8
stop_distance = (price * 0.02) * atr_multiplier

# max_margin = price * quantity / leverage
# quantity = (risk_amount / stop_distance) * leverage
# max_margin = price * ((risk_amount / stop_distance) * leverage) / leverage
# max_margin = price * risk_amount / stop_distance
# risk_amount = max_margin * stop_distance / price

risk_amount = max_margin * stop_distance / price
risk_per_trade = risk_amount / balance

print("=" * 80)
print("SAFE RISK CALCULATION")
print("=" * 80)
print()
print(f"Current Balance: ${balance:.2f}")
print(f"XAGUSDT Price: ${price:.2f}")
print(f"Leverage: {leverage}x")
print(f"ATR Multiplier: {atr_multiplier}")
print()
print(f"Max Safe Margin (80% of balance): ${max_margin:.2f}")
print(f"Stop Distance: ${stop_distance:.4f}")
print()
print(f"Safe Risk Amount: ${risk_amount:.2f}")
print(f"Safe Risk Per Trade: {risk_per_trade * 100:.2f}%")
print()
print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print()
print(f"Set risk_per_trade to: {risk_per_trade:.4f} ({risk_per_trade * 100:.2f}%)")
print()
print("This will allow the bot to execute trades with your current balance.")
print()
print("⚠️  WARNING: $14.15 is VERY LOW for futures trading!")
print("   Recommended minimum: $50-100")
print("   Consider adding more funds for safer trading.")
print()
