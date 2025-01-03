from base_strategy import BaseStrategy
from registry import Registry
import asyncio
import time
from utils.util import calc_fees, get_digits
from utils.KalshiClientV3 import ExchangeClient
import yfinance as yf
import numpy as np
from scipy.stats import norm
from datetime import datetime
from math import ceil

class BSMStrategy(BaseStrategy):
    def __init__(self, registry: Registry, event_ticker: str, client: ExchangeClient, registry_mutex: asyncio.Lock):
        super().__init__(registry, [event_ticker], client, registry_mutex)
        self.bsm_ticker = event_ticker
        
        self.set_up = False
        self.market_indices = []
        self.market_index_to_ticker = {} # index int -> actual market ticker

        self.balance = 200
        self.total_spent = 0

        self.volatility = 0
        self.trade_amount = ceil(0.01 * self.balance)

        self.vol_multiplier = 1.2

    def threshold(self, minute):
        return 15 - minute / 8
    
    def get_spend_limit(self, minute):
        multiplier = ((minute ** 2) / 100 + 5) / 100
        return multiplier * self.balance
        
    async def run(self):
        await asyncio.sleep(10) # probably necessary because some weird race condition dont touch
        first = False

        while True:
            if not first:
                print("starting bsm checking task")
                first = True

            async with self.mutex:
                # Your strategy here

                if not self.set_up:
                    if self.bsm_ticker not in self.registry.data:
                        continue
                    if len(self.registry.data[self.bsm_ticker]) != 0:
                        for market in self.registry.data[self.bsm_ticker]:
                            first_num_str = market.split(" ")[0]
                            market_idx = get_digits(first_num_str)

                            self.market_indices.append(market_idx)
                            self.market_index_to_ticker[market_idx] = market

                        btc = yf.Ticker("BTC-USD")
                        data = btc.history(period="5d", interval="1m")
                        data["Returns"] = np.log(data["Close"] / data["Close"].shift(1))
                        data = data.dropna()

                        # past_hour_volume = sum(data.tail(60)["Volume"].values)

                        # N = len(data)
                        self.volatility = data["Returns"].std() * self.vol_multiplier

                        self.set_up = True

                else:
                    if self.registry.check_btc_freshness() and self.registry.check_data_freshness():
                        # best_orders = {
                        #     "profit": 0,
                        #     "volume": 0,
                        #     "cost": 0,
                        #     "orders": {} # ticker: {"side": side}
                        # }
                        
                        # #profit, ("no"/"yes", ticker1), ("no"/"yes", ticker2), ("no"/"yes", ticker3)

                        btc_price = self.registry.btc_price

                        for market_line in self.market_indices:
                            market_ticker = self.market_index_to_ticker[market_line]
                            market_unique_ticker = self.registry.data[self.bsm_ticker][market_ticker]["unique_ticker"]

                            yes_ask_price = self.registry.data[self.bsm_ticker][market_ticker]["yes_ask_price"]
                            no_ask_price = self.registry.data[self.bsm_ticker][market_ticker]["no_ask_price"]
                            yes_ask_volume = self.registry.data[self.bsm_ticker][market_ticker]["yes_ask_volume"]
                            no_ask_volume = self.registry.data[self.bsm_ticker][market_ticker]["no_ask_volume"]

                            yes_bid_price = self.registry.data[self.bsm_ticker][market_ticker]["yes_bid_price"]
                            no_bid_price = self.registry.data[self.bsm_ticker][market_ticker]["no_bid_price"]
                            yes_bid_volume = self.registry.data[self.bsm_ticker][market_ticker]["yes_bid_volume"]
                            no_bid_volume = self.registry.data[self.bsm_ticker][market_ticker]["no_bid_volume"]

                            if yes_ask_price is None or \
                                no_ask_price is None or \
                                yes_ask_volume is None or \
                                no_ask_volume is None or \
                                yes_bid_price is None or \
                                no_bid_price is None or \
                                yes_bid_volume is None or \
                                no_bid_volume is None:

                                continue
                                
                            # tau in minutes

                            curr_minute = datetime.now().minute
                            tau = 60 - curr_minute

                            d1 = (np.log(btc_price / market_line) + (self.volatility ** 2)/2 * tau) / (self.volatility * np.sqrt(tau))
                            d2 = d1 - self.volatility * np.sqrt(tau)

                            call_price = norm.cdf(d2)
                            put_price = (1 - call_price) * 100
                            call_price *= 100 

                            print(market_line, no_ask_price, put_price, btc_price, "buy no")
                            print(self.get_spend_limit(curr_minute), self.total_spent)

                            if call_price - yes_ask_price > self.threshold(curr_minute) and self.total_spent < self.get_spend_limit(curr_minute):
                                amount = min(yes_ask_volume, self.trade_amount)
                                print(market_line, yes_ask_price, call_price, btc_price, "buy yes", amount)

                                fees = calc_fees(yes_ask_price, amount)
                                self.total_spent += yes_ask_price * amount / 100 + fees

                                self.buy_yes_market_order(market_unique_ticker, amount)
                                print("current spend and limits", self.total_spent, self.get_spend_limit(curr_minute), self.threshold(curr_minute))
                                await asyncio.sleep(10)

                            elif put_price - no_ask_price > self.threshold(curr_minute) and self.total_spent < self.get_spend_limit(curr_minute):
                                amount = min(no_ask_volume, self.trade_amount)
                                print(market_line, no_ask_price, put_price, btc_price, "buy no", amount)

                                fees = calc_fees(no_ask_price, amount)
                                self.total_spent += no_ask_price * amount / 100 + fees

                                self.buy_no_market_order(market_unique_ticker, amount)
                                print("current spend and limits", self.total_spent, self.get_spend_limit(curr_minute), self.threshold(curr_minute))
                                await asyncio.sleep(10)

            await asyncio.sleep(0.01)