"""Run backtest for all portfolio symbols."""

import json
import time
from src.config import Config
from src.trading_bot import TradingBot

print("=" * 80)
print("PORTFOLIO BACKTEST - ALL 5 SYMBOLS")
print("=" * 80)

# Load config
config = Config.load_from_file('config/config.json')

# Override run_mode to BACKTEST
config.run_mode = "BACKTEST"

# Get portfolio symbols
symbols = config.portfolio_symbols
print(f"\nBacktesting {len(symbols)} symbols: {', '.join(symbols)}")
print(f"Backtest period: {config.backtest_days} days")
print(f"Risk per trade: {config.risk_per_trade * 100}%")
print(f"Leverage: {config.leverage}x")
print(f"Portfolio max risk: {config.portfolio_max_total_risk * 100}%")
print("\n" + "=" * 80)

# Store results for all symbols
all_results = {}

# Run backtest for each symbol
for idx, symbol in enumerate(symbols, 1):
    print(f"\n[{idx}/{len(symbols)}] BACKTESTING {symbol}")
    print("-" * 80)
    
    try:
        # Update config with current symbol
        config.symbol = symbol
        
        # Create bot and run backtest
        bot = TradingBot(config)
        bot.start()
        
        # Get results from log file
        with open(config.log_file, 'r') as f:
            results = json.load(f)
            all_results[symbol] = results
        
        print(f"✓ {symbol} backtest complete")
        
        # Add delay between symbols to avoid rate limiting
        if idx < len(symbols):
            delay = 2  # 2 second delay
            print(f"\nWaiting {delay}s before next symbol...")
            time.sleep(delay)
    
    except Exception as e:
        print(f"✗ Error backtesting {symbol}: {e}")
        all_results[symbol] = {"error": str(e)}

# Display summary for all symbols
print("\n" + "=" * 80)
print("PORTFOLIO BACKTEST SUMMARY")
print("=" * 80)

print(f"\n{'Symbol':<12} {'Trades':<8} {'Win Rate':<10} {'ROI':<10} {'Sharpe':<8}")
print("-" * 60)

total_trades = 0
total_roi = 0.0
successful_symbols = 0

for symbol, results in all_results.items():
    if "error" in results:
        print(f"{symbol:<12} ERROR: {results['error']}")
    else:
        trades = results.get('total_trades', 0)
        win_rate = results.get('win_rate', 0.0) * 100
        roi = results.get('roi', 0.0) * 100
        sharpe = results.get('sharpe_ratio', 0.0)
        
        print(f"{symbol:<12} {trades:<8} {win_rate:<9.2f}% {roi:<9.2f}% {sharpe:<8.2f}")
        
        total_trades += trades
        total_roi += roi
        successful_symbols += 1

print("-" * 60)

if successful_symbols > 0:
    avg_roi = total_roi / successful_symbols
    print(f"\nTotal Trades: {total_trades}")
    print(f"Average ROI: {avg_roi:.2f}%")
    print(f"Successful Symbols: {successful_symbols}/{len(symbols)}")
else:
    print("\nNo successful backtests")

print("\n" + "=" * 80)
print("IMPORTANT NOTES")
print("=" * 80)
print("""
1. Each symbol was backtested INDEPENDENTLY
2. Portfolio management was NOT simulated (no correlation checks)
3. In live trading, portfolio manager will:
   - Limit total risk across all symbols
   - Reduce exposure for correlated symbols
   - Allocate capital based on signal confidence
   
4. Your current settings:
   - Risk per trade: 20%
   - Portfolio max risk: 100%
   - Max 5 symbols simultaneously
   - Potential max exposure: 1000% (20% × 10x leverage × 5 symbols)

5. To run TRUE portfolio backtest (all symbols together):
   - Would need to implement multi-symbol backtest engine
   - Would simulate correlation checks and capital allocation
   - Would track portfolio-level metrics
""")

print("=" * 80)

# Save combined results
combined_file = "portfolio_backtest_results.json"
with open(combined_file, 'w') as f:
    json.dump(all_results, f, indent=2)

print(f"\n✓ Combined results saved to {combined_file}")
print("=" * 80)
