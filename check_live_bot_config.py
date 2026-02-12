"""Check what config the live bot is actually using."""

import sys
sys.path.append('src')

from config import Config

print("\n" + "="*80)
print("LIVE BOT CONFIGURATION CHECK")
print("="*80 + "\n")

# Load config the same way the bot does
config = Config.load_from_file("config/config.json")

print("Configuration loaded from: config/config.json\n")

print("ADVANCED FEATURES STATUS:")
print(f"  enable_advanced_exits: {config.enable_advanced_exits}")
print(f"  enable_multi_timeframe: {config.enable_multi_timeframe}")
print(f"  enable_volume_profile: {config.enable_volume_profile}")
print(f"  enable_ml_prediction: {config.enable_ml_prediction}")
print(f"  enable_portfolio_management: {config.enable_portfolio_management}")
print(f"  enable_regime_detection: {config.enable_regime_detection}")

if config.enable_advanced_exits:
    print("\n✓ ADVANCED EXITS IS ENABLED")
    print("\nAdvanced Exit Settings:")
    print(f"  Partial Exit 1: {config.exit_partial_1_percentage * 100}% at {config.exit_partial_1_atr_multiplier}x ATR")
    print(f"  Partial Exit 2: {config.exit_partial_2_percentage * 100}% at {config.exit_partial_2_atr_multiplier}x ATR")
    print(f"  Final Exit: at {config.exit_final_atr_multiplier}x ATR")
    print(f"  Breakeven Stop: at {config.exit_breakeven_atr_multiplier}x ATR")
    print(f"  Tight Stop: at {config.exit_tight_stop_atr_multiplier}x ATR")
    print(f"  Max Hold Time: {config.exit_max_hold_time_hours} hours")
    print(f"  Regime Change Exits: {config.exit_regime_change_enabled}")
else:
    print("\n✗ ADVANCED EXITS IS DISABLED")

print("\nRISK SETTINGS:")
print(f"  Risk Per Trade: {config.risk_per_trade * 100}%")
print(f"  Leverage: {config.leverage}x")
print(f"  Stop Loss ATR Multiplier: {config.stop_loss_atr_multiplier}x")
print(f"  Trailing Stop ATR Multiplier: {config.trailing_stop_atr_multiplier}x")

print("\nTRADING SETTINGS:")
print(f"  Symbol: {config.symbol}")
print(f"  Run Mode: {config.run_mode}")
print(f"  ADX Threshold: {config.adx_threshold}")
print(f"  RVOL Threshold: {config.rvol_threshold}")

print("\n" + "="*80 + "\n")
