import json
import websockets
import asyncio
from utils.KalshiClient import ExchangeClient
from config import WEBSOCKET_ENDPOINT
from pprint import pprint
from datetime import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
import base64


class KalshiWebsocketClient:
    def __init__(self, private_key: rsa.RSAPrivateKey, key_id):
        self.websocket = None
        self.lock = asyncio.Lock()
        self.id = 1
        self.sid = 1
        self.private_key = private_key
        self.key_id = key_id

        self.websocket_endpoint = WEBSOCKET_ENDPOINT

    def sign_pss_text(self, text: str) -> str:
        # Before signing, we need to hash our message.
        # The hash is what we actually sign.
        # Convert the text to bytes
        message = text.encode('utf-8')
        try:
            signature = self.private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH
                ),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except InvalidSignature as e:
            raise ValueError("RSA sign PSS failed") from e

    async def connect(self):
        """Connect to WebSocket and establish the connection."""
        if self.websocket is not None:
            print("Already connected!")
            return
        current_time = datetime.now()
        timestamp = current_time.timestamp()
        current_time_milliseconds = int(timestamp * 1000)
        timestampt_str = str(current_time_milliseconds)

        msg_string = timestampt_str + "GET" + '/trade-api/ws/v2'
        signature = self.sign_pss_text(msg_string)

        headers = {"Content-Type": "application/json"}
        headers["KALSHI-ACCESS-KEY"] = self.key_id
        headers["KALSHI-ACCESS-SIGNATURE"] = signature
        headers["KALSHI-ACCESS-TIMESTAMP"] = timestampt_str

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
    def __init__(self, private_key, key_id, market_ticker: str):
        super().__init__(private_key=private_key, key_id=key_id)
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
                    #print("Internal orderbook updated with delta")

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
        side = "yes" if side == "no" else "no"
        print(side)
        async with self.lock:
            while self.orderbook[side][i] == 0 and i > 0:
                i -= 1
            #print(self.markets[ticker][side])
            return self.orderbook[side][i], 100-i
    
    async def get_bid(self, side):
        i = 99
        async with self.lock:
            while self.orderbook[side][i] == 0 and i > 0:
                i -= 1
            #print(self.markets[ticker][side])
            return self.orderbook[side][i], i
        
    async def get_snapshot(self):
        async with self.lock:
            return self.orderbook

class EventListener(KalshiWebsocketClient):
    def __init__(self, exchange_client: ExchangeClient, private_key, key_id, event_ticker: str):
        super().__init__(private_key=private_key, key_id=key_id)
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
                    pprint(self.orderbooks[ticker])

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
        
    async def get_ask(self, market, side):
        i = 99
        side = "yes" if side == "no" else "no"
        async with self.lock:
            while self.orderbooks[market][side][i] == 0 and i > 0:
                i -= 1
            #print(self.markets[ticker][side])
            return self.orderbooks[market][side][i], 100-i
    
    async def get_bid(self, market, side):
        i = 99
        async with self.lock:
            while self.orderbooks[market][side][i] == 0 and i > 0:
                i -= 1
            #print(self.markets[ticker][side])
            return self.orderbooks[market][side][i], i