import json
import websockets
import requests
import asyncio
from collections import defaultdict
from KalshiClientsBaseV2ApiKey import ExchangeClient
from pprint import pprint
from config import EMAIL, PASSWORD, WEBSOCKET_ENDPOINT
from bisect import bisect_left
import time

class Event:
    def __init__(self, ticker, exchange_client: ExchangeClient):
        self.ticker = ticker
        self.markets = {}

        self.exchange_client = exchange_client
        self.seq = 1
        self.sid = 1
        self.id = 1
        self.auth_token = self.login()
        self.last_time = time.time()

    def initialize(self):
        event = self.exchange_client.get_event(self.ticker)
        for market in event["markets"]:
            self.markets[market["ticker"]] = {
                "yes" : [0]*100,
                "no" : [0]*100
            }
        
        #pprint(self.markets)

    def login(self):
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

    async def process_message(self, message):
        data = json.loads(message)
        #pprint(data)
        msg = data["msg"]
        match data.get("type", "subscribe"):
            case "orderbook_snapshot":
                self.seq = data["seq"]
                self.sid = data["sid"]
                for price, orders in msg.get("yes", []):
                    self.markets[msg["market_ticker"]]["yes"][price-1] = orders
                for price, orders in msg.get("no", []):
                    self.markets[msg["market_ticker"]]["no"][price-1] = orders
            case "orderbook_delta":
                if data["seq"]-self.seq != 1:
                    print(f"Out of sequence. Expected: {self.seq+1}, got: {data["seq"]}. Resubscribing...")
                    return False
                self.markets[msg["market_ticker"]][msg["side"]][msg["price"]-1] += msg["delta"]
                self.seq = data["seq"]
            case "subscribe":
                print("Subscribed to markets!")

        return True

    async def start_listen(self):
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        msg = json.dumps({
            "id": self.id,
            "cmd": "subscribe",
            "params": {
                "channels": ["orderbook_delta"],
                "market_tickers": list(self.markets.keys())
            }
        })
        self.id += 1
        # async def process_message(message):
        #     decoded = json.loads(message)
        #     pprint(decoded)
        
        try:
            async with websockets.connect(WEBSOCKET_ENDPOINT, additional_headers=headers) as websocket:
                await websocket.send(msg)
                print(f"Sent message: {msg}")

                while True:
                    try:
                        message = await websocket.recv()
                        #print(f"Seconds elapsed: {time.time()-self.last_time}")
                        #self.last_time = time.time()
                        if not await self.process_message(message):
                            unsub = json.dumps({
                                "id": self.id,
                                "cmd": "unsubscribe",
                                "params": {
                                    "sids" : [self.sid]
                                }
                            })
                            self.id += 1
                            await websocket.send(unsub)
                            print(f"Sent unsub message: {unsub}")
                            message = await websocket.recv()
                            print(f"Unsub message recieved: {message}")
                            sub = json.dumps({
                                "id": self.id,
                                "cmd": "subscribe",
                                "params": {
                                    "channels": ["orderbook_delta"],
                                    "market_tickers": list(self.markets.keys())
                                }
                            })
                            self.id += 1
                            await websocket.send(sub)
                            print(f"Sent sub message: {sub}")
                            message = await websocket.recv()
                            print(f"Sub message recieved: {message}")

                    except websockets.ConnectionClosed as e:
                        print(f"Connection closed: {e}")
                        break
                    except Exception as e:
                        print(f"An error occurred: {e}")
                        break
        except Exception as e:
            print(f"Failed to connect to WebSocket: {e}")

    async def get_data(self, ticker, side):
        try:
            i = 99
            while self.markets[ticker][side][i] == 0 and i > 0:
                i -= 1
            #print(self.markets[ticker][side])
            return self.markets[ticker][side][i], i+1
        except Exception as e:
            print(e)
            return -1, -1