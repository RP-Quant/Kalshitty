import time

class Registry:
    def __init__(self) -> None:
        self.data = {}
        self.balance = 0
        self.btc_price = 0
        self.last_data_recv_ts = time.time()
        self.last_btc_recv_ts = time.time()
        self.freshness_threshold = 0.05 # data should be received 50 ms ago max to be fresh
        self.btc_recv_threshold = 1.1

        # data model:
        # {
        #   event_ticker: {
        #       market_yes_subtitle: {
        #           "yes_price": int,
        #           "no_price": int, 
        #           "yes_volume": int,
        #           "no_volume": int,
        #           "unique_ticker": str
        #       }
        # }

        # market price for buying a yes is (100 - no_price) -> if you want to sell to the best no, you buy the yes at a price of (100 - no_price)
        # market price for buying a no is (100 - yes_price) -> if you want to sell to the best yes, you buy the no at a price of (100 - yes_price)

    def add_events(self, events):
        for event in events:
            if event not in self.data:
                self.data[event] = {}

    # run this method before accessing data, also make sure to use mutex before accessing data
    def check_data_freshness(self):
        if time.time() - self.last_data_recv_ts > self.freshness_threshold:
            return False
        return True
    
    # run this method before accessing btc price, also make sure to use mutex before accessing price
    def check_btc_freshness(self):
        if time.time() - self.last_btc_recv_ts > self.btc_recv_threshold:
            return False
        return True
