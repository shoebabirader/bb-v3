"""Test WhatsApp notifications to verify setup is working."""

import sys

print("=" * 60)
print("WhatsApp Notification Test")
print("=" * 60)
print("\nWhich version are you testing?")
print("1. FREE version (CallMeBot)")
print("2. Twilio version")
print()

choice = input("Enter 1 or 2: ").strip()

if choice == "1":
    print("\n--- Testing CallMeBot (FREE) ---\n")
    
    # Import from free version
    try:
        import requests
        from urllib.parse import quote
        
        phone = input("Enter your phone number (with country code, e.g., +923001234567): ").strip()
        api_key = input("Enter your CallMeBot API key: ").strip()
        
        print("\nSending test message...")
        
        message = "✅ WhatsApp test successful! Your signal monitor is working."
        encoded_message = quote(message)
        url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_message}&apikey={api_key}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✓ SUCCESS! Check your WhatsApp for the test message.")
        else:
            print(f"✗ FAILED: {response.text}")
            print("\nTroubleshooting:")
            print("1. Verify your phone number format (include country code)")
            print("2. Check your API key")
            print("3. Make sure you sent 'I allow callmebot to send me messages' to +34 644 44 71 67")
    
    except ImportError:
        print("✗ ERROR: 'requests' library not installed")
        print("Run: pip install requests")
    except Exception as e:
        print(f"✗ ERROR: {e}")

elif choice == "2":
    print("\n--- Testing Twilio ---\n")
    
    try:
        from twilio.rest import Client
        
        account_sid = input("Enter your Twilio Account SID: ").strip()
        auth_token = input("Enter your Twilio Auth Token: ").strip()
        from_number = input("Enter Twilio WhatsApp number (e.g., whatsapp:+14155238886): ").strip()
        to_number = input("Enter your WhatsApp number (e.g., whatsapp:+923001234567): ").strip()
        
        print("\nSending test message...")
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            from_=from_number,
            body="✅ WhatsApp test successful! Your signal monitor is working.",
            to=to_number
        )
        
        print(f"✓ SUCCESS! Message SID: {message.sid}")
        print("Check your WhatsApp for the test message.")
    
    except ImportError:
        print("✗ ERROR: 'twilio' library not installed")
        print("Run: pip install twilio")
    except Exception as e:
        print(f"✗ ERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Verify your Twilio credentials")
        print("2. Check your phone number format")
        print("3. Make sure you joined the WhatsApp sandbox")

else:
    print("Invalid choice!")

print("\n" + "=" * 60)
