import asyncio
import uuid
import math
import time
from KalshiClientsBaseV2ApiKey import ExchangeClient
from marketdata import Event
from util import load_private_key_from_file, filter_digits, get_month_day
from config import KEY_ID, API_BASE
from datetime import datetime

class CryptoArbitrage:
    def __init__(self, api_base, key_id: str, private_key, threshold, prod, mode, crypto, block_size):
        self.ticker = crypto
        month, day = get_month_day()
        self.above_ticker = "KX" + self.ticker + "D-24" + month.upper() + str(day) + "17"
        self.range_ticker = "KX" + self.ticker + "-24" + month.upper() + str(day) + "17"
        self.block_size = block_size
        self.prod = prod
        self.mode = mode

        self.exchange_client = ExchangeClient(api_base, key_id, private_key)
        self.above_event = Event(self.above_ticker, self.exchange_client)
        self.range_event = Event(self.range_ticker, self.exchange_client)

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
            idx = math.ceil(filter_digits(ticker.split("-")[-1])) // self.block_size
            above_dict[idx] = ticker
            min_idx = min(min_idx, idx)
            max_idx = max(max_idx, idx)

        for ticker in range_markets:
            idx = (math.ceil(filter_digits(ticker.split("-")[-1])) - (self.block_size/2)) // self.block_size
            range_dict[idx] = ticker
            min_idx = min(min_idx, idx)
            max_idx = max(max_idx, idx)

        for i in range(min_idx, max_idx+1):
            if i in above_dict:
                self.markets_arr[i - min_idx]["above"] = above_dict[i]
            if i in range_dict:
                self.markets_arr[i - min_idx]["range"] = range_dict[i]

        print("Markets set!")

    async def make_orders(self, orders_to_make):
        async with self.lock:  # Ensure only one make_orders execution
            if not orders_to_make:
                print("No opportunities found.")
                return

            for ticker, amount, side in orders_to_make:
                order_params = {
                    'ticker': ticker,
                    'client_order_id': str(uuid.uuid4()),
                    'type': 'market',
                    'action': 'buy',
                    'side': side,
                    'count': amount,  # Adjust as needed
                }
                self.exchange_client.create_order(**order_params)
                print(f"Order placed: {amount} shares of {ticker} ({side})")
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
                        above_sell, above_sell_price = await self.above_event.get_data(self.markets_arr[i]["above"], "yes")
                        above_buy, above_buy_price = await self.above_event.get_data(self.markets_arr[i + 1]["above"], "no")
                        range_buy, range_buy_price = await self.range_event.get_data(self.markets_arr[i]["range"], "no")

                        A, B, C = 100 - above_sell_price, 100 - above_buy_price, 100 - range_buy_price
                        orders = min(above_sell, above_buy, range_buy)
                        if self.prod:
                            orders = min(orders, self.balance//(A+B+C))
                        if orders > 0 and A + B + C < 100:
                            print(f"SBB Arbitrage found on {self.ticker} at {datetime.now().strftime("%H:%M:%S")}. Profit: {100 - A - B - C}, Orders: {orders}")
                            if 100 - A - B - C >= self.profit_threshold:
                                if self.prod:
                                    await self.make_orders([
                                        (self.markets_arr[i]["above"], orders, "no"),
                                        (self.markets_arr[i+1]["above"], orders, "yes"),
                                        (self.markets_arr[i]["range"], orders, "yes"),
                                    ])
                                    break

                    elif mode == "bss":
                        above_buy, above_buy_price = await self.above_event.get_data(self.markets_arr[i]["above"], "no")
                        above_sell, above_sell_price = await self.above_event.get_data(self.markets_arr[i + 1]["above"], "yes")
                        range_sell, range_sell_price = await self.range_event.get_data(self.markets_arr[i]["range"], "yes")

                        A, B, C = 100 - above_buy_price, 100 - above_sell_price, 100 - range_sell_price
                        orders = min(above_buy, above_sell, range_sell)
                        if self.prod:
                            orders = min(orders, self.balance//(A+B+C))
                        if orders > 0 and A + B + C < 200:
                            print(f"BSS Arbitrage found on {self.ticker} at {datetime.now().strftime("%H:%M:%S")}. Profit: {200 - A - B - C}, Orders: {orders}")
                            if 200 - A - B - C >= self.profit_threshold:
                                if self.prod:
                                    await self.make_orders([
                                        (self.markets_arr[i]["above"], orders, "yes"),
                                        (self.markets_arr[i+1]["above"], orders, "no"),
                                        (self.markets_arr[i]["range"], orders, "no"),
                                    ])
                                    break

                await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Scan error: {e}")

    async def run(self):
        self.set_markets()
        self.balance = self.exchange_client.get_balance()["balance"]

        self.above_event.initialize()
        self.range_event.initialize()

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
