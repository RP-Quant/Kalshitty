from KalshiClientsBaseV2ApiKey import ExchangeClient
from util import filter_digits, calc_fees, cut_down
import uuid
import time
from pprint import pprint
import csv

#base arbtrage class
class Arbitrage:
    def __init__(self, api_base:str, key_id:str, private_key, above_event:str, between_event:str, side:str):
        #exchange client creation
        self.exchange_client = ExchangeClient(api_base, key_id, private_key)

        #threshold for probable markets
        self.bid_threshold = 5

        #buy yes or no
        self.side = side

        #event tickers
        self.above_event_ticker = above_event
        self.between_event_ticker = between_event

        #arrays to hold the asks for each specific market
        self.above_market_asks = [None]*100
        self.above_market_bids = [None]*100
        self.between_market_asks = [None]*100
        self.between_market_bids = [None]*100

        #arrays to hold the tickers for each specific market
        self.above_market_tickers = [None]*100
        self.between_market_tickers = [None]*100

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
                self.above_market_bids[market_idx] = market[f'{self.side}_bid']
                self.above_market_tickers[market_idx] = market["ticker"]

        for market in between_event["markets"]:
            #print(market["subtitle"], market["yes_bid"], market["no_bid"])
            if market["yes_bid"] >= self.bid_threshold and market["no_bid"] >= self.bid_threshold:
                if "above" in market[f'{self.side}_sub_title'] or "below" in market[f'{self.side}_sub_title']:
                    continue

                market_idx = cut_down(filter_digits(market[f'{self.side}_sub_title'][-10:]))
                self.between_market_asks[market_idx] = market[f'{self.side}_ask']
                self.between_market_bids[market_idx] = market[f'{self.side}_bid']
                self.between_market_tickers[market_idx] = market["ticker"]

    def find_min_orders_and_fees(self, tickers):
        side = "no" if self.side == "yes" else "yes"
        minimum_orders = float("inf")
        total_price = 0
        for ticker, price in tickers:
            #print(ticker, price, self.exchange_client.get_orderbook(ticker=ticker, depth=32)["orderbook"][side][-1][1])
            minimum_orders = min(minimum_orders, self.exchange_client.get_orderbook(ticker=ticker, depth=1)["orderbook"][side][-1][1])
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
        # TODO: CHANGE THIS TO AMOUNT ONCE DONE TESTING
        for ticker, amount, side in orders_to_make:
            order_params = {'ticker':ticker,
                    'client_order_id':str(uuid.uuid4()),
                    'type':'market',
                    'action':'buy',
                    'side':side,
                    'count':1,#amount,
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

class Mint(Arbitrage):
    def __init__(self, api_base, key_id, private_key, above_event, between_event, side):
        super().__init__(api_base, key_id, private_key, above_event, between_event, side)

    def arb_search(self):
        sell1, buy1, sell2 = None, None, None
        max_profit = -float('inf')
        for i in range(39):
            if not self.above_market_asks[i] or not self.above_market_bids[i+1] or not self.between_market_bids[i+1]:
                #print(self.above_market_asks[i], self.above_market_bids[i+1], self.between_market_bids[i+1])
                continue

            A = 100-self.above_market_bids[i+1]
            B = self.above_market_asks[i]
            C = 100-self.between_market_bids[i+1]
            #print(A, B, C)
            if 200 > C+B+A:
                print(A, B, C)
                #print(self.above_market_tickers[i+1], self.above_market_tickers[i], self.between_market_tickers[i+1])
                print(f'Opportunity found, profit: {200-(C+B+A)}')
                if 200-(C+B+A) > max_profit and 200-(C+B+A) > 2:
                    max_profit = 200-(C+B+A)
                    sell1, buy1, sell2 = self.above_market_tickers[i+1], self.above_market_tickers[i], self.between_market_tickers[i+1]
        
        if sell1:
            print(sell1, buy1, sell2)
            _, _, s = self.get_min_orders(sell1, buy1, sell2)
            return [(sell1, s, "no"), (buy1, s, "yes"), (sell2, s, "no")]
        return []

    def get_min_orders(self, A, B, C):
        A_price, A_orders = self.exchange_client.get_orderbook(A, 1)["orderbook"]["yes"][-1]
        B_price, B_orders = self.exchange_client.get_orderbook(B, 1)["orderbook"]["no"][-1]
        C_price, C_orders = self.exchange_client.get_orderbook(C, 1)["orderbook"]["yes"][-1]

        print(self.exchange_client.get_orderbook(A, 1)["orderbook"]["yes"])

        min_orders = min(A_orders, B_orders, C_orders)#self.exchange_client.get_balance()["balance"]//(a+b+c))
        total_cost = calc_fees(A_price, min_orders) + calc_fees(B_price, min_orders) + calc_fees(C_price, min_orders)
        total_profit = min_orders * (200-(A_price+B_price+C_price))

        print(f'Total cost: {total_cost}, total_profit: {total_profit}, shares availible: {min_orders}')
        return total_cost, total_profit, min_orders



    def run(self):
        print("Starting...")
        while 1:
            self.get_ranges()
            starttime = time.time()
            arbs = self.arb_search()
            if arbs:
                print(arbs)
                self.make_orders(arbs)
                print("making orders took:", str(time.time() - starttime), "seconds, from getting data to placing order")
                time.sleep(10)


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
                        
