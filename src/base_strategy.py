from KalshiClientV3 import ExchangeClient
from util import filter_digits, calc_fees, cut_down
import uuid
import time
import asyncio
from registry import Registry
from abc import ABC, abstractmethod

# base general strategy class
class BaseStrategy(ABC):
    def __init__(self, api_base: str, key_id: str, private_key, registry: Registry, event_tickers: list[str]):
        self.api_base = api_base
        self.key_id = key_id
        self.private_key = private_key
        self.registry = registry
        self.event_tickers = event_tickers

        self.registry.add_events(event_tickers)

        # total number of market data requests per second throughout entire program MUST BE LESS THAN 10
        # if you're looking at 2 events, for example, setting this variable to 3 means
        # minimum 6 requests per second 
        self.data_requests_per_second_per_event = 3

        # maximum of 6 outstanding market data requests at a time
        self.concurrent_request_limit = 6
        self.request_semaphore = asyncio.Semaphore(self.concurrent_request_limit)

        # maximum of 3 outstanding orders at a time
        self.concurrent_order_limit = 3
        self.order_semaphore = asyncio.Semaphore(self.concurrent_order_limit)

        # maximum of 3 outstanding orders at a time
        self.concurrent_volume_request_limit = 3
        self.volume_request_semaphore = asyncio.Semaphore(self.concurrent_volume_request_limit)

        # timestamp of when we sent the last data request that we received data for
        self.last_data_request_sent_timestamps = {e : time.time() for e in event_tickers}

        self.mutex = asyncio.Lock()

    async def _get_data(self, client, event_ticker):
        async with self.request_semaphore:
            data_sent_timestamp = time.time()

            # get data
            data = await client.get_event(event_ticker)

            # if data_sent_timestamp > last_data_request_sent_timestamps[event_ticker], then update data,
            # meaning that we sent out the timestamp after we received back data from the last one, so the data is fresh
            async with self.mutex:
                if data_sent_timestamp > self.last_data_request_sent_timestamps[event_ticker]:
                    for market in data["markets"]:
                        if market["yes_sub_title"] not in self.registry.data[event_ticker]:
                            self.registry.data[event_ticker][market["yes_sub_title"]] = {
                                "yes_bid_price": None, 
                                "yes_ask_price": None,
                                "no_bid_price": None, 
                                "no_ask_price": None, 
                                # don't need to store the following because we get it on the fly anwyway
                                # "yes_bid_volume": None,
                                # "yes_ask_volume": None,
                                # "no_bid_volume": None,
                                # "no_ask_volume": None,
                                "previous_yes_bid": None,
                                "previous_yes_ask": None,
                                "unique_ticker": None
                            }

                        self.registry.data[event_ticker][market["yes_sub_title"]]["yes_bid_price"] = None if not (3 <= market["yes_bid"] <= 97) else market["yes_bid"]
                        self.registry.data[event_ticker][market["yes_sub_title"]]["yes_ask_price"] = None if not (3 <= market["yes_ask"] <= 97) else market["yes_ask"]
                        self.registry.data[event_ticker][market["yes_sub_title"]]["no_bid_price"] = None if not (3 <= market["no_bid"] <= 97) else market["no_bid"]
                        self.registry.data[event_ticker][market["yes_sub_title"]]["no_ask_price"] = None if not (3 <= market["no_ask"] <= 97) else market["no_ask"]
                        self.registry.data[event_ticker][market["yes_sub_title"]]["previous_yes_bid"] = None if not (1 <= market["previous_yes_bid"] <= 99) else market["previous_yes_bid"]
                        self.registry.data[event_ticker][market["yes_sub_title"]]["previous_yes_ask"] = None if not (1 <= market["previous_yes_ask"] <= 99) else market["previous_yes_ask"]
                        self.registry.data[event_ticker][market["yes_sub_title"]]["unique_ticker"] = market["ticker"]

                    # print(time.time() - data_sent_timestamp, data_sent_timestamp, [i for i in self.registry.data[event_ticker].keys()], time.time())
                    self.registry.last_data_recv_ts = time.time()
                    self.last_data_request_sent_timestamps[event_ticker] = data_sent_timestamp

    async def get_market_data(self, client):
        while True:
            for event_ticker in self.event_tickers:
                asyncio.create_task(self._get_data(client, event_ticker))
            await asyncio.sleep(1.0 / self.data_requests_per_second_per_event)

    async def _place_order(self, client, ticker, order_type, action, side, amount, yes_price, no_price, expiration_ts, sell_position_floor=None, buy_max_cost=None):
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
            
            response = await client.create_order(**order_params)
            print(action, amount, "shares of", ticker, side)
            print(response)
            print(time.time())

    def buy_yes_market_order(self, client, ticker, amount):
        asyncio.create_task(self._place_order(client=client, ticker=ticker, 
                                              order_type="market", action="buy",
                                              side="yes", amount=amount,
                                              yes_price=None, no_price=None, 
                                              expiration_ts=None))
    
    def buy_no_market_order(self, client, ticker, amount):
        asyncio.create_task(self._place_order(client=client, ticker=ticker, 
                                              order_type="market", action="buy",
                                              side="no", amount=amount,
                                              yes_price=None, no_price=None, 
                                              expiration_ts=None))
        
    def sell_yes_market_order(self, client, ticker, amount):
        asyncio.create_task(self._place_order(client=client, ticker=ticker, 
                                              order_type="market", action="sell",
                                              side="yes", amount=amount,
                                              yes_price=None, no_price=None, 
                                              expiration_ts=None))
        
    def sell_no_market_order(self, client, ticker, amount):
        asyncio.create_task(self._place_order(client=client, ticker=ticker, 
                                              order_type="market", action="sell",
                                              side="no", amount=amount,
                                              yes_price=None, no_price=None, 
                                              expiration_ts=None))
        
    def buy_yes_limit_order(self, client, ticker, amount, price, expiration_ts=None):
        asyncio.create_task(self._place_order(client=client, ticker=ticker, 
                                              order_type="limit", action="buy",
                                              side="yes", amount=amount,
                                              yes_price=price, no_price=None, 
                                              expiration_ts=expiration_ts))
        
    def buy_no_limit_order(self, client, ticker, amount, price, expiration_ts=None):
        asyncio.create_task(self._place_order(client=client, ticker=ticker, 
                                              order_type="limit", action="buy",
                                              side="no", amount=amount,
                                              yes_price=None, no_price=price, 
                                              expiration_ts=expiration_ts))
        
    def sell_yes_limit_order(self, client, ticker, amount, price, expiration_ts=None):
        asyncio.create_task(self._place_order(client=client, ticker=ticker, 
                                              order_type="limit", action="sell",
                                              side="yes", amount=amount,
                                              yes_price=price, no_price=None, 
                                              expiration_ts=expiration_ts))
        
    def sell_no_limit_order(self, client, ticker, amount, price, expiration_ts=None):
        asyncio.create_task(self._place_order(client=client, ticker=ticker, 
                                              order_type="limit", action="sell",
                                              side="no", amount=amount,
                                              yes_price=None, no_price=price, 
                                              expiration_ts=expiration_ts))
        
    async def get_volume(self, client, market_ticker, side):
        async with self.volume_request_semaphore:
            result = await client.get_orderbook(ticker=market_ticker, depth=1)
            return result["orderbook"][side][-1][1]
    
    @abstractmethod
    async def strategy(self, client):
        pass

    async def loop(self):
        async with ExchangeClient(self.api_base, self.key_id, self.private_key) as client:
            await asyncio.gather(self.get_market_data(client), self.strategy(client))

    def run(self):
        asyncio.run(self.loop())

    # def get_balance(self):
    #     return usd(self.exchange_client.get_balance()["balance"])

    #     print(self.exchange_client.get_orderbook(ticker=market["ticker"], depth=1), market["yes_sub_title"])




        #     if market["yes_bid"] >= self.bid_threshold and market["no_bid"] >= self.bid_threshold:
        #         market_idx = cut_down(filter_digits(market[f'{self.side}_sub_title']))
        #         self.above_market_asks[market_idx] = market[f'{self.side}_ask']  
        #         self.above_market_tickers[market_idx] = market["ticker"]
            
        #     out[]

