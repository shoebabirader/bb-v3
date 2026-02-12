"""Check current price from Binance."""
from binance.client import Client
from src.config import Config

config = Config.load_from_file("config/config.json")
client = Client(config.api_key, config.api_secret)

ticker = client.futures_symbol_ticker(symbol=config.symbol)
print(f"Current {config.symbol} price: ${float(ticker['price']):.4f}")
