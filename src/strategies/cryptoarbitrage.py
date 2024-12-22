import asyncio
import uuid
import math
import time
from utils.KalshiClient import ExchangeClient
from datacollection.DataListeners import EventListener
from utils.util import filter_digits, get_month_day, get_hour
from datetime import datetime
import pandas as pd

class CryptoArbitrage:
    def __init__(self, api_base, key_id: str, private_key, threshold, prod, mode, crypto, block_size):
        self.ticker = crypto
        month, day = get_month_day()
        hour = get_hour()
        self.above_ticker = "KX" + self.ticker + "D-24" + month.upper() + str(day) + hour
        self.range_ticker = "KX" + self.ticker + "-24" + month.upper() + str(day) + hour
        self.block_size = block_size
        self.prod = prod
        self.mode = mode

        self.exchange_client = ExchangeClient(api_base, key_id, private_key)
        self.above_event = EventListener(exchange_client=self.exchange_client, private_key = private_key, key_id=key_id, event_ticker=self.above_ticker)
        self.range_event = EventListener(exchange_client=self.exchange_client, private_key = private_key, key_id=key_id, event_ticker=self.range_ticker)

        self.markets_arr = [{"above": None, "range": None} for _ in range(100)]
        self.balance = 0
        self.lock = asyncio.Lock()  # Lock for exclusive access to make_orders
        self.profit_threshold = threshold

    def set_markets(self):
        above_markets = [m["ticker"] for m in self.exchange_client.get_event(self.above_ticker)["markets"]]
        range_markets = [m["ticker"] for m in self.exchange_client.get_event(self.range_ticker)["markets"]]
        above_dict, range_dict = {}, {}
        min_idx = float("inf")
        max_idx = -float("inf")

        for ticker in above_markets:
            idx = int(math.ceil(filter_digits(ticker.split("-")[-1])) // self.block_size)
            above_dict[idx] = ticker
            min_idx = min(min_idx, idx)
            max_idx = max(max_idx, idx)

        for ticker in range_markets:
            idx = int((math.ceil(filter_digits(ticker.split("-")[-1])) - (self.block_size/2)) // self.block_size)
            range_dict[idx] = ticker
            min_idx = min(min_idx, idx)
            max_idx = max(max_idx, idx)

        for i in range(min_idx, max_idx+1):
            if i in above_dict:
                self.markets_arr[i - min_idx]["above"] = above_dict[i]
            if i in range_dict:
                self.markets_arr[i - min_idx]["range"] = range_dict[i]

        print("Markets set!")

    def get_markets(self):
        return self.above_event.get_markets() + self.range_event.get_markets()

    def make_orders(self, orders_to_make):
        #async with self.lock:  # Ensure only one make_orders execution
        if not orders_to_make:
            print("No opportunities found.")
            return

        # Function to generate order parameters
        def get_order(ticker, amount, side):
            return {'ticker':ticker,
                    'client_order_id':str(uuid.uuid4()),
                    'type':'market',
                    'action':'buy',
                    'side':side,
                    'count':5,
                    'expiration_ts':None,
                    'sell_position_floor':None,
                    'buy_max_cost':None}
            
        for ticker, amount, side in orders_to_make:
            order = get_order(ticker, amount, side)
            print(order)
            self.exchange_client.create_order(**order)

        #await asyncio.gather(*tasks)

        # Update balance after all orders
        self.balance = self.exchange_client.get_balance()["balance"]
        print(f"Current balance: {self.balance}")
        time.sleep(0.5)


    async def scan(self, mode: str):
        print("Starting scan...")
        try:
            while True:
                if self.lock.locked():  # Pause scanning if make_orders is running
                    await asyncio.sleep(0.1)
                    continue

                for i in range(99):
                    if not (self.markets_arr[i]["above"] and self.markets_arr[i]["range"] and self.markets_arr[i + 1]["above"]):
                        continue

                    if mode == "sbb":
                        above_sell, above_sell_price = await self.above_event.get_ask(self.markets_arr[i]["above"], "no")
                        above_buy, above_buy_price = await self.above_event.get_ask(self.markets_arr[i + 1]["above"], "yes")
                        range_buy, range_buy_price = await self.range_event.get_ask(self.markets_arr[i]["range"], "yes")

                        orders = min(above_sell, above_buy, range_buy)
                        if self.prod:
                            orders = min(orders, self.balance//(above_sell_price + above_buy_price + range_buy_price))
                        if orders > 0 and above_sell_price + above_buy_price + range_buy_price < 100:
                            print(f"SBB Arbitrage found on {self.ticker} at {datetime.now().strftime("%H:%M:%S")}. Profit: {100 - (above_sell_price + above_buy_price + range_buy_price)}, Orders: {orders}")
                            if 100 - (above_sell_price + above_buy_price + range_buy_price) >= self.profit_threshold:
                                if self.prod:
                                    print("Making orders")
                                    response = await self.make_orders([
                                        (self.markets_arr[i]["above"], orders, "no"),
                                        (self.markets_arr[i+1]["above"], orders, "yes"),
                                        (self.markets_arr[i]["range"], orders, "yes"),
                                    ])
                                    print(response.json())
                                    print("Orders made")
                                    break

                    elif mode == "bss":
                        above_buy, above_buy_price = await self.above_event.get_ask(self.markets_arr[i]["above"], "yes")
                        above_sell, above_sell_price = await self.above_event.get_ask(self.markets_arr[i + 1]["above"], "no")
                        range_sell, range_sell_price = await self.range_event.get_ask(self.markets_arr[i]["range"], "no")

                        orders = min(above_buy, above_sell, range_sell)
                        if self.prod:
                            orders = min(orders, self.balance//(above_buy_price + above_sell_price + range_sell_price))
                        if orders > 0 and (above_buy_price + above_sell_price + range_sell_price) < 200:
                            print(f"BSS Arbitrage found on {self.ticker} at {datetime.now().strftime("%H:%M:%S")}. Profit: {200 - (above_buy_price + above_sell_price + range_sell_price)}, Orders: {orders}")
                            if 200 - (above_buy_price + above_sell_price + range_sell_price) >= self.profit_threshold:
                                if self.prod:
                                    response = await self.make_orders([
                                        (self.markets_arr[i]["above"], orders, "yes"),
                                        (self.markets_arr[i+1]["above"], orders, "no"),
                                        (self.markets_arr[i]["range"], orders, "no"),
                                    ])
                                    print(response)
                                    break

                await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Scan error: {e}")

    async def run(self):
        self.set_markets()
        self.balance = self.exchange_client.get_balance()["balance"]

        above_task = asyncio.create_task(self.above_event.start_listen())
        range_task = asyncio.create_task(self.range_event.start_listen())
        scan_task = asyncio.create_task(self.scan(mode=self.mode))

        print(f"Initialization complete. Starting balance: {self.balance}")

        try:
            while True:
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            print("Main loop cancelled. Cleaning up...")
        finally:
            above_task.cancel()
            range_task.cancel()
            scan_task.cancel()
            try:
                await above_task
                await range_task
                await scan_task
            except asyncio.CancelledError:
                pass

class BTCArbitrage(CryptoArbitrage):
    def __init__(self, api_base, key_id, private_key, threshold, mode, prod):
        super().__init__(api_base=api_base, key_id=key_id, private_key=private_key, threshold=threshold, prod=prod, mode = mode, crypto="BTC", block_size=500)

class ETHArbitrage(CryptoArbitrage):
    def __init__(self, api_base, key_id, private_key, threshold, mode, prod):
        super().__init__(api_base=api_base, key_id=key_id, private_key=private_key, threshold=threshold, prod=prod, mode = mode, crypto="ETH", block_size=40)
