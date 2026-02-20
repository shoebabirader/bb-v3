"""Test that dashboard can start the bot independently."""

import time
from src.streamlit_bot_controller import BotController

def test_dashboard_can_start_bot():
    """Test that BotController can start the bot."""
    
    print("="*60)
    print("Testing Dashboard Bot Control")
    print("="*60)
    
    controller = BotController()
    
    # Check if bot is already running
    print("\n1. Checking if bot is already running...")
    if controller._is_running():
        print("   ⚠️  Bot is already running, stopping it first...")
        success, msg = controller.stop_bot()
        print(f"   Stop result: {msg}")
        time.sleep(2)
    else:
        print("   ✅ Bot is not running (good)")
    
    # Try to start the bot
    print("\n2. Starting bot from dashboard controller...")
    success, message = controller.start_bot()
    
    if success:
        print(f"   ✅ {message}")
        print("   ✅ Bot started successfully from dashboard!")
        
        # Wait a moment
        time.sleep(3)
        
        # Verify it's running
        print("\n3. Verifying bot is running...")
        if controller._is_running():
            print("   ✅ Bot process detected!")
        else:
            print("   ❌ Bot process not found")
        
        # Stop the bot
        print("\n4. Stopping bot...")
        success, msg = controller.stop_bot()
        print(f"   {msg}")
        
        print("\n" + "="*60)
        print("✅ TEST PASSED: Dashboard can start bot independently!")
        print("="*60)
        print("\nYou can:")
        print("  1. Start only Streamlit: streamlit run streamlit_app.py")
        print("  2. Go to Controls page")
        print("  3. Click 'Start Bot' button")
        print("  4. Bot will launch in new window")
        
    else:
        print(f"   ❌ Failed: {message}")
        print("\n" + "="*60)
        print("❌ TEST FAILED")
        print("="*60)

if __name__ == "__main__":
    test_dashboard_can_start_bot()
