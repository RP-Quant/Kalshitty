self.ticker = crypto
        month, day = get_month_day()
        self.above_ticker = "KX" + self.ticker + "D-" + month + str(day) + "17"
        self.range_ticker = "KX" + self.ticker + "-" + month + str(day) + "17"
        print(self.above_ticker, self.range_ticker)
        self.block_size = block_size
        self.prod = prod

        self.exchange_client = ExchangeClient(api_base, key_id, private_key)
        self.above_event = Event(self.above_ticker, self.exchange_client)
        self.range_event = Event(self.range_ticker, self.exchange_client)