import asyncio
import uuid
import math
import time
from KalshiClientsBaseV2ApiKey import ExchangeClient
from marketdata import Event
from util import load_private_key_from_file, filter_digits
from config import KEY_ID


class BTCArbitrage:
    def __init__(self, api_base, key_id: str, private_key, range_ticker, above_ticker, threshold):
        self.exchange_client = ExchangeClient(api_base, key_id, private_key)
        self.above_ticker = above_ticker
        self.range_ticker = range_ticker
        self.above_event = Event(above_ticker, self.exchange_client)
        self.range_event = Event(range_ticker, self.exchange_client)

        self.markets_arr = [{"above": None, "range": None} for _ in range(100)]
        self.balance = 0
        self.lock = asyncio.Lock()  # Lock for exclusive access to make_orders
        self.profit_threshold = threshold

    def set_markets(self):
        above_markets = [m["ticker"] for m in self.exchange_client.get_event(self.above_ticker)["markets"]]
        range_markets = [m["ticker"] for m in self.exchange_client.get_event(self.range_ticker)["markets"]]
        above_dict, range_dict = {}, {}
        min_idx = float("inf")

        for ticker in above_markets:
            idx = math.ceil(filter_digits(ticker.split("-")[-1])) // 500
            above_dict[idx] = ticker
            min_idx = min(min_idx, idx)

        for ticker in range_markets:
            idx = (math.ceil(filter_digits(ticker.split("-")[-1])) - 250) // 500
            range_dict[idx] = ticker
            min_idx = min(min_idx, idx)

        for i in range(100, 300):
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
            time.sleep(1)

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
                        orders = min(above_sell, above_buy, range_buy, self.balance//(A+B+C))
                        if orders > 0 and A + B + C < 100:
                            print(f"SBB Arbitrage found. Profit: {100 - A - B - C}, Orders: {orders}")
                            if 100 - A - B - C >= self.profit_threshold:
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
                        orders = min(above_buy, above_sell, range_sell, self.balance//(A+B+C))
                        if orders > 0 and A + B + C < 200:
                            print(f"BSS Arbitrage found. Profit: {200 - A - B - C}, Orders: {orders}")
                            if 200 - A - B - C >= self.profit_threshold:
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
        scan_task = asyncio.create_task(self.scan(mode="sbb"))

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

class ETHArbitrage:
    def __init__(self, api_base, key_id: str, private_key, range_ticker, above_ticker, threshold):
        self.exchange_client = ExchangeClient(api_base, key_id, private_key)
        self.above_ticker = above_ticker
        self.range_ticker = range_ticker
        self.above_event = Event(above_ticker, self.exchange_client)
        self.range_event = Event(range_ticker, self.exchange_client)

        self.markets_arr = [{"above": None, "range": None} for _ in range(100)]
        self.balance = 0
        self.lock = asyncio.Lock()  # Lock for exclusive access to make_orders
        self.profit_threshold = threshold

    def set_markets(self):
        above_markets = [m["ticker"] for m in self.exchange_client.get_event(self.above_ticker)["markets"]]
        range_markets = [m["ticker"] for m in self.exchange_client.get_event(self.range_ticker)["markets"]]
        above_dict, range_dict = {}, {}
        min_idx = float("inf")

        for ticker in above_markets:
            idx = math.ceil(filter_digits(ticker.split("-")[-1])) // 40
            above_dict[idx] = ticker
            min_idx = min(min_idx, idx)

        for ticker in range_markets:
            idx = (math.ceil(filter_digits(ticker.split("-")[-1])) - 20) // 40
            range_dict[idx] = ticker
            min_idx = min(min_idx, idx)

        for i in range(50, 150):
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
            time.sleep(1)

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
                        orders = min(above_sell, above_buy, range_buy, self.balance//(A+B+C))
                        if orders > 0 and A + B + C < 100:
                            print(f"SBB Arbitrage found. Profit: {100 - A - B - C}, Orders: {orders}")
                            if 100 - A - B - C >= self.profit_threshold:
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
                        orders = min(above_buy, above_sell, range_sell, self.balance//(A+B+C))
                        if orders > 0 and A + B + C < 200:
                            print(f"BSS Arbitrage found. Profit: {200 - A - B - C}, Orders: {orders}")
                            if 200 - A - B - C >= self.profit_threshold:
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
        scan_task = asyncio.create_task(self.scan(mode="sbb"))

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

# Run the arbitrage bot
private_key = load_private_key_from_file("src/kalshi.key")
api_base = "https://api.elections.kalshi.com/trade-api/v2"

arb = ETHArbitrage(api_base=api_base, key_id=KEY_ID, private_key=private_key, above_ticker="KXETHD-24DEC0317", range_ticker="KXETH-24DEC0317", threshold=3)
asyncio.run(arb.run())
