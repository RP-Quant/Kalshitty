import json
import websockets
import asyncio
from utils.KalshiClient import ExchangeClient
from config import WEBSOCKET_ENDPOINT
from pprint import pprint

class KalshiWebsocketClient:
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.websocket = None
        self.lock = asyncio.Lock()
        self.id = 1
        self.sid = 1

        self.websocket_endpoint = WEBSOCKET_ENDPOINT

    async def connect(self):
        """Connect to WebSocket and establish the connection."""
        if self.websocket is not None:
            print("Already connected!")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        try:
            self.websocket = await websockets.connect(self.websocket_endpoint, additional_headers=headers)
            print("WebSocket connection established.")
        except Exception as e:
            print(f"Failed to connect to WebSocket: {e}")
    
    async def subscribe(self, msg):
        if self.websocket is None:
            raise RuntimeError("WebSocket is not connected. Call connect() first.")
        print(msg)
        async with self.lock:
            self.id += 1
            await self.websocket.send(msg)
            print(f"Sent subscription message: {msg}")
            message = await self.websocket.recv()
            print(f"Subscription message recieved: {message}")
            self.sid = json.loads(message)['msg']['sid']

    async def unsubscribe(self):
        if self.websocket is None:
            raise RuntimeError("WebSocket is not connected. Call connect() first.")
    
        async with self.lock:
            msg = json.dumps({
                "id": self.id,
                "cmd": "unsubscribe",
                "params": {
                    "sids" : [self.sid]
                }
            })
            self.id += 1
            await self.websocket.send(msg)
            print(f"Sent unsubscription message: {msg}")
            message = await self.websocket.recv()
            print(f"Unsubscription message recieved: {message}")

class MarketListener(KalshiWebsocketClient):
    def __init__(self, auth_token: str, market_ticker: str):
        super().__init__(auth_token=auth_token)
        self.market_ticker = market_ticker

        self.seq = 0

        self.orderbook = {
            "yes" : [0]*100,
            "no" : [0]*100
        }

    async def process_message(self, message):
        type = message['type']
        data = message['msg']
        seq = message['seq']

        async with self.lock:
            match type:
                case "orderbook_snapshot":
                    self.seq = seq
                    for price, orders in data.get('yes', []):
                        self.orderbook['yes'][price] = orders
                    for price, orders in data.get('no', []):
                        self.orderbook['no'][price] = orders
                    print("Internal orderbook set to snapshot")
                    pprint(self.orderbook)

                case "orderbook_delta":
                    if seq != self.seq+1:
                        print("Datastream out of order.")
                        return False
                    
                    self.orderbook[data['side']][data['price']] += data['delta']
                    self.seq = seq
                    print("Internal orderbook updated with delta")

        return True

    async def start_listen(self):
        if not self.websocket:
            await self.connect()
        if self.websocket is None:
            print("Failed to establish WebSocket connection. Exiting...")
            return
        
        await self.subscribe(msg=json.dumps({
                "id": self.id,
                "cmd": "subscribe",
                "params": {
                    "channels": ["orderbook_delta"],
                    "market_tickers": [self.market_ticker]
                }
            }))

        while True:
            try:
                message = json.loads(await self.websocket.recv())
                if message['msg']['market_ticker']:
                    await self.process_message(message)
                await asyncio.sleep(1)
            except websockets.ConnectionClosed as e:
                print(f"Connection closed: {e}")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                break

    async def get_ask(self, side):
        i = 99
        side = "yes" if side == "no" else "yes"
        async with self.lock:
            while self.orderbook[side][i] == 0 and i > 0:
                i -= 1
            #print(self.markets[ticker][side])
            return 100-self.orderbook[side][side][i], i+1
    
    async def get_bid(self, side):
        i = 99
        async with self.lock:
            while self.orderbook[side][i] == 0 and i > 0:
                i -= 1
            #print(self.markets[ticker][side])
            return self.orderbook[side][side][i], i+1
        
    async def get_snapshot(self):
        async with self.lock:
            return self.orderbook

class EventListener(KalshiWebsocketClient):
    def __init__(self, exchange_client: ExchangeClient, auth_token: str, event_ticker: str):
        super().__init__(auth_token=auth_token)
        self.exchange_client = exchange_client
        self.event_ticker = event_ticker

        self.seq = 0

        self.orderbooks = {}

    def get_markets(self):
        event = self.exchange_client.get_event(self.event_ticker)
        for market in event["markets"]:
            self.orderbooks[market["ticker"]] = {
                "yes" : [0]*100,
                "no" : [0]*100
            }

    async def process_message(self, message):
        type = message['type']
        data = message['msg']
        seq = message['seq']
        ticker = data['market_ticker']

        async with self.lock:
            match type:
                case "orderbook_snapshot":
                    self.seq = seq
                    for price, orders in data.get('yes', []):
                        self.orderbooks[ticker]['yes'][price] = orders
                    for price, orders in data.get('no', []):
                        self.orderbooks[ticker]['no'][price] = orders
                    print(f"Internal orderbook for {ticker} set to snapshot")
                    #pprint(self.orderbooks[ticker])

                case "orderbook_delta":
                    if seq != self.seq+1:
                        print("Datastream out of order.")
                        return False
                    
                    self.orderbooks[ticker][data['side']][data['price']] += data['delta']
                    self.seq = seq
                    #print(f"Internal orderbook for {ticker} updated with delta")

        return True

    async def start_listen(self):
        self.get_markets()
        if not self.websocket:
            await self.connect()
        if self.websocket is None:
            print("Failed to establish WebSocket connection. Exiting...")
            return
        
        await self.subscribe(msg=json.dumps({
                "id": self.id,
                "cmd": "subscribe",
                "params": {
                    "channels": ["orderbook_delta"],
                    "market_tickers": list(self.orderbooks.keys())
                }
            }))

        while True:
            try:
                message = json.loads(await self.websocket.recv())
                if message['msg']['market_ticker']:
                    await self.process_message(message)
                await asyncio.sleep(0.01)
            except websockets.ConnectionClosed as e:
                print(f"Connection closed: {e}")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                break

    def get_market_tickers(self):
        return self.orderbooks.keys()

    async def get_snapshot(self, side):
        data = {}
        for market in self.get_market_tickers():
            print(f"recording for {market}")
            data[market] = await self.get_ask(side, market)
            print(market, data[market])
        return data

    async def get_ask(self, side, market):
        i = 99
        side = "yes" if side == "no" else "yes"
        async with self.lock:
            while self.orderbooks[market][side][i] == 0 and i > 0:
                i -= 1
            #print(self.markets[ticker][side])
            return 100-self.orderbooks[market][side][i], i+1
    
    async def get_bid(self, side, market):
        i = 99
        async with self.lock:
            while self.orderbooks[market][side][i] == 0 and i > 0:
                i -= 1
            #print(self.markets[ticker][side])
            return self.orderbooks[market][side][side][i], i+1