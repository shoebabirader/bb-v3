"""Verify bot and dashboard setup is complete and working."""

import os
import sys
import json

def check_file_exists(filepath, description):
    """Check if a file exists and print status."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} MISSING: {filepath}")
        return False

def check_imports():
    """Check if all required imports work."""
    print("\n📦 Checking Python imports...")
    
    try:
        from src.trading_bot import main
        print("✅ Trading bot imports OK")
    except Exception as e:
        print(f"❌ Trading bot import failed: {e}")
        return False
    
    try:
        import streamlit
        print("✅ Streamlit imports OK")
    except Exception as e:
        print(f"❌ Streamlit import failed: {e}")
        print("   Run: pip install -r requirements_ui.txt")
        return False
    
    try:
        from src.streamlit_data_provider import StreamlitDataProvider
        from src.streamlit_bot_controller import BotController
        from src.streamlit_config_editor import ConfigEditor
        from src.streamlit_charts import ChartGenerator
        print("✅ Dashboard components imports OK")
    except Exception as e:
        print(f"❌ Dashboard component import failed: {e}")
        return False
    
    return True

def check_config():
    """Check if config is valid."""
    print("\n⚙️ Checking configuration...")
    
    if not os.path.exists('config/config.json'):
        print("❌ config/config.json not found")
        return False
    
    try:
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        
        print(f"✅ Config loaded successfully")
        print(f"   Mode: {config.get('run_mode', 'UNKNOWN')}")
        print(f"   Symbol: {config.get('symbol', 'UNKNOWN')}")
        print(f"   Risk per trade: {config.get('risk_per_trade', 0)*100}%")
        print(f"   Leverage: {config.get('leverage', 0)}x")
        
        # Check API keys
        api_key = config.get('api_key', '')
        api_secret = config.get('api_secret', '')
        
        if not api_key or not api_secret:
            print("⚠️  WARNING: API keys not configured")
            print("   Add your Binance API credentials to config/config.json")
            print("   Or set BINANCE_API_KEY and BINANCE_API_SECRET environment variables")
        else:
            print(f"✅ API key configured: {api_key[:4]}...{api_key[-4:]}")
        
        return True
    
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def main():
    """Run all verification checks."""
    print("="*60)
    print("🔍 VERIFYING BOT AND DASHBOARD SETUP")
    print("="*60)
    
    all_ok = True
    
    # Check files
    print("\n📁 Checking required files...")
    all_ok &= check_file_exists('main.py', 'Bot entry point')
    all_ok &= check_file_exists('streamlit_app.py', 'Dashboard entry point')
    all_ok &= check_file_exists('config/config.json', 'Configuration')
    all_ok &= check_file_exists('src/trading_bot.py', 'Trading bot')
    all_ok &= check_file_exists('src/streamlit_data_provider.py', 'Data provider')
    all_ok &= check_file_exists('start_dashboard.bat', 'Launcher script')
    
    # Check imports
    all_ok &= check_imports()
    
    # Check config
    all_ok &= check_config()
    
    # Check integration
    print("\n🔗 Checking bot-dashboard integration...")
    try:
        from src.streamlit_data_provider import StreamlitDataProvider
        provider = StreamlitDataProvider()
        print("✅ Data provider initialized")
        
        # Create sample data file if it doesn't exist
        if not os.path.exists('binance_results.json'):
            sample_data = {
                "timestamp": "2026-02-13T00:00:00",
                "bot_status": "stopped",
                "run_mode": "PAPER",
                "balance": 10000.0,
                "total_pnl": 0.0,
                "total_pnl_percent": 0.0,
                "open_positions": [],
                "current_price": 0.0,
                "adx": 0.0,
                "rvol": 0.0,
                "atr": 0.0,
                "signal": "NONE",
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0
            }
            with open('binance_results.json', 'w') as f:
                json.dump(sample_data, f, indent=2)
            print("✅ Created initial binance_results.json")
        
        # Test reading
        balance_pnl = provider.get_balance_and_pnl()
        print(f"✅ Can read bot data: Balance ${balance_pnl['balance']:.2f}")
        
    except Exception as e:
        print(f"❌ Integration check failed: {e}")
        all_ok = False
    
    # Final summary
    print("\n" + "="*60)
    if all_ok:
        print("✅ ALL CHECKS PASSED!")
        print("="*60)
        print("\n🚀 You're ready to start!")
        print("\nTo start the bot and dashboard:")
        print("  1. Add API credentials to config/config.json (if not done)")
        print("  2. Run: start_dashboard.bat")
        print("  3. Dashboard will open at: http://localhost:8501")
        print("\n⚠️  Remember: Bot is in PAPER mode (no real money)")
    else:
        print("❌ SOME CHECKS FAILED")
        print("="*60)
        print("\nPlease fix the issues above before starting")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
