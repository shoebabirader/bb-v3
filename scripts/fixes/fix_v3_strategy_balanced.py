"""Fix V3 strategy - adjust to balanced settings that will actually trade."""

import json

def main():
    """Adjust V3 strategy to balanced settings."""
    
    print("\n" + "="*80)
    print("FIXING V3 STRATEGY - BALANCED APPROACH")
    print("="*80)
    
    # Load current config
    with open('config/config.json', 'r') as f:
        config = json.load(f)
    
    print("\n❌ CURRENT V3 SETTINGS (TOO STRICT):")
    print(f"  ADX Threshold: {config['adx_threshold']}")
    print(f"  RVOL Threshold: {config['rvol_threshold']}")
    print(f"  Min Timeframe Alignment: {config['min_timeframe_alignment']}/4")
    print("  Result: 0 trades in 90 days")
    
    # Apply balanced settings
    print("\n✅ NEW BALANCED SETTINGS (V3.1):")
    
    config['adx_threshold'] = 25.0  # Down from 30 - still strong but not impossible
    config['rvol_threshold'] = 1.2  # Down from 1.5 - good volume but achievable
    config['min_timeframe_alignment'] = 3  # Down from 4 - 3 out of 4 timeframes
    
    print(f"  ADX Threshold: {config['adx_threshold']} (was 30.0)")
    print(f"  RVOL Threshold: {config['rvol_threshold']} (was 1.5)")
    print(f"  Min Timeframe Alignment: {config['min_timeframe_alignment']}/4 (was 4/4)")
    
    print("\n📊 KEEPING GOOD V3 FEATURES:")
    print(f"  ✅ Wider stops: {config['stop_loss_atr_multiplier']}x ATR")
    print(f"  ✅ Bigger targets: {config['take_profit_pct']*100}%")
    print(f"  ✅ Better exits: 50% at 2x, 30% at 4x, 20% at 6x ATR")
    print(f"  ✅ Quality symbols: {', '.join(config['portfolio_symbols'])}")
    print(f"  ✅ Safe risk: {config['risk_per_trade']*100}% per trade")
    print(f"  ✅ Safe leverage: {config['leverage']}x")
    
    # Save config
    with open('config/config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n💾 Config saved to config/config.json")
    
    print("\n🎯 EXPECTED RESULTS:")
    print("  - 10-20 trades in 90 days (good frequency)")
    print("  - Win rate: 50-60% (quality signals)")
    print("  - Profit factor: 1.5-2.5 (profitable)")
    print("  - Better than V2 (which had 47% win rate)")
    
    print("\n🔄 NEXT STEPS:")
    print("  1. Run backtest: python run_portfolio_backtest.py")
    print("  2. Verify results are profitable")
    print("  3. If still no trades, try Option 2 (ADX 22, RVOL 1.0)")
    print("  4. If profitable, deploy to EC2")
    
    print("\n📝 VERSION HISTORY:")
    print("  V1: ADX 25, RVOL 1.2 - Too strict (13 trades)")
    print("  V2: ADX 22, RVOL 1.0 - Too loose (47% win rate)")
    print("  V3: ADX 30, RVOL 1.5, 4/4 TF - TOO STRICT (0 trades)")
    print("  V3.1: ADX 25, RVOL 1.2, 3/4 TF - BALANCED ⭐")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
