from utils.util import filter_digits, calc_fees, cut_down
import uuid
import time
import asyncio
from registry import Registry
from abc import ABC, abstractmethod
from utils.KalshiClientV3 import ExchangeClient

# base general strategy class

class BaseStrategy(ABC):
    def __init__(self, registry: Registry, event_tickers: list[str], client: ExchangeClient, registry_mutex: asyncio.Lock):
        self.registry = registry
        self.event_tickers = event_tickers
        self.client = client

        # maximum of 3 outstanding orders at a time for any given strategy
        self.concurrent_order_limit = 3
        self.order_semaphore = asyncio.Semaphore(self.concurrent_order_limit)

        # timestamp of when we sent the last data request that we received data for
        self.last_data_request_sent_timestamps = {e : time.time() for e in event_tickers}

        self.mutex = registry_mutex

    async def _place_order(self, ticker, order_type, action, side, amount, yes_price, no_price, expiration_ts, sell_position_floor=None, buy_max_cost=None):
        async with self.order_semaphore:
            order_params = {'ticker': ticker,
                        'client_order_id': str(uuid.uuid4()),
                        'type': order_type, # either "market" or "limit"
                        'action': action,
                        'side': side,
                        'count': amount,
                        'yes_price': yes_price,
                        'no_price': no_price, 
                        'expiration_ts': expiration_ts,
                        'sell_position_floor': sell_position_floor,
                        'buy_max_cost': buy_max_cost}
            
            response = await self.client.create_order(**order_params)
            print(action, amount, "shares of", ticker, side)
            print(response)
            print(time.time())

    def buy_yes_market_order(self, ticker, amount):
        asyncio.create_task(self._place_order(ticker=ticker, 
                                              order_type="market", action="buy",
                                              side="yes", amount=amount,
                                              yes_price=None, no_price=None, 
                                              expiration_ts=None))
    
    def buy_no_market_order(self, ticker, amount):
        asyncio.create_task(self._place_order(ticker=ticker, 
                                              order_type="market", action="buy",
                                              side="no", amount=amount,
                                              yes_price=None, no_price=None, 
                                              expiration_ts=None))
        
    def sell_yes_market_order(self, ticker, amount):
        asyncio.create_task(self._place_order(ticker=ticker, 
                                              order_type="market", action="sell",
                                              side="yes", amount=amount,
                                              yes_price=None, no_price=None, 
                                              expiration_ts=None))
        
    def sell_no_market_order(self, ticker, amount):
        asyncio.create_task(self._place_order(ticker=ticker, 
                                              order_type="market", action="sell",
                                              side="no", amount=amount,
                                              yes_price=None, no_price=None, 
                                              expiration_ts=None))
        
    def buy_yes_limit_order(self, ticker, amount, price, expiration_ts=None):
        asyncio.create_task(self._place_order(ticker=ticker, 
                                              order_type="limit", action="buy",
                                              side="yes", amount=amount,
                                              yes_price=price, no_price=None, 
                                              expiration_ts=expiration_ts))
        
    def buy_no_limit_order(self, ticker, amount, price, expiration_ts=None):
        asyncio.create_task(self._place_order(ticker=ticker, 
                                              order_type="limit", action="buy",
                                              side="no", amount=amount,
                                              yes_price=None, no_price=price, 
                                              expiration_ts=expiration_ts))
        
    def sell_yes_limit_order(self, ticker, amount, price, expiration_ts=None):
        asyncio.create_task(self._place_order(ticker=ticker, 
                                              order_type="limit", action="sell",
                                              side="yes", amount=amount,
                                              yes_price=price, no_price=None, 
                                              expiration_ts=expiration_ts))
        
    def sell_no_limit_order(self, ticker, amount, price, expiration_ts=None):
        asyncio.create_task(self._place_order(ticker=ticker, 
                                              order_type="limit", action="sell",
                                              side="no", amount=amount,
                                              yes_price=None, no_price=price, 
                                              expiration_ts=expiration_ts))
    
    @abstractmethod
    async def run(self):
        # Your strategy here
        pass


    # DEPRECATED: REST methods for getting data
    
    # async def get_volume_rest(self, client, market_ticker, side):
    #     async with self.volume_request_semaphore:
    #         result = await client.get_orderbook(ticker=market_ticker, depth=1)
    #         return result["orderbook"][side][-1][1]


    # async def _get_data_rest(self, client, event_ticker):
    #     async with self.request_semaphore:
    #         data_sent_timestamp = time.time()

    #         # get data
    #         data = await client.get_event(event_ticker)

    #         # if data_sent_timestamp > last_data_request_sent_timestamps[event_ticker], then update data,
    #         # meaning that we sent out the timestamp after we received back data from the last one, so the data is fresh
    #         async with self.mutex:
    #             if data_sent_timestamp > self.last_data_request_sent_timestamps[event_ticker]:
    #                 for market in data["markets"]:
    #                     if market["yes_sub_title"] not in self.registry.data[event_ticker]:
    #                         self.registry.data[event_ticker][market["yes_sub_title"]] = {
    #                             "yes_bid_price": None, 
    #                             "yes_ask_price": None,
    #                             "no_bid_price": None, 
    #                             "no_ask_price": None, 
    #                             # don't need to store the following because we get it on the fly anwyway
    #                             # "yes_bid_volume": None,
    #                             # "yes_ask_volume": None,
    #                             # "no_bid_volume": None,
    #                             # "no_ask_volume": None,
    #                             "previous_yes_bid": None,
    #                             "previous_yes_ask": None,
    #                             "unique_ticker": None
    #                         }

    #                     self.registry.data[event_ticker][market["yes_sub_title"]]["yes_bid_price"] = None if not (3 <= market["yes_bid"] <= 97) else market["yes_bid"]
    #                     self.registry.data[event_ticker][market["yes_sub_title"]]["yes_ask_price"] = None if not (3 <= market["yes_ask"] <= 97) else market["yes_ask"]
    #                     self.registry.data[event_ticker][market["yes_sub_title"]]["no_bid_price"] = None if not (3 <= market["no_bid"] <= 97) else market["no_bid"]
    #                     self.registry.data[event_ticker][market["yes_sub_title"]]["no_ask_price"] = None if not (3 <= market["no_ask"] <= 97) else market["no_ask"]
    #                     self.registry.data[event_ticker][market["yes_sub_title"]]["previous_yes_bid"] = None if not (1 <= market["previous_yes_bid"] <= 99) else market["previous_yes_bid"]
    #                     self.registry.data[event_ticker][market["yes_sub_title"]]["previous_yes_ask"] = None if not (1 <= market["previous_yes_ask"] <= 99) else market["previous_yes_ask"]
    #                     self.registry.data[event_ticker][market["yes_sub_title"]]["unique_ticker"] = market["ticker"]

    #                 # print(time.time() - data_sent_timestamp, data_sent_timestamp, [i for i in self.registry.data[event_ticker].keys()], time.time())
    #                 self.registry.last_data_recv_ts = time.time()
    #                 self.last_data_request_sent_timestamps[event_ticker] = data_sent_timestamp

    # async def get_market_data_rest(self, client):
    #     while True:
    #         for event_ticker in self.event_tickers:
    #             asyncio.create_task(self._get_data(client, event_ticker))
    #         await asyncio.sleep(1.0 / self.data_requests_per_second_per_event)