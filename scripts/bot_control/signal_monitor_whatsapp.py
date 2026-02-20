"""Signal Monitor with WhatsApp Notifications
Runs check_signals.py every 30 seconds and sends WhatsApp alerts when signals are detected.
"""

import time
import subprocess
import re
from datetime import datetime
from twilio.rest import Client as TwilioClient

# ===== CONFIGURATION =====
# Get these from https://www.twilio.com/console
TWILIO_ACCOUNT_SID = "your_account_sid_here"  # Replace with your Twilio Account SID
TWILIO_AUTH_TOKEN = "your_auth_token_here"    # Replace with your Twilio Auth Token
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"  # Twilio WhatsApp sandbox number
YOUR_WHATSAPP_NUMBER = "whatsapp:+1234567890"  # Your WhatsApp number (with country code)

CHECK_INTERVAL = 30  # seconds
SIGNAL_COOLDOWN = 300  # Don't send duplicate alerts within 5 minutes

# ===== GLOBAL STATE =====
last_signals = {}  # Track last signal time per symbol to avoid spam


def send_whatsapp_message(message):
    """Send WhatsApp message using Twilio API."""
    try:
        client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=YOUR_WHATSAPP_NUMBER
        )
        
        print(f"✓ WhatsApp message sent (SID: {msg.sid})")
        return True
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
    
    message = f"""🚨 TRADING SIGNAL DETECTED 🚨

Symbol: {signal['symbol']}
Signal: {signal['type']}
Time: {timestamp}

Action: Check your trading bot!
"""
    return message


def main():
    """Main monitoring loop."""
    print("=" * 60)
    print("Signal Monitor with WhatsApp Notifications")
    print("=" * 60)
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print(f"Alert cooldown: {SIGNAL_COOLDOWN} seconds")
    print(f"WhatsApp number: {YOUR_WHATSAPP_NUMBER}")
    print("=" * 60)
    print("\nStarting monitor... Press Ctrl+C to stop\n")
    
    # Send startup notification
    startup_msg = f"✅ Signal Monitor Started\nChecking every {CHECK_INTERVAL} seconds"
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
    if TWILIO_ACCOUNT_SID == "your_account_sid_here":
        print("ERROR: Please configure your Twilio credentials in the script!")
        print("\nSteps to set up:")
        print("1. Sign up at https://www.twilio.com/try-twilio")
        print("2. Get your Account SID and Auth Token from console")
        print("3. Set up WhatsApp sandbox: https://www.twilio.com/console/sms/whatsapp/sandbox")
        print("4. Update TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and YOUR_WHATSAPP_NUMBER in this script")
        exit(1)
    
    main()
