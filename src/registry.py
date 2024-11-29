import time

class Registry:
    def __init__(self) -> None:
        self.data = {}
        self.last_data_recv_ts = None
        self.freshness_threshold = 0.5 # data should be received 0.5 seconds ago max to be fresh

        # data model:
        # {event_ticker: {
        #   market_yes_subtitle: {
        #       yes_bid_price: int, 
        #       no_bid_price: int, 
        #       yes_bid_volume: int,
        #       no_bid_volume: int,
        #       previous_price: int
        #   }
        # }

    def add_events(self, events):
        for event in events:
            if event not in self.data:
                self.data[event] = {}

    # run this method before accessing data, also make sure to use mutex before accessing data
    def check_data_freshness(self):
        if time.time() - self.last_data_recv_ts > self.freshness_threshold:
            return False
        return True
