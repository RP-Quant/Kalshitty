from src.config import API_BASE, KEY_ID, EMAIL, PASSWORD
from src.utils.util import load_private_key_from_file
import requests
from src.utils.KalshiClient import ExchangeClient
from DataListeners import MarketListener, EventListener
import asyncio

def login():
    try:
        r = requests.post(
            "https://trading-api.kalshi.com/trade-api/v2/login",
            json={"email": EMAIL, "password": PASSWORD}
        )
        r.raise_for_status()  # Raise exception for HTTP errors
        response = r.json()
        token = response.get("token")
        if not token:
            raise ValueError("No token in response")
        return token
    except Exception as e:
        print(f"Error during authentication: {e}")
        exit(1)

private_key = load_private_key_from_file("src/kalshi.key")
client = ExchangeClient(exchange_api_base=API_BASE, key_id=KEY_ID, private_key=private_key)
token = login()

#listener = MarketListener(auth_token=token, market_ticker="KXSECVA-26DEC31-DC")
listener = EventListener(exchange_client=client, auth_token=token, event_ticker="KXBTCD-24DEC0917")
asyncio.run(listener.start_listen())