from marketdata import Event
from config import KEY_ID
import asyncio
from util import load_private_key_from_file, filter_digits
from KalshiClientsBaseV2ApiKey import ExchangeClient
import math
from pprint import pprint
from collections import defaultdict

class BTCArbitrage:
    def __init__(self, api_base, key_id:str, private_key):
        self.exchange_client = ExchangeClient(api_base, key_id, private_key)
        self.above_event = Event("KXBTCD-24NOV2917", self.exchange_client)
        self.range_event = Event("KXBTC-24NOV2917", self.exchange_client)

        self.markets_arr = [{"above" : None, "range" : None} for _ in range(100)]

    def set_markets(self):
        above_markets = [m["ticker"] for m in self.exchange_client.get_event("KXBTCD-24NOV2917")["markets"]]
        range_markets = [m["ticker"] for m in self.exchange_client.get_event("KXBTC-24NOV2917")["markets"]]
        above_dict = {}
        range_dict = {}

        min_idx = float("inf")
            
        for ticker in above_markets:
            idx = (math.ceil(filter_digits(ticker.split("-")[-1]))//250)//2
            above_dict[idx] = ticker
            min_idx = min(min_idx, idx)

        for ticker in range_markets:
            idx = ((math.ceil(filter_digits(ticker.split("-")[-1]))-250)//250)//2
            range_dict[idx] = ticker
            min_idx = min(min_idx, idx)

        for i in range(100, 300):
            if above_dict.get(i, None):
                self.markets_arr[i-min_idx]["above"] = above_dict[i]
            if range_dict.get(i, None):
                self.markets_arr[i-min_idx]["range"] = range_dict[i]

        print("markets set!")

    async def scan(self, mode: str):
        try:
            while True:
                print("Scan running...")
                for i in range(99):
                    if mode == "sbb":
                        if self.markets_arr[i]["above"] and self.markets_arr[i]["range"] and self.markets_arr[i+1]["above"]:
                            above_sell_orders, above_sell_price = await self.above_event.get_data(self.markets_arr[i]["above"], "yes")
                            above_buy_orders, above_buy_price = await self.above_event.get_data(self.markets_arr[i+1]["above"], "no")
                            range_buy_orders, range_buy_price = await self.range_event.get_data(self.markets_arr[i]["range"], "no")

                            A, B, C = 100-above_sell_price, 100-above_buy_price, 100-range_buy_price
                            orders = min(above_sell_orders, above_buy_orders, range_buy_orders)
                            if orders == 0:
                                continue
                            #print(A, B, C, orders)
                            if A+B+C < 100:
                                print(f"SBB Arbitrage found. Profit: {100-A-B-C}, orders: {orders}")
                    else:
                        if self.markets_arr[i]["above"] and self.markets_arr[i]["range"] and self.markets_arr[i+1]["above"]:
                            above_buy_orders, above_buy_price = await self.above_event.get_data(self.markets_arr[i]["above"], "no")
                            above_sell_orders, above_sell_price = await self.above_event.get_data(self.markets_arr[i+1]["above"], "yes")
                            range_sell_orders, range_sell_price = await self.range_event.get_data(self.markets_arr[i]["range"], "yes")

                            A, B, C = 100-above_buy_price, 100-above_sell_price, 100-range_sell_price
                            orders = min(above_buy_orders, above_sell_orders, range_sell_orders)
                            if orders == 0:
                                continue
                            #print(A, B, C, orders)

                            if A+B+C < 200:
                                print(f"BSS Arbitrage found. Profit: {200-A-B-C}, orders: {orders}")

                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"an error occurred: {e}")

    async def run(self):
        self.set_markets()

        self.above_event.initialize()
        self.range_event.initialize()

        above_task = asyncio.create_task(self.above_event.start_listen())
        range_task = asyncio.create_task(self.range_event.start_listen())
        scan_task = asyncio.create_task(self.scan(mode = "bss"))

        try:
            while True:
                await asyncio.sleep(1)  # Avoid tight loop, sleep for a second
        except asyncio.CancelledError:
            print("Main loop cancelled. Cleaning up...")
        finally:
            # Ensure the WebSocket task is cancelled when the main loop exits
            above_task.cancel()
            range_task.cancel()
            scan_task.cancel()
            try:
                await above_task
                await range_task
                await scan_task
            except asyncio.CancelledError:
                pass

private_key = load_private_key_from_file("src/kalshi.key")
api_base = "https://api.elections.kalshi.com/trade-api/v2"

arb = BTCArbitrage(api_base=api_base, key_id=KEY_ID, private_key=private_key)

asyncio.run(arb.run())