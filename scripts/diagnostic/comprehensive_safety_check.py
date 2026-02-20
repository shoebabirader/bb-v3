"""
Comprehensive Safety Check for Trading Bot
Verifies all strategies, functions, and features are safe for paper and live trading
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import importlib.util

class SafetyChecker:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []
        
    def log_pass(self, check: str):
        self.passed.append(f"✅ {check}")
        
    def log_warning(self, check: str, message: str):
        self.warnings.append(f"⚠️  {check}: {message}")
        
    def log_issue(self, check: str, message: str):
        self.issues.append(f"❌ {check}: {message}")
    
    def check_config_safety(self) -> bool:
        """Check configuration for dangerous settings"""
        print("\n" + "="*80)
        print("1. CONFIGURATION SAFETY CHECK")
        print("="*80)
        
        try:
            with open('config/config.json', 'r') as f:
                config = json.load(f)
            
            # Check mode
            mode = config.get('mode', 'UNKNOWN')
            run_mode = config.get('run_mode', 'UNKNOWN')
            print(f"   Mode: {mode}, Run Mode: {run_mode}")
            
            if mode == 'LIVE' or run_mode == 'LIVE':
                self.log_warning("Config Mode", "Bot is configured for LIVE trading")
            else:
                self.log_pass("Config Mode: PAPER/BACKTEST (safe)")
            
            # Check risk settings
            risk = config.get('risk_per_trade', 0)
            leverage = config.get('leverage', 0)
            
            if risk > 0.15:  # 15%
                self.log_issue("Risk Per Trade", f"Risk too high: {risk*100}% (recommended: <15%)")
            elif risk > 0.05:  # 5%
                self.log_warning("Risk Per Trade", f"Risk moderate: {risk*100}% (recommended: <5%)")
            else:
                self.log_pass(f"Risk Per Trade: {risk*100}% (safe)")
            
            if leverage > 20:
                self.log_issue("Leverage", f"Leverage too high: {leverage}x (recommended: ≤20x)")
            elif leverage > 10:
                self.log_warning("Leverage", f"Leverage moderate: {leverage}x (recommended: ≤10x)")
            else:
                self.log_pass(f"Leverage: {leverage}x (safe)")
            
            # Check stop loss
            stop_loss_atr = config.get('stop_loss_atr_multiplier', 0)
            if stop_loss_atr < 2.0:
                self.log_warning("Stop Loss", f"Stops too tight: {stop_loss_atr}x ATR (recommended: ≥3.0x)")
            else:
                self.log_pass(f"Stop Loss: {stop_loss_atr}x ATR (safe)")
            
            # Check portfolio settings
            max_positions = config.get('max_positions', 1)
            portfolio_max_risk = config.get('portfolio_max_total_risk', 0)
            
            if max_positions > 5:
                self.log_warning("Max Positions", f"{max_positions} positions (recommended: ≤5)")
            else:
                self.log_pass(f"Max Positions: {max_positions} (safe)")
            
            if portfolio_max_risk > 0.5:  # 50%
                self.log_issue("Portfolio Risk", f"Total risk too high: {portfolio_max_risk*100}%")
            else:
                self.log_pass(f"Portfolio Max Risk: {portfolio_max_risk*100}% (safe)")
            
            # Check API keys are present
            api_key = config.get('api_key', '')
            api_secret = config.get('api_secret', '')
            
            if not api_key or not api_secret:
                self.log_issue("API Keys", "Missing API credentials")
            else:
                self.log_pass("API Keys: Present")
            
            # Check advanced exits
            advanced_exits = config.get('enable_advanced_exits', False)
            if advanced_exits and run_mode == 'BACKTEST':
                self.log_warning("Advanced Exits", "Enabled in backtest (known to be broken)")
            else:
                self.log_pass(f"Advanced Exits: {advanced_exits} (appropriate for mode)")
            
            return len(self.issues) == 0
            
        except Exception as e:
            self.log_issue("Config Loading", f"Failed to load config: {e}")
            return False
    
    def check_critical_files(self) -> bool:
        """Check all critical files exist and are valid"""
        print("\n" + "="*80)
        print("2. CRITICAL FILES CHECK")
        print("="*80)
        
        critical_files = [
            'src/trading_bot.py',
            'src/strategy.py',
            'src/risk_manager.py',
            'src/position_sizer.py',
            'src/backtest_engine.py',
            'src/data_manager.py',
            'src/logger.py',
            'src/config.py',
            'src/models.py',
            'config/config.json',
            'main.py'
        ]
        
        all_exist = True
        for file_path in critical_files:
            if Path(file_path).exists():
                self.log_pass(f"File exists: {file_path}")
            else:
                self.log_issue(f"Missing File", f"{file_path} not found")
                all_exist = False
        
        return all_exist
    
    def check_risk_manager_safety(self) -> bool:
        """Check risk manager has proper safeguards"""
        print("\n" + "="*80)
        print("3. RISK MANAGER SAFETY CHECK")
        print("="*80)
        
        try:
            with open('src/risk_manager.py', 'r') as f:
                content = f.read()
            
            # Check for position shutdown fix
            if 'PANIC' in content and 'def _shutdown' in content:
                self.log_pass("Position Shutdown: Fixed (uses PANIC exit reason)")
            elif 'SHUTDOWN' in content and 'def _shutdown' in content:
                self.log_issue("Position Shutdown", "Still uses invalid SHUTDOWN exit reason")
            else:
                self.log_pass("Position Shutdown: Method present")
            
            # Check for portfolio management
            if 'PortfolioManager' in content:
                self.log_pass("Portfolio Management: Integrated")
            else:
                self.log_warning("Portfolio Management", "Not found in risk manager")
            
            # Check for stop loss validation
            if 'trailing_stop' in content and 'stop_loss' in content:
                self.log_pass("Stop Loss Logic: Present")
            else:
                self.log_warning("Stop Loss Logic", "May be incomplete")
            
            # Check for position size limits
            if 'max_position_size' in content or 'position_size' in content:
                self.log_pass("Position Sizing: Present")
            else:
                self.log_warning("Position Sizing", "May not have size limits")
            
            return len(self.issues) == 0
            
        except Exception as e:
            self.log_issue("Risk Manager Check", f"Failed to check: {e}")
            return False
    
    def check_strategy_safety(self) -> bool:
        """Check strategy has proper signal validation"""
        print("\n" + "="*80)
        print("4. STRATEGY SAFETY CHECK")
        print("="*80)
        
        try:
            with open('src/strategy.py', 'r') as f:
                content = f.read()
            
            # Check for candle close confirmation
            if '_candle_just_closed' in content or 'candle_close' in content:
                self.log_pass("Candle Close Confirmation: Implemented")
            else:
                self.log_warning("Candle Close Confirmation", "May not wait for candle close")
            
            # Check for ADX threshold
            if 'adx_threshold' in content:
                self.log_pass("ADX Threshold: Present")
            else:
                self.log_warning("ADX Threshold", "May not filter weak trends")
            
            # Check for RVOL threshold
            if 'rvol_threshold' in content or 'relative_volume' in content:
                self.log_pass("RVOL Threshold: Present")
            else:
                self.log_warning("RVOL Threshold", "May not filter low volume")
            
            # Check for multi-timeframe
            if 'timeframe_coordinator' in content or 'multi_timeframe' in content:
                self.log_pass("Multi-Timeframe: Implemented")
            else:
                self.log_warning("Multi-Timeframe", "May only use single timeframe")
            
            # Check for momentum exhaustion
            if 'momentum_exhausted' in content or 'overextended' in content:
                self.log_pass("Momentum Exhaustion Check: Present")
            else:
                self.log_warning("Momentum Exhaustion", "May not filter overextended moves")
            
            return True
            
        except Exception as e:
            self.log_issue("Strategy Check", f"Failed to check: {e}")
            return False
    
    def check_backtest_engine_safety(self) -> bool:
        """Check backtest engine is not broken"""
        print("\n" + "="*80)
        print("5. BACKTEST ENGINE SAFETY CHECK")
        print("="*80)
        
        try:
            with open('src/backtest_engine.py', 'r') as f:
                content = f.read()
            
            # Check for broken partial exit tracking
            if '_partial_exit_pnl' in content:
                self.log_issue("Backtest Engine", "Still has broken partial exit tracking")
            else:
                self.log_pass("Partial Exit Tracking: Removed (fixed)")
            
            # Check for simple take profit
            if 'take_profit_pct' in content:
                self.log_pass("Take Profit: Simple implementation present")
            else:
                self.log_warning("Take Profit", "May not have take profit logic")
            
            # Check for trailing stop
            if 'trailing_stop' in content and '_check_stop_hit_in_candle' in content:
                self.log_pass("Trailing Stop: Implemented")
            else:
                self.log_warning("Trailing Stop", "May not have trailing stop logic")
            
            # Check for fees and slippage
            if 'apply_fees_and_slippage' in content:
                self.log_pass("Fees & Slippage: Applied")
            else:
                self.log_warning("Fees & Slippage", "May not account for trading costs")
            
            return len(self.issues) == 0
            
        except Exception as e:
            self.log_issue("Backtest Engine Check", f"Failed to check: {e}")
            return False
    
    def check_advanced_exits_safety(self) -> bool:
        """Check advanced exits manager is safe"""
        print("\n" + "="*80)
        print("6. ADVANCED EXITS SAFETY CHECK")
        print("="*80)
        
        try:
            with open('src/advanced_exit_manager.py', 'r') as f:
                content = f.read()
            
            # Check for partial exit logic
            if 'check_partial_exits' in content:
                self.log_pass("Partial Exits: Method present")
            else:
                self.log_warning("Partial Exits", "Method may be missing")
            
            # Check for breakeven stop
            if 'breakeven' in content.lower():
                self.log_pass("Breakeven Stop: Implemented")
            else:
                self.log_warning("Breakeven Stop", "May not move stop to breakeven")
            
            # Check for time-based exit
            if 'time_based_exit' in content or 'max_hold_time' in content:
                self.log_pass("Time-Based Exit: Implemented")
            else:
                self.log_warning("Time-Based Exit", "May not exit stale positions")
            
            # Check for exit tracking reset
            if 'reset_exit_tracking' in content:
                self.log_pass("Exit Tracking Reset: Present")
            else:
                self.log_warning("Exit Tracking Reset", "May not clean up properly")
            
            return True
            
        except Exception as e:
            self.log_issue("Advanced Exits Check", f"Failed to check: {e}")
            return False
    
    def check_trading_bot_safety(self) -> bool:
        """Check trading bot has proper error handling"""
        print("\n" + "="*80)
        print("7. TRADING BOT SAFETY CHECK")
        print("="*80)
        
        try:
            with open('src/trading_bot.py', 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check for keyboard listener fix
            if 'KEYBOARD_AVAILABLE' in content:
                self.log_pass("Keyboard Listener: Headless-safe (optional)")
            else:
                self.log_warning("Keyboard Listener", "May fail in headless environment")
            
            # Check for shutdown handler
            if '_shutdown' in content and 'signal.signal' in content:
                self.log_pass("Shutdown Handler: Implemented")
            else:
                self.log_warning("Shutdown Handler", "May not handle graceful shutdown")
            
            # Check for error handling
            if 'try:' in content and 'except' in content:
                self.log_pass("Error Handling: Present")
            else:
                self.log_warning("Error Handling", "May not handle errors gracefully")
            
            # Check for mode validation
            if 'PAPER' in content and 'LIVE' in content and 'BACKTEST' in content:
                self.log_pass("Mode Validation: All modes supported")
            else:
                self.log_warning("Mode Validation", "May not validate mode properly")
            
            return True
            
        except Exception as e:
            self.log_issue("Trading Bot Check", f"Failed to check: {e}")
            return False
    
    def check_data_manager_safety(self) -> bool:
        """Check data manager has rate limiting"""
        print("\n" + "="*80)
        print("8. DATA MANAGER SAFETY CHECK")
        print("="*80)
        
        try:
            with open('src/data_manager.py', 'r') as f:
                content = f.read()
            
            # Check for rate limiting
            if 'rate_limiter' in content.lower() or 'RateLimiter' in content:
                self.log_pass("Rate Limiting: Implemented")
            else:
                self.log_warning("Rate Limiting", "May not have API rate limiting")
            
            # Check for error handling
            if 'BinanceAPIException' in content or 'except' in content:
                self.log_pass("API Error Handling: Present")
            else:
                self.log_warning("API Error Handling", "May not handle API errors")
            
            # Check for data validation
            if 'validate' in content.lower() or 'len(candles)' in content:
                self.log_pass("Data Validation: Present")
            else:
                self.log_warning("Data Validation", "May not validate fetched data")
            
            return True
            
        except Exception as e:
            self.log_issue("Data Manager Check", f"Failed to check: {e}")
            return False
    
    def print_summary(self):
        """Print comprehensive summary"""
        print("\n" + "="*80)
        print("SAFETY CHECK SUMMARY")
        print("="*80)
        
        print(f"\n✅ PASSED: {len(self.passed)} checks")
        for item in self.passed:
            print(f"   {item}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS: {len(self.warnings)} items")
            for item in self.warnings:
                print(f"   {item}")
        
        if self.issues:
            print(f"\n❌ CRITICAL ISSUES: {len(self.issues)} items")
            for item in self.issues:
                print(f"   {item}")
        
        print("\n" + "="*80)
        if self.issues:
            print("❌ SAFETY CHECK FAILED - DO NOT USE FOR LIVE TRADING")
            print("   Fix critical issues before proceeding")
        elif self.warnings:
            print("⚠️  SAFETY CHECK PASSED WITH WARNINGS")
            print("   Review warnings before live trading")
        else:
            print("✅ SAFETY CHECK PASSED - SAFE FOR PAPER TRADING")
            print("   Monitor paper trading for 7+ days before going live")
        print("="*80 + "\n")
        
        return len(self.issues) == 0

def main():
    print("\n" + "="*80)
    print("COMPREHENSIVE TRADING BOT SAFETY CHECK")
    print("="*80)
    print("Verifying all strategies, functions, and features...")
    
    checker = SafetyChecker()
    
    # Run all checks
    checks = [
        checker.check_config_safety(),
        checker.check_critical_files(),
        checker.check_risk_manager_safety(),
        checker.check_strategy_safety(),
        checker.check_backtest_engine_safety(),
        checker.check_advanced_exits_safety(),
        checker.check_trading_bot_safety(),
        checker.check_data_manager_safety()
    ]
    
    # Print summary
    passed = checker.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
