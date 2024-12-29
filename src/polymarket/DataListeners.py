import asyncio
import websockets
import datetime
import json
import pprint

class TokenListener:
    def __init__(self, tokens):
        self.tokens = tokens
        self.websocket = None
        self.lock = asyncio.Lock()  # Not currently used but kept for extensibility
        self.orderbooks = {}

    async def connect(self):
        """
        Establishes the websocket connection.
        """
        try:
            # Connect to the websocket with timeout
            self.websocket = await websockets.connect('wss://ws-subscriptions-clob.polymarket.com/ws/market')
            print("WebSocket connected")
        except Exception as e:
            print(f"Connection failed: {e}")
            self.websocket = None

    async def process_msg(self, msg):
        async with self.lock:
            asset_id = msg['asset_id']
            match msg['event_type']:
                case 'book':
                    if asset_id not in self.orderbooks:
                        self.orderbooks[asset_id] = {'bids' : [0]*100, 'asks' : [0]*100}
                    
                    for order in msg['bids']:
                        self.orderbooks[asset_id]['bids'][int(float(order['price'])*100)] = float(order['size'])
                    
                    for order in msg['asks']:
                        self.orderbooks[asset_id]['asks'][int(float(order['price'])*100)] = float(order['size'])

                    print(f"Successfully set orderbook for asset {asset_id}")

                case 'price_change':
                    for change in msg['changes']:
                        match change['side']:
                            case 'BUY':
                                self.orderbooks[asset_id]['bids'][int(float(change['price'])*100)] = float(change['size'])
                            case 'SELL':
                                self.orderbooks[asset_id]['asks'][int(float(change['price'])*100)] = float(change['size'])

    async def get_best_ask(self, token):
        if token not in self.orderbooks:
            print("Token not found on internal orderbook")
            return
        async with self.lock:
            i = 1
            while self.orderbooks[token]['asks'][i] == 0 and i < 100:
                i += 1
            return (i, self.orderbooks[token]['asks'][i])
    
    async def get_best_bid(self, token):
        if token not in self.orderbooks:
            print("Token not found on internal orderbook")
            return
        async with self.lock:
            i = 99
            while self.orderbooks[token]['bids'][i] == 0 and i > 0:
                i -= 1
            return (i+1, self.orderbooks[token]['bids'][i])

    async def start_listen(self):
        last_pong = datetime.datetime.now()

        await self.connect()
        if not self.websocket:
            print("WebSocket connection could not be established.")
            return

        try:
            # Send subscription message
            await self.websocket.send(json.dumps({"assets_ids": self.tokens, "type": "market"}))
            print("Subscribed to tokens.")

            while True:
                m = await self.websocket.recv()

                # Handle the case where the message is empty
                if not m:
                    print("Received empty message.")
                    continue  # Skip this iteration and wait for the next message

                # Handle the case where the message is not valid JSON
                try:
                    data = json.loads(m)
                    for d in data:
                        await self.process_msg(d)
                except json.JSONDecodeError:
                    print(f"Received invalid JSON: {m}")
                    continue  # Skip this iteration and wait for the next message

                # Handle PONG message to reset the timeout
                if m != "PONG":
                    last_pong = datetime.datetime.now()

                # Send PING if server hasn't responded in 10 seconds
                if last_pong + datetime.timedelta(seconds=10) < datetime.datetime.now():
                    await self.websocket.send("PING")

        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection closed: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
            await self.start_listen()  # Reconnect

        except Exception as e:
            print(f"Error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
            await self.start_listen()  # Reconnect


async def main():
    # Tokens
    yes_token = "88458672007514219171605090869548159546185169218791748266793909997093690233909"
    no_token = "6923631216705603224951354298877779165510028272364667413602219029200417868719"

    # Initialize listener
    listener = TokenListener(tokens=[yes_token])
    t1 = asyncio.create_task(listener.start_listen())

    async def get_ask():
        while 1:
            print(await listener.get_best_bid(yes_token))
            await asyncio.sleep(1)
    
    t2 = asyncio.create_task(get_ask())

    await asyncio.gather(t1, t2)

asyncio.run(main())
