# from event import Event
import asyncio
from utils.KalshiClientV3 import ExchangeClient
import aiohttp
from registry import Registry
import time
from datacollection.DataListeners import EventListener

# continuously get data and update registry

class DataPuller:
    def __init__(self, registry: Registry, registry_mutex: asyncio.Lock, event_tickers: list[str], client: ExchangeClient, private_key, key_id) -> None:
        self.mutex = registry_mutex
        self.event_tickers = event_tickers
        self.client = client
        self.registry = registry
        self.event_listeners: dict[str, EventListener] = {}
        self.private_key = private_key
        self.key_id = key_id
        self.map_unique_to_subtitle = {}

    def is_valid(self, price):
        if 1 <= price <= 99:
            return price
        else:
            return None
        
    async def get_btc_data(self):
        async with aiohttp.ClientSession() as session:
            while True:
                raw = None
                btc_price = None

                async with session.get("https://www.cfbenchmarks.com/data/indices/BRTI") as resp:
                    raw = await resp.text()
                    try:
                        loc = raw.index("$")
                        end = loc + 1
                        while str.isdecimal(raw[end]) or raw[end] == '.' or raw[end] == ",":
                            end += 1
                        
                        out = raw[loc + 1 : end]
                        out = int(''.join([i for i in out if i != "," and i != "."]))
                        btc_price = out / 100
                    except:
                        continue
                
                async with self.mutex:
                    if btc_price != self.registry.btc_price:
                        self.registry.last_btc_recv_ts = time.time()
                    self.registry.btc_price = btc_price
                await asyncio.sleep(0.01)

    async def get_data(self):
        # set up event listeners    

        self.registry.add_events(self.event_tickers)
        
        for event_ticker in self.event_tickers:
            data = await self.client.get_event(event_ticker)

            async with self.mutex:
                for market in data["markets"]:
                    self.registry.data[event_ticker][market["yes_sub_title"]] = {
                        "yes_ask_price": None,
                        "yes_ask_volume": None,
                        "yes_bid_price": None,
                        "yes_bid_volume": None,
                        "no_ask_price": None,
                        "no_ask_volume": None,
                        "no_bid_price": None,
                        "no_bid_volume": None,
                        "unique_ticker": market["ticker"]
                    }
                    self.map_unique_to_subtitle[market["ticker"]] = market["yes_sub_title"]

            event = EventListener(exchange_client=self.client, private_key=self.private_key, key_id=self.key_id, event_ticker=event_ticker)
            self.event_listeners[event_ticker] = event
            asyncio.create_task(event.start_listen())

        await asyncio.sleep(10)
        first = False

        while True:
            if not first:
                print("starting data retrieval task")
                first = True
            async with self.mutex:
                for event in self.registry.data:
                    for market_ticker in self.event_listeners[event].get_market_tickers():
                        market = self.map_unique_to_subtitle[market_ticker]

                        yes_ask_volume, yes_ask_price = await self.event_listeners[event].get_ask(market_ticker, "yes")
                        yes_bid_volume, yes_bid_price = await self.event_listeners[event].get_bid(market_ticker, "yes")

                        no_ask_volume, no_ask_price = await self.event_listeners[event].get_ask(market_ticker, "no")
                        no_bid_volume, no_bid_price = await self.event_listeners[event].get_bid(market_ticker, "no")

                        yes_ask_price = self.is_valid(yes_ask_price)
                        yes_bid_price = self.is_valid(yes_bid_price)
                        no_ask_price = self.is_valid(no_ask_price)
                        no_bid_price = self.is_valid(no_bid_price)
                        
                        self.registry.data[event][market]["yes_ask_price"] = yes_ask_price
                        self.registry.data[event][market]["yes_ask_volume"] = yes_ask_volume

                        self.registry.data[event][market]["yes_bid_price"] = yes_bid_price
                        self.registry.data[event][market]["yes_bid_volume"] = yes_bid_volume

                        self.registry.data[event][market]["no_ask_price"] = no_ask_price
                        self.registry.data[event][market]["no_ask_volume"] = no_ask_volume

                        self.registry.data[event][market]["no_bid_price"] = no_bid_price
                        self.registry.data[event][market]["no_bid_volume"] = no_bid_volume

                self.registry.last_data_recv_ts = time.time()
            await asyncio.sleep(0.01)