#     def find_min_orders_and_fees(self, tickers):
#         side = "no" if self.side == "yes" else "yes"
#         minimum_orders = float("inf")
#         total_price = 0
#         for ticker, price in tickers:
#             #print(ticker, price, self.exchange_client.get_orderbook(ticker=ticker, depth=32)["orderbook"][side][-1][1])
#             minimum_orders = min(minimum_orders, self.exchange_client.get_orderbook(ticker=ticker, depth=32)["orderbook"][side][-1][1])
#             total_price += price
#         print(total_price)
#         minimum_orders = min(min(minimum_orders, self.exchange_client.get_balance()["balance"]//total_price), 100)

#         total_fees = 0
#         for ticker, price in tickers:
#             total_fees += calc_fees(price, minimum_orders)

#         return minimum_orders, total_fees
    
#     def make_orders(self, orders_to_make):
#         #orders = {"orders" : []}
#         for ticker, amount in orders_to_make:
#             order_params = {'ticker':ticker,
#                     'client_order_id':str(uuid.uuid4()),
#                     'type':'market',
#                     'action':'buy',
#                     'side':self.side,
#                     'count':amount,
#                     'yes_price':None, # yes_price = 100 - no_price
#                     'no_price':None, # no_price = 100 - yes_price
#                     'expiration_ts':None,
#                     'sell_position_floor':None,
#                     'buy_max_cost':None}
            
#             #print(order_params)
#             #orders["orders"].append(order_params)
#             self.exchange_client.create_order(**order_params)
#             print(f'Bought {amount} shares of {ticker}')
#         self.order_made = True
#     #finding price discrepancies
#     def arb_search(self):
#         raise NotImplementedError
    
#     #run
#     def run(self):
#         raise NotImplementedError

# class SpreadCover(Arbitrage):
#     def __init__(self, api_base, key_id, private_key, above_event, between_event, side):
#         super().__init__(api_base, key_id, private_key, above_event, between_event, side)

#     def arb_search(self):
#         max_profit = 0
#         max_arb = None

#         under_price = 0
#         curr_between_asks = []
#         for i in range(40):
#             if self.between_market_asks[i] and self.above_market_asks[i]:
#                 under_price += self.between_market_asks[i]
#                 curr_between_asks.append((self.between_market_tickers[i], self.between_market_asks[i]))
#                 if under_price+self.above_market_asks[i] < 100:
#                     minimum_orders, total_fees = self.find_min_orders_and_fees(curr_between_asks+[(self.above_market_tickers[i], self.above_market_asks[i])])
#                     if minimum_orders*(100-under_price-self.above_market_asks[i]) > total_fees:
#                         if minimum_orders*(100-under_price-self.above_market_asks[i])-total_fees > max_profit:
#                             arb = [(self.above_market_tickers[i], minimum_orders)]
#                             for between_ticker, _ in curr_between_asks:
#                                 arb.append((between_ticker, minimum_orders))
#                             max_arb = arb
#                             max_profit = minimum_orders*(100-under_price-self.above_market_asks[i])-total_fees
#                             print(f'Profitable trade found. Estmated profit: {minimum_orders*(100-under_price-self.above_market_asks[i])-total_fees}')
        
#         return max_arb
    

