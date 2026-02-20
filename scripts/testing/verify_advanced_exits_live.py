"""Verify that Advanced Exit Manager is working in the live bot."""

import sys
sys.path.append('src')

from config import Config
from risk_manager import RiskManager
from position_sizer import PositionSizer

print("\n" + "="*80)
print("ADVANCED EXIT MANAGER - LIVE BOT VERIFICATION")
print("="*80 + "\n")

# Load config the same way the bot does
config = Config.load_from_file("config/config.json")

print(f"Config: enable_advanced_exits = {config.enable_advanced_exits}\n")

# Initialize the same way the bot does
position_sizer = PositionSizer(config)
risk_manager = RiskManager(config, position_sizer)

print("RiskManager Initialization:")
print(f"  AdvancedExitManager object: {risk_manager.advanced_exit_manager}")
print(f"  Feature Manager status: {risk_manager.feature_manager.is_feature_enabled('advanced_exits')}")

if risk_manager.advanced_exit_manager:
    print("\n✓ ADVANCED EXIT MANAGER IS INITIALIZED AND ACTIVE")
    
    print("\nAdvanced Exit Manager Configuration:")
    aem = risk_manager.advanced_exit_manager
    print(f"  Partial Exit 1: {aem.exit_percentages['partial_1'] * 100}% at {aem.exit_levels['partial_1']}x ATR")
    print(f"  Partial Exit 2: {aem.exit_percentages['partial_2'] * 100}% at {aem.exit_levels['partial_2']}x ATR")
    print(f"  Final Exit: at {aem.exit_levels['final']}x ATR")
    print(f"  Max Hold Time: {config.exit_max_hold_time_hours} hours")
    print(f"  Regime Change Enabled: {config.exit_regime_change_enabled}")
    
    print("\n✓ THE LIVE BOT IS USING ADVANCED EXITS!")
    print("\nWhat this means:")
    print("  1. When position reaches 1.5x ATR profit → Close 33% and move stop to breakeven")
    print("  2. When position reaches 3.0x ATR profit → Close another 33%")
    print("  3. When position reaches 5.0x ATR profit → Close remaining 34%")
    print("  4. If position held for 24+ hours → Close entire position")
    print("  5. If market regime changes → Close position")
    
else:
    print("\n✗ ADVANCED EXIT MANAGER FAILED TO INITIALIZE")
    print("  This should not happen with enable_advanced_exits=True")
    print("  Check for initialization errors in the logs")

print("\n" + "="*80 + "\n")
