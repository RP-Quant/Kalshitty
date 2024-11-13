from KalshiClientsBaseV2ApiKey import ExchangeClient
from util import filter_digits, calc_fees, cut_down
import uuid
import time

#base arbtrage class
class Arbitrage:
    def __init__(self, api_base:str, key_id:str, private_key, above_event:str, between_event:str, side:str):
        #exchange client creation
        self.exchange_client = ExchangeClient(api_base, key_id, private_key)

        #threshold for probable markets
        self.bid_threshold = 2

        #buy yes or no
        self.side = side

        #event tickers
        self.above_event_ticker = above_event
        self.between_event_ticker = between_event

        #arrays to hold the asks for each specific market
        self.above_market_asks = [None]*40
        self.between_market_asks = [None]*40

        #arrays to hold the tickers for each specific market
        self.above_market_tickers = [None]*40
        self.between_market_tickers = [None]*40

        #testing
        self.order_made = False

    #getting the price points for each range on both markets
    def get_ranges(self):
        above_event = self.exchange_client.get_event(self.above_event_ticker)
        between_event = self.exchange_client.get_event(self.between_event_ticker)

        for market in above_event["markets"]:
            if market["yes_bid"] >= self.bid_threshold and market["no_bid"] >= self.bid_threshold:
                market_idx = cut_down(filter_digits(market[f'{self.side}_sub_title']))
                self.above_market_asks[market_idx] = market[f'{self.side}_ask']  
                self.above_market_tickers[market_idx] = market["ticker"]

        for market in between_event["markets"]:
            if market["yes_bid"] >= self.bid_threshold and market["no_bid"] >= self.bid_threshold:
                if "above" in market[f'{self.side}_sub_title']:
                    continue

                market_idx = cut_down(filter_digits(market[f'{self.side}_sub_title'][-10:]))

                self.between_market_asks[market_idx] = market[f'{self.side}_ask']
                self.between_market_tickers[market_idx] = market["ticker"]

    def find_min_orders_and_fees(self, tickers):
        side = "no" if self.side == "yes" else "yes"
        minimum_orders = float("inf")
        total_price = 0
        for ticker, price in tickers:
            #print(ticker, price, self.exchange_client.get_orderbook(ticker=ticker, depth=32)["orderbook"][side][-1][1])
            minimum_orders = min(minimum_orders, self.exchange_client.get_orderbook(ticker=ticker, depth=32)["orderbook"][side][-1][1])
            total_price += price
        #print(total_price)
        minimum_orders = min(min(minimum_orders, self.exchange_client.get_balance()["balance"]//total_price), 50)

        total_fees = 0
        for ticker, price in tickers:
            total_fees += calc_fees(price, minimum_orders)

        return minimum_orders, total_fees
    
    def make_orders(self, orders_to_make):
        orders = {"orders":[]}
        if not orders_to_make:
            print("No opportunities found")
            return
        
        for ticker, amount in orders_to_make:
            order_params = {'ticker':ticker,
                    'client_order_id':str(uuid.uuid4()),
                    'type':'market',
                    'action':'buy',
                    'side':self.side,
                    'count':amount,
                    'yes_price':None, # yes_price = 100 - no_price
                    'no_price':None, # no_price = 100 - yes_price
                    'expiration_ts':None,
                    'sell_position_floor':None,
                    'buy_max_cost':None}
            
            #print(order_params)
            orders["orders"].append(order_params)
            self.exchange_client.create_order(**order_params)
            print(f'Bought {amount} shares of {ticker}')
        #self.exchange_client.batch_create_orders(orders)
        self.order_made = True
    #finding price discrepancies
    def arb_search(self):
        raise NotImplementedError
    
    #run
    def run(self):
        raise NotImplementedError

class SpreadCover(Arbitrage):
    def __init__(self, api_base, key_id, private_key, above_event, between_event, side):
        super().__init__(api_base, key_id, private_key, above_event, between_event, side)

    def arb_search(self):
        max_profit = 0
        max_arb = None

        under_price = 0
        curr_between_asks = []
        for i in range(40):
            if self.between_market_asks[i] and self.above_market_asks[i]:
                under_price += self.between_market_asks[i]
                curr_between_asks.append((self.between_market_tickers[i], self.between_market_asks[i]))
                if under_price+self.above_market_asks[i] < 100:
                    minimum_orders, total_fees = self.find_min_orders_and_fees(curr_between_asks+[(self.above_market_tickers[i], self.above_market_asks[i])])
                    if minimum_orders*(100-under_price-self.above_market_asks[i]) > total_fees:
                        if minimum_orders*(100-under_price-self.above_market_asks[i])-total_fees > max_profit:
                            arb = [(self.above_market_tickers[i], minimum_orders)]
                            for between_ticker, _ in curr_between_asks:
                                arb.append((between_ticker, minimum_orders))
                            #max_arb = arb
                            #max_profit = minimum_orders*(100-under_price-self.above_market_asks[i])-total_fees
                            print(f'Profitable trade found. Estmated profit: {minimum_orders*(100-under_price-self.above_market_asks[i])-total_fees}')
                            return arb
        
        return []
    
    def run(self):
        while not self.order_made:
            self.get_ranges()
            arb = self.arb_search()
            print(arb)
            self.make_orders(arb)
            time.sleep(0.1)
                        
