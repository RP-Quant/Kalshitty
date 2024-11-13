from KalshiClientsBaseV2ApiKey import ExchangeClient
from config import KEY_ID, BTC_PRICE_TICKER, BTC_PRICE_RANGE_TICKER
from util import load_private_key_from_file, filter_digits
from pprint import pprint
from bisect import bisect_left, bisect_right

class Arbitrage:
    def __init__(self, api_base, key_id, private_key):
        self.exchange_client = ExchangeClient(api_base, key_id, private_key)
        self.bid_threshold = 2
        self.market_tickers = {}

    def get_ranges(self):
        btc_price = self.exchange_client.get_event(BTC_PRICE_TICKER)
        btc_range_price = self.exchange_client.get_event(BTC_PRICE_RANGE_TICKER)

        btc_prices = {}
        btc_range_prices = {}

        for market in btc_price["markets"]:
            if market["yes_bid"] >= self.bid_threshold and market["no_bid"] >= self.bid_threshold:
                btc_prices[filter_digits(market["yes_sub_title"])] = market["yes_ask"]
                self.market_tickers[filter_digits(market["yes_sub_title"])] = market["ticker"]

        for market in btc_range_price["markets"]:
            if market["yes_bid"] >= self.bid_threshold and market["no_bid"] >= self.bid_threshold:
                btc_range_prices[filter_digits(market["yes_sub_title"][-10:])] = market["yes_ask"]
                self.market_tickers[filter_digits(market["yes_sub_title"][-10:])] = market["ticker"]
        #print(self.market_tickers)
        return btc_prices, btc_range_prices
    
    def arb_search(self):
        btc_prices, btc_range_prices = self.get_ranges()
        #pprint(btc_prices)
        #pprint(btc_range_prices)
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
                print(f'arbitrage found at {k}: upper: {v}, lower: {prefix_sum[position]}. Projected profit margin: {100-(v+prefix_sum[position])}')
                arbs.append((self.market_tickers[k], [self.market_tickers[range_ends[position-i-1]] for i in range(position)]))

        return arbs
    
    def parse_orderbook(self):
        arbs = self.arb_search()
        print(arbs)
        above_orders = {}
        below_orders = {}

        for above, belows in arbs:
            above_orders[above] = self.exchange_client.get_orderbook(ticker=above, depth=2)
            below_orders = {below : self.exchange_client.get_orderbook(ticker=below, depth=2) for below in belows}

        return above_orders, below_orders
        

private_key = load_private_key_from_file("src/kalshi.key")
api_base = "https://api.elections.kalshi.com/trade-api/v2"

arb = Arbitrage(api_base=api_base, key_id=KEY_ID, private_key=private_key)

print(arb.parse_orderbook())