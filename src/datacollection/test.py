from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from src.utils.KalshiClient import ExchangeClient
from DataListeners import MarketListener, EventListener
import asyncio

def load_private_key_from_file(file_path):
    with open(file_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,  # or provide a password if your key is encrypted
            backend=default_backend()
        )
    return private_key

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
KEY_ID = "aab7962b-a788-4f1b-8b7d-5f8c9bc4a7f9"

private_key = load_private_key_from_file("src/kalshi.key")
client = ExchangeClient(exchange_api_base=API_BASE, key_id=KEY_ID, private_key=private_key)
#token = login()

#listener = MarketListener(auth_token=token, market_ticker="KXSECVA-26DEC31-DC")
listener = EventListener(exchange_client=client, auth_token="", event_ticker="KXBTC-24DEC2219")
asyncio.run(listener.start_listen())