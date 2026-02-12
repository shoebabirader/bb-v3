"""Fix LIVE trading mode and trailing stop loss issues."""

import json
import sys

print("\n" + "="*80)
print("FIXING LIVE TRADING AND TRAILING STOP ISSUES")
print("="*80 + "\n")

# Issue 1: Verify config is set to LIVE
print("ISSUE 1: Bot Running in PAPER Mode")
print("-" * 80)

with open('config/config.json', 'r') as f:
    config = json.load(f)

current_mode = config.get('run_mode', 'UNKNOWN')
print(f"Current config run_mode: {current_mode}")

if current_mode == "PAPER":
    print("[X] Config is still set to PAPER mode")
    print("[ACTION] Changing to LIVE mode...")
    config['run_mode'] = "LIVE"
    
    with open('config/config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("[OK] Config updated to LIVE mode")
elif current_mode == "LIVE":
    print("[OK] Config is already set to LIVE mode")
    print("[INFO] You MUST restart the bot for changes to take effect!")
else:
    print(f"[WARNING] Unknown run_mode: {current_mode}")

# Issue 2: Check trailing stop configuration
print("\n" + "="*80)
print("ISSUE 2: Trailing Stop Loss Configuration")
print("-" * 80)

trailing_stop_multiplier = config.get('trailing_stop_atr_multiplier', 0)
stop_loss_multiplier = config.get('stop_loss_atr_multiplier', 0)
enable_advanced_exits = config.get('enable_advanced_exits', False)

print(f"Stop Loss ATR Multiplier: {stop_loss_multiplier}")
print(f"Trailing Stop ATR Multiplier: {trailing_stop_multiplier}")
print(f"Advanced Exits Enabled: {enable_advanced_exits}")

if trailing_stop_multiplier < stop_loss_multiplier:
    print("\n[WARNING] Trailing stop is TIGHTER than initial stop loss!")
    print(f"  Initial stop: {stop_loss_multiplier} ATR")
    print(f"  Trailing stop: {trailing_stop_multiplier} ATR")
    print("\n[PROBLEM] This means:")
    print("  - Position enters with 2.0 ATR stop loss")
    print("  - Trailing stop immediately activates at 1.5 ATR")
    print("  - This is TIGHTER than entry stop, so you get stopped out faster")
    print("  - You can't capture profits because stop is too tight")
    print("\n[RECOMMENDATION] Trailing stop should be WIDER or equal to initial stop")
    print("  Option 1: Set trailing_stop_atr_multiplier = 2.0 (same as stop loss)")
    print("  Option 2: Set trailing_stop_atr_multiplier = 2.5 (wider)")
    print("  Option 3: Set trailing_stop_atr_multiplier = 3.0 (much wider)")
else:
    print("\n[OK] Trailing stop configuration looks reasonable")

# Issue 3: Check if advanced exits might be interfering
if enable_advanced_exits:
    print("\n[INFO] Advanced Exits are ENABLED")
    print("  This includes:")
    print(f"  - Partial exit 1: {config.get('exit_partial_1_atr_multiplier', 0)} ATR ({config.get('exit_partial_1_percentage', 0)*100}%)")
    print(f"  - Partial exit 2: {config.get('exit_partial_2_atr_multiplier', 0)} ATR ({config.get('exit_partial_2_percentage', 0)*100}%)")
    print(f"  - Final exit: {config.get('exit_final_atr_multiplier', 0)} ATR")
    print(f"  - Breakeven: {config.get('exit_breakeven_atr_multiplier', 0)} ATR")
    print(f"  - Tight stop: {config.get('exit_tight_stop_atr_multiplier', 0)} ATR")
    print("\n[WARNING] Advanced exits might be closing positions early")
    print("  Consider disabling: set 'enable_advanced_exits': false")

print("\n" + "="*80)
print("SUMMARY AND NEXT STEPS")
print("="*80 + "\n")

print("1. CONFIG UPDATED:")
print(f"   run_mode: {config['run_mode']}")
print()

print("2. YOU MUST RESTART THE BOT:")
print("   - Stop the current bot (Ctrl+C if running)")
print("   - Start fresh: python main.py")
print("   - Look for: 'LIVE TRADING MODE ACTIVATED'")
print("   - Look for: '[WARNING] REAL MONEY AT RISK [WARNING]'")
print()

print("3. TRAILING STOP ISSUE:")
if trailing_stop_multiplier < stop_loss_multiplier:
    print("   [X] Trailing stop is TOO TIGHT")
    print("   [ACTION] Consider increasing trailing_stop_atr_multiplier")
    print(f"   Current: {trailing_stop_multiplier} → Recommended: {stop_loss_multiplier} or higher")
else:
    print("   [OK] Trailing stop configuration looks good")
print()

print("4. VERIFY LIVE MODE:")
print("   After restarting, check logs/bot.log:")
print("   - Should say: 'TradingBot initialized in LIVE mode'")
print("   - Should NOT say: 'TradingBot initialized in PAPER mode'")
print()

print("5. MONITOR FIRST TRADE:")
print("   - Watch console output carefully")
print("   - Check Binance Futures for real orders")
print("   - Verify balance changes")
print()

print("="*80)
print()

# Offer to fix trailing stop
print("Would you like to fix the trailing stop configuration?")
print("This will set trailing_stop_atr_multiplier = 2.0 (same as stop loss)")
print()
response = input("Fix trailing stop? (y/n): ").strip().lower()

if response == 'y':
    config['trailing_stop_atr_multiplier'] = 2.0
    with open('config/config.json', 'w') as f:
        json.dump(config, f, indent=2)
    print("\n[OK] Trailing stop updated to 2.0 ATR")
    print("[INFO] Restart the bot for changes to take effect")
else:
    print("\n[INFO] Trailing stop not changed")

print("\n" + "="*80)
print("RESTART THE BOT NOW: python main.py")
print("="*80 + "\n")
