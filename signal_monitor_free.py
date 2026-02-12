"""Signal Monitor with FREE WhatsApp Notifications (CallMeBot)
Runs check_signals.py every 30 seconds and sends WhatsApp alerts when signals are detected.
100% FREE - No registration, no API keys, no credit card needed!
"""

import time
import subprocess
import requests
from datetime import datetime
from urllib.parse import quote

# ===== CONFIGURATION =====
# Get your API key by:
# 1. Add +34 644 44 71 67 to WhatsApp contacts
# 2. Send message: "I allow callmebot to send me messages"
# 3. You'll receive your API key
YOUR_PHONE_NUMBER = "+1234567890"  # Your phone number with country code (no spaces)
CALLMEBOT_API_KEY = "your_api_key_here"  # API key from CallMeBot

CHECK_INTERVAL = 30  # seconds
SIGNAL_COOLDOWN = 300  # Don't send duplicate alerts within 5 minutes

# ===== GLOBAL STATE =====
last_signals = {}  # Track last signal time per symbol to avoid spam


def send_whatsapp_message(message):
    """Send WhatsApp message using CallMeBot FREE API."""
    try:
        # URL encode the message
        encoded_message = quote(message)
        
        # CallMeBot API endpoint
        url = f"https://api.callmebot.com/whatsapp.php?phone={YOUR_PHONE_NUMBER}&text={encoded_message}&apikey={CALLMEBOT_API_KEY}"
        
        # Send request
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✓ WhatsApp message sent")
            return True
        else:
            print(f"✗ Failed to send WhatsApp: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Failed to send WhatsApp: {e}")
        return False


def run_signal_check():
    """Run check_signals.py and capture output."""
    try:
        result = subprocess.run(
            ["python", "check_signals.py"],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        print("✗ Signal check timed out")
        return None
    except Exception as e:
        print(f"✗ Error running signal check: {e}")
        return None


def parse_signals(output):
    """Parse check_signals.py output to detect signals."""
    if not output:
        return []
    
    signals = []
    current_symbol = None
    
    for line in output.split('\n'):
        # Detect symbol
        if line.startswith("--- ") and line.endswith(" ---"):
            current_symbol = line.strip("- ")
        
        # Detect LONG signal
        elif "LONG SIGNAL DETECTED" in line and current_symbol:
            signals.append({
                "symbol": current_symbol,
                "type": "LONG",
                "timestamp": datetime.now()
            })
        
        # Detect SHORT signal
        elif "SHORT SIGNAL DETECTED" in line and current_symbol:
            signals.append({
                "symbol": current_symbol,
                "type": "SHORT",
                "timestamp": datetime.now()
            })
    
    return signals


def should_send_alert(symbol, signal_type):
    """Check if we should send alert (avoid spam)."""
    key = f"{symbol}_{signal_type}"
    now = time.time()
    
    if key in last_signals:
        time_since_last = now - last_signals[key]
        if time_since_last < SIGNAL_COOLDOWN:
            return False
    
    last_signals[key] = now
    return True


def format_alert_message(signal):
    """Format WhatsApp alert message."""
    timestamp = signal["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    
    message = f"""🚨 TRADING SIGNAL 🚨

Symbol: {signal['symbol']}
Signal: {signal['type']}
Time: {timestamp}

Check your bot!"""
    return message


def main():
    """Main monitoring loop."""
    print("=" * 60)
    print("Signal Monitor with FREE WhatsApp Notifications")
    print("=" * 60)
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print(f"Alert cooldown: {SIGNAL_COOLDOWN} seconds")
    print(f"Phone number: {YOUR_PHONE_NUMBER}")
    print("=" * 60)
    print("\nStarting monitor... Press Ctrl+C to stop\n")
    
    # Send startup notification
    startup_msg = f"✅ Signal Monitor Started (Checking every {CHECK_INTERVAL}s)"
    send_whatsapp_message(startup_msg)
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Check #{iteration}")
            
            # Run signal check
            output = run_signal_check()
            
            if output:
                # Parse for signals
                signals = parse_signals(output)
                
                if signals:
                    print(f"✓ Found {len(signals)} signal(s)")
                    
                    # Send WhatsApp alerts
                    for signal in signals:
                        if should_send_alert(signal["symbol"], signal["type"]):
                            message = format_alert_message(signal)
                            print(f"  → Sending alert for {signal['symbol']} {signal['type']}")
                            send_whatsapp_message(message)
                            time.sleep(2)  # Rate limit: wait 2 seconds between messages
                        else:
                            print(f"  → Skipping alert (cooldown) for {signal['symbol']} {signal['type']}")
                else:
                    print("✓ No signals detected")
            else:
                print("✗ Failed to check signals")
            
            # Wait for next check
            print(f"  Waiting {CHECK_INTERVAL} seconds...\n")
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        shutdown_msg = "⛔ Signal Monitor Stopped"
        send_whatsapp_message(shutdown_msg)
        print("Monitor stopped.")


if __name__ == "__main__":
    # Validate configuration
    if CALLMEBOT_API_KEY == "your_api_key_here":
        print("=" * 60)
        print("ERROR: Please configure CallMeBot first!")
        print("=" * 60)
        print("\nQuick Setup (2 minutes):")
        print("\n1. Add this number to WhatsApp contacts:")
        print("   +34 644 44 71 67")
        print("\n2. Send this message to that number:")
        print("   I allow callmebot to send me messages")
        print("\n3. You'll receive your API key")
        print("\n4. Update these values in signal_monitor_free.py:")
        print("   YOUR_PHONE_NUMBER = '+923001234567'  # Your number")
        print("   CALLMEBOT_API_KEY = 'your_api_key'   # From step 3")
        print("\n5. Install requests:")
        print("   pip install requests")
        print("\n6. Run again:")
        print("   python signal_monitor_free.py")
        print("=" * 60)
        exit(1)
    
    main()
