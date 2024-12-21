from event import Event
import asyncio
from utils.KalshiClientV3 import ExchangeClient
from registry import Registry
import time

# continuously get data and update registry

class DataPuller:
    def __init__(self, registry: Registry, registry_mutex: asyncio.Lock, event_tickers: list[str], client: ExchangeClient) -> None:
        self.mutex = registry_mutex
        self.event_tickers = event_tickers
        self.client = client
        self.registry = registry
        self.event_listeners = {}

    async def get_data(self):
        # set up event listeners    

        self.registry.add_events(self.event_tickers)
        
        for event_ticker in self.event_tickers:
            data = await self.client.get_event(event_ticker)

            market_tickers = []

            async with self.mutex:
                for market in data["markets"]:
                    self.registry.data[event_ticker][market["yes_sub_title"]] = {
                        "yes_price": None,
                        "no_price": None, 
                        "yes_volume": None,
                        "no_volume": None,
                        "unique_ticker": market["ticker"]
                    }

                    market_tickers.append(market["ticker"])

            event = Event(market_tickers=market_tickers)
            self.event_listeners[event_ticker] = event
            asyncio.create_task(event.start_listen())

        while True:
            async with self.mutex:
                for event in self.registry.data:
                    for market in self.registry.data[event]:
                        market_ticker = self.registry.data[event][market]["unique_ticker"]

                        yes_volume, yes_price = await self.event_listeners[event].get_data(market_ticker, "yes")
                        no_volume, no_price = await self.event_listeners[event].get_data(market_ticker, "no")

                        self.registry.data[event][market]["yes_price"] = yes_price
                        self.registry.data[event][market]["no_price"] = no_price
                        self.registry.data[event][market]["yes_volume"] = yes_volume
                        self.registry.data[event][market]["no_volume"] = no_volume

                self.registry.last_data_recv_ts = time.time()
            await asyncio.sleep(0.001)