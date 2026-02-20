"""Diagnose why bot isn't executing trades despite having signals."""

from src.config import Config

config = Config.load_from_file()

print("=" * 80)
print("WHY BOT ISN'T EXECUTING TRADES")
print("=" * 80)
print()

print("ISSUE #1: SYMBOL MISMATCH")
print("-" * 80)
print(f"Bot is monitoring: {config.symbol}")
print(f"Signal is on: XRPUSDT")
print()
if config.symbol != "XRPUSDT":
    print("❌ PROBLEM: Bot is watching SNXUSDT, but signal is on XRPUSDT!")
    print("   The bot will NEVER see this signal because it's not monitoring XRPUSDT")
else:
    print("✓ Symbol matches")
print()

print("ISSUE #2: PORTFOLIO MANAGEMENT")
print("-" * 80)
print(f"Portfolio Management Enabled: {config.enable_portfolio_management}")
print(f"Portfolio Symbols: {config.portfolio_symbols}")
print()
if config.enable_portfolio_management:
    print("⚠️  PORTFOLIO MODE ACTIVE")
    print("   Bot is in portfolio mode, which means:")
    print("   1. It monitors ALL portfolio symbols")
    print("   2. It may have additional filters (correlation, allocation limits)")
    print("   3. It may be waiting to allocate across multiple symbols")
    print()
    if "XRPUSDT" in config.portfolio_symbols:
        print("   ✓ XRPUSDT is in portfolio_symbols list")
        print("   ✓ Bot SHOULD be monitoring XRPUSDT")
        print()
        print("   But portfolio manager may be blocking the trade due to:")
        print("   - Correlation with other positions")
        print("   - Max allocation limits")
        print("   - Risk management rules")
    else:
        print("   ❌ XRPUSDT is NOT in portfolio_symbols list!")
        print("   Bot will NOT monitor XRPUSDT even in portfolio mode")
else:
    print("✓ Portfolio mode disabled - bot monitors single symbol only")
print()

print("ISSUE #3: RUN MODE")
print("-" * 80)
print(f"Run Mode: {config.run_mode}")
print()
if config.run_mode == "PAPER":
    print("⚠️  PAPER TRADING MODE")
    print("   Bot is in paper trading mode (simulated trades)")
    print("   Trades will be logged but NOT executed on exchange")
elif config.run_mode == "LIVE":
    print("✓ LIVE TRADING MODE")
    print("   Bot will execute real trades")
else:
    print(f"❓ Unknown mode: {config.run_mode}")
print()

print("ISSUE #4: ADVANCED FEATURES")
print("-" * 80)
print(f"Multi-timeframe: {config.enable_multi_timeframe}")
print(f"Volume Profile: {config.enable_volume_profile}")
print(f"Regime Detection: {config.enable_regime_detection}")
print(f"Advanced Exits: {config.enable_advanced_exits}")
print()
print("⚠️  MULTIPLE ADVANCED FEATURES ENABLED")
print("   These features add additional filters that may block trades:")
print()
if config.enable_multi_timeframe:
    print(f"   - Multi-timeframe: Requires {config.min_timeframe_alignment} out of 4 timeframes aligned")
    print("     May be blocking if 5m or 4h data not available")
print()
if config.enable_regime_detection:
    print("   - Regime Detection: May block trades in UNCERTAIN regime")
    print("     May require regime stability before trading")
print()
if config.enable_volume_profile:
    print("   - Volume Profile: May reduce position size in low-volume areas")
print()

print("=" * 80)
print("ROOT CAUSE ANALYSIS")
print("=" * 80)
print()

# Determine the most likely issue
if config.symbol != "XRPUSDT" and not config.enable_portfolio_management:
    print("🔴 PRIMARY ISSUE: SYMBOL MISMATCH")
    print()
    print("   Bot is configured to trade SNXUSDT only")
    print("   Signal is on XRPUSDT")
    print("   Bot will NEVER execute this trade")
    print()
    print("   SOLUTION: Change symbol to XRPUSDT or enable portfolio management")
    
elif config.enable_portfolio_management and "XRPUSDT" in config.portfolio_symbols:
    print("🟡 LIKELY ISSUE: PORTFOLIO MANAGER BLOCKING")
    print()
    print("   Bot IS monitoring XRPUSDT (it's in portfolio)")
    print("   But portfolio manager may be blocking due to:")
    print("   - Risk allocation limits")
    print("   - Correlation checks")
    print("   - Waiting for better opportunities across portfolio")
    print()
    print("   SOLUTION: Check portfolio manager logs or disable portfolio mode")
    
elif config.enable_portfolio_management and "XRPUSDT" not in config.portfolio_symbols:
    print("🔴 PRIMARY ISSUE: XRPUSDT NOT IN PORTFOLIO")
    print()
    print("   Portfolio mode is enabled")
    print("   But XRPUSDT is not in the portfolio_symbols list")
    print("   Bot will NOT monitor XRPUSDT")
    print()
    print("   SOLUTION: Add XRPUSDT to portfolio_symbols or change main symbol")

print()
print("=" * 80)
print("RECOMMENDED FIXES")
print("=" * 80)
print()

print("OPTION 1: Trade XRPUSDT Only (Simplest)")
print("-" * 80)
print("Change config.json:")
print('{')
print('  "symbol": "XRPUSDT",')
print('  "enable_portfolio_management": false,')
print('  "enable_multi_timeframe": false,')
print('  "enable_regime_detection": false')
print('}')
print()
print("Then restart: python restart_bot.py")
print()

print("OPTION 2: Keep Portfolio Mode")
print("-" * 80)
print("Verify XRPUSDT is in portfolio_symbols (it is)")
print("Check bot logs to see why portfolio manager is blocking")
print("May need to adjust:")
print('  - "portfolio_max_single_allocation": 0.35')
print('  - "portfolio_correlation_threshold": 0.7')
print()

print("OPTION 3: Disable Advanced Features Temporarily")
print("-" * 80)
print("Keep current symbol but disable blockers:")
print('{')
print('  "enable_multi_timeframe": false,')
print('  "enable_regime_detection": false,')
print('  "enable_volume_profile": false')
print('}')
print()

print("=" * 80)
print("NEXT STEPS")
print("=" * 80)
print()
print("1. Decide which option you prefer")
print("2. Update config/config.json")
print("3. Restart bot: python restart_bot.py")
print("4. Monitor logs to confirm trades execute")
print()
print("For OPTION 1 (recommended for testing):")
print("  - Simplest solution")
print("  - Bot will focus on XRPUSDT only")
print("  - Fewer filters = more likely to trade")
