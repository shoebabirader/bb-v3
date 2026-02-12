#!/usr/bin/env python3
"""Test Binance API connection before starting bot."""

import json
from binance.client import Client

def test_connection():
    """Test if we can connect to Binance API."""
    print("=" * 80)
    print("TESTING BINANCE API CONNECTION")
    print("=" * 80)
    print()
    
    # Load config
    with open('config/config.json', 'r') as f:
        config = json.load(f)
    
    api_key = config['api_key']
    api_secret = config['api_secret']
    symbol = config['symbol']
    
    print(f"Testing connection with symbol: {symbol}")
    print()
    
    try:
        # Initialize client
        print("1. Initializing Binance client...")
        client = Client(api_key, api_secret)
        print("   ✓ Client initialized")
        print()
        
        # Test account access
        print("2. Testing account access...")
        account = client.futures_account()
        balance = float(account['totalWalletBalance'])
        print(f"   ✓ Account accessible")
        print(f"   Balance: ${balance:.2f} USDT")
        print()
        
        # Test fetching historical data
        print(f"3. Testing historical data fetch for {symbol}...")
        klines = client.futures_klines(
            symbol=symbol,
            interval='15m',
            limit=100
        )
        print(f"   ✓ Fetched {len(klines)} candles")
        print()
        
        # Test current price
        print(f"4. Testing current price for {symbol}...")
        ticker = client.futures_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])
        print(f"   ✓ Current price: ${price:.4f}")
        print()
        
        print("=" * 80)
        print("✓ ALL TESTS PASSED - API CONNECTION IS WORKING")
        print("=" * 80)
        print()
        print("You can now start the bot with: python main.py")
        return True
        
    except Exception as e:
        print()
        print("=" * 80)
        print("✗ API CONNECTION FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        print("Possible causes:")
        print("  1. Invalid API credentials")
        print("  2. Network/firewall blocking connection")
        print("  3. Binance API is down")
        print("  4. API permissions not set correctly")
        print()
        return False

if __name__ == "__main__":
    test_connection()
