import websockets
import json
import requests
import asyncio
import uuid
from pprint import pprint
from bisect import bisect_left

from config import WEBSOCKET_ENDPOINT, EMAIL, PASSWORD

# Authenticate and get token
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
except Exception as e:
    print(f"Error during authentication: {e}")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

msg = json.dumps({
    "id": 1,
    "cmd": "subscribe",
    "params": {
        "channels": ["orderbook_delta"],
        "market_tickers": "POPVOTEMOVSMALLER-24-R-B1.4"
    }
})

# Message processing
async def process_message(message):
    decoded = json.loads(message)
    pprint(decoded)

# WebSocket listener
async def listen():
    try:
        async with websockets.connect(WEBSOCKET_ENDPOINT, additional_headers=headers) as websocket:
            await websocket.send(msg)
            print(f"Sent message: {msg}")

            while True:
                try:
                    print("trying..")
                    message = await websocket.recv()
                    await process_message(message)
                except websockets.ConnectionClosed as e:
                    print(f"Connection closed: {e}")
                    break
                except Exception as e:
                    print(f"An error occurred: {e}")
                    break
    except Exception as e:
        print(f"Failed to connect to WebSocket: {e}")

# Run the event loop
if __name__ == "__main__":
    asyncio.run(listen())
