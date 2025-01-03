import json
import websockets
import requests
import asyncio
from collections import defaultdict
from pprint import pprint
from config import EMAIL, PASSWORD, WEBSOCKET_ENDPOINT
from bisect import bisect_left
import time

class Event:
    def __init__(self, market_tickers):
        self.market_tickers = market_tickers # list of market tickers
        self.markets = {}

        self.seq = 1
        self.sid = 1
        self.id = 1
        self.auth_token = self.login()
        self.last_time = time.time()
        
        for market_ticker in market_tickers:
            self.markets[market_ticker] = {
                "yes" : [0]*100,
                "no" : [0]*100
            }

        self.mutex = asyncio.Lock()
        
        #pprint(self.markets)

    def login(self):
        try:
            r = requests.post(
                "https://api.elections.kalshi.com/trade-api/v2/login",
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

    def process_message(self, message):
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
                    seq = data["seq"]
                    print(f"Out of sequence. Expected: {self.seq+1}, got: {seq}. Resubscribing...")
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
                        res = None
                        async with self.mutex:
                            res = self.process_message(message)
                        if not res:
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
            async with self.mutex:
                while i >= 0 and self.markets[ticker][side][i] == 0:
                    i -= 1
                    
                if i < 0:
                    return None, None
                else:
                    return self.markets[ticker][side][i], i+1
        except Exception as e:
            print(e)
            return None, None