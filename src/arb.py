from KalshiClientsBaseV2ApiKey import ExchangeClient
from config import KEY_ID, BTC_PRICE_TICKER, BTC_PRICE_RANGE_TICKER
from util import load_private_key_from_file, filter_digits, calc_fees
from pprint import pprint
from bisect import bisect_left
import uuid

class Arbitrage:
    def __init__(self, api_base, key_id, private_key):
        self.exchange_client = ExchangeClient(api_base, key_id, private_key)
        self.bid_threshold = 2
        self.above_tickers = {}
        self.below_tickers = {}

    #getting the price points for each range on both markets
    def get_ranges(self):
        btc_price = self.exchange_client.get_event(BTC_PRICE_TICKER)
        btc_range_price = self.exchange_client.get_event(BTC_PRICE_RANGE_TICKER)

        btc_prices = {}
        btc_range_prices = {}

        for market in btc_price["markets"]:
            if market["yes_bid"] >= self.bid_threshold and market["no_bid"] >= self.bid_threshold:
                btc_prices[filter_digits(market["yes_sub_title"])] = market["yes_ask"]  
                self.above_tickers[filter_digits(market["yes_sub_title"])] = market["ticker"]

        for market in btc_range_price["markets"]:
            if market["yes_bid"] >= self.bid_threshold and market["no_bid"] >= self.bid_threshold:
                btc_range_prices[filter_digits(market["yes_sub_title"][-10:])] = market["yes_ask"]
                self.below_tickers[filter_digits(market["yes_sub_title"][-10:])] = market["ticker"]
        #pprint(self.above_tickers)
        #pprint(self.below_tickers)
        return btc_prices, btc_range_prices
    
    #searching for price discrepancies between two markets to arb
    def arb_search(self):
        btc_prices, btc_range_prices = self.get_ranges()
        # print("above _ prices")
        # pprint(btc_prices)
        # print("between _ and _ prices")
        # pprint(btc_range_prices)
        prefix_sum = [0]
        range_ends = []
        for k, v in btc_range_prices.items():
            range_ends.append(k)
            prefix_sum.append(prefix_sum[-1]+v)
        
        arbs = []

        for k, v in btc_prices.items():
            position = bisect_left(range_ends, k)
            if position == 0:
                continue
            elif position == len(range_ends):
                if k - range_ends[-1] > 1:
                    continue

            if v + prefix_sum[position] < 100:
                total_fees = calc_fees(v/100)
                for i in range(position):
                    total_fees += calc_fees(btc_range_prices[range_ends[i]]/100)

                if 1:#total_fees < 100-(v+prefix_sum[position]):
                    print(f'arbitrage found at {k}: upper: {v}, lower: {prefix_sum[position]}. Projected profit margin: {100-(v+prefix_sum[position])}')
                    arbs.append((self.above_tickers[k], [self.below_tickers[range_ends[position-i-1]] for i in range(position)]))

        return arbs
    
    #getting the amount of orders for both
    def parse_orderbook(self):
        arbs = self.arb_search()
        pprint(arbs)
        orders = []

        for above, belows in arbs:
            above_asks = self.exchange_client.get_orderbook(ticker=above, depth=32)["orderbook"]["no"][0][-1]
            min_below_asks = min([self.exchange_client.get_orderbook(ticker=below, depth=32)["orderbook"]["no"][0][-1] for below in belows])
            final_orders = min(above_asks, min_below_asks)
            orders.append((above, final_orders))
            for below in belows:
                orders.append((below, final_orders))

        return orders
        

private_key = load_private_key_from_file("src/kalshi.key")
api_base = "https://api.elections.kalshi.com/trade-api/v2"

arb = Arbitrage(api_base=api_base, key_id=KEY_ID, private_key=private_key)

pprint(arb.parse_orderbook())