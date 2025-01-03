from base_strategy import BaseStrategy
from registry import Registry
import asyncio
import time
from utils.util import calc_fees, get_digits
from utils.KalshiClientV3 import ExchangeClient

class Arbitrage(BaseStrategy):
    def __init__(self, registry: Registry, event_tickers: list[str], client: ExchangeClient, registry_mutex: asyncio.Lock):
        super().__init__(registry, event_tickers, client, registry_mutex)
        
        self.above_below_ticker = event_tickers[0] if event_tickers[0].startswith("KXBTCD-") else event_tickers[1]
        self.range_ticker = event_tickers[0] if event_tickers[0].startswith("KXBTC-") else event_tickers[1]

        self.set_up = False
        self.event_to_sorted_market_indices = {e : None for e in event_tickers} # event ticker -> list of ints
        self.index_to_market_ticker = {e : {} for e in event_tickers} # event ticker -> index int -> actual market ticker
        self.market_range_width = 500 if self.above_below_ticker[-2:] == "17" else 250

        self.profit_threshold = 1

    async def run(self):
        await asyncio.sleep(10) # probably necessary because some weird race condition dont touch
        first = False

        while True:
            if not first:
                print("starting arb checking task")
                first = True

            async with self.mutex:
                # print(self.registry.data)
                # Your strategy here
                if not self.set_up:
                    if self.above_below_ticker not in self.registry.data:
                        continue
                    if len(self.registry.data[self.above_below_ticker]) != 0 \
                        and len(self.registry.data[self.range_ticker]) != 0:

                        above_below_indices = []
                        range_indices = []

                        for market in self.registry.data[self.above_below_ticker]:
                            first_num_str = market.split(" ")[0]
                            market_idx = get_digits(first_num_str)

                            above_below_indices.append(market_idx)
                            self.index_to_market_ticker[self.above_below_ticker][market_idx] = market

                        for market in self.registry.data[self.range_ticker]:
                            first_num_str = market.split(" ")[0]
                            market_idx = get_digits(first_num_str)

                            range_indices.append(market_idx)
                            self.index_to_market_ticker[self.range_ticker][market_idx] = market

                        ab_idx_set = set(above_below_indices)
                        range_idx_set = set(range_indices)

                        above_below_indices_filtered = [i for i in above_below_indices if i in range_idx_set]
                        range_indices_filtered = [i for i in range_indices if i in ab_idx_set]

                        above_below_indices_filtered.sort()
                        range_indices_filtered.sort()

                        if (above_below_indices_filtered[-1] + self.market_range_width) in ab_idx_set:
                            above_below_indices_filtered.append(above_below_indices_filtered[-1] + self.market_range_width)
                        else:
                            range_indices_filtered.pop()

                        # print(above_below_indices_filtered)
                        # print(range_indices_filtered)

                        self.event_to_sorted_market_indices[self.above_below_ticker] = above_below_indices_filtered
                        self.event_to_sorted_market_indices[self.range_ticker] = range_indices_filtered

                        self.set_up = True

                        # print(self.event_to_sorted_market_indices[self.above_below_ticker])
                        # print(self.event_to_sorted_market_indices[self.range_ticker])

                        assert (len(self.event_to_sorted_market_indices[self.above_below_ticker]) == len(self.event_to_sorted_market_indices[self.range_ticker]) + 1)
                else:
                    # print(self.registry.last_data_recv_ts)
                    # print(time.time(), self.registry.check_data_freshness())
                    if self.registry.check_data_freshness():
                        range_starts = self.event_to_sorted_market_indices[self.range_ticker]
                        above_below = self.event_to_sorted_market_indices[self.above_below_ticker]

                        best_orders = {
                            "profit": 0,
                            "volume": 0,
                            "cost": 0,
                            "orders": {} # ticker: {"side": side}
                        }
                        
                        #profit, ("no"/"yes", ticker1), ("no"/"yes", ticker2), ("no"/"yes", ticker3)
                        for idx in range(len(range_starts)):
                            range_start = range_starts[idx]
                            ab_start = above_below[idx]
                            ab_end = above_below[idx + 1]

                            if range_start == ab_start and ab_end - ab_start == self.market_range_width:
                                range_start_ticker = self.index_to_market_ticker[self.range_ticker][range_start]
                                ab_start_ticker = self.index_to_market_ticker[self.above_below_ticker][ab_start]
                                ab_end_ticker = self.index_to_market_ticker[self.above_below_ticker][ab_end]

                                range_unique_ticker = self.registry.data[self.range_ticker][range_start_ticker]["unique_ticker"]
                                ab_start_unique_ticker = self.registry.data[self.above_below_ticker][ab_start_ticker]["unique_ticker"]
                                ab_end_unique_ticker = self.registry.data[self.above_below_ticker][ab_end_ticker]["unique_ticker"]

                                range_start_yes_ask_price = self.registry.data[self.range_ticker][range_start_ticker]["yes_ask_price"]
                                ab_start_yes_ask_price = self.registry.data[self.above_below_ticker][ab_start_ticker]["yes_ask_price"]
                                ab_end_yes_ask_price = self.registry.data[self.above_below_ticker][ab_end_ticker]["yes_ask_price"]

                                range_start_no_ask_price = self.registry.data[self.range_ticker][range_start_ticker]["no_ask_price"]
                                ab_start_no_ask_price = self.registry.data[self.above_below_ticker][ab_start_ticker]["no_ask_price"]
                                ab_end_no_ask_price = self.registry.data[self.above_below_ticker][ab_end_ticker]["no_ask_price"]

                                range_start_yes_ask_volume = self.registry.data[self.range_ticker][range_start_ticker]["yes_ask_volume"]
                                ab_start_yes_ask_volume = self.registry.data[self.above_below_ticker][ab_start_ticker]["yes_ask_volume"]
                                ab_end_yes_ask_volume = self.registry.data[self.above_below_ticker][ab_end_ticker]["yes_ask_volume"]

                                range_start_no_ask_volume = self.registry.data[self.range_ticker][range_start_ticker]["no_ask_volume"]
                                ab_start_no_ask_volume = self.registry.data[self.above_below_ticker][ab_start_ticker]["no_ask_volume"]
                                ab_end_no_ask_volume = self.registry.data[self.above_below_ticker][ab_end_ticker]["no_ask_volume"]

                                # range_start_yes_bid_price = self.registry.data[self.range_ticker][range_start_ticker]["yes_bid_price"]
                                # ab_start_yes_bid_price = self.registry.data[self.above_below_ticker][ab_start_ticker]["yes_bid_price"]
                                # ab_end_yes_bid_price = self.registry.data[self.above_below_ticker][ab_end_ticker]["yes_bid_price"]

                                # range_start_no_bid_price = self.registry.data[self.range_ticker][range_start_ticker]["no_bid_price"]
                                # ab_start_no_bid_price = self.registry.data[self.above_below_ticker][ab_start_ticker]["no_bid_price"]
                                # ab_end_no_bid_price = self.registry.data[self.above_below_ticker][ab_end_ticker]["no_bid_price"]

                                # range_start_yes_bid_volume = self.registry.data[self.range_ticker][range_start_ticker]["yes_bid_volume"]
                                # ab_start_yes_bid_volume = self.registry.data[self.above_below_ticker][ab_start_ticker]["yes_bid_volume"]
                                # ab_end_yes_bid_volume = self.registry.data[self.above_below_ticker][ab_end_ticker]["yes_bid_volume"]

                                # range_start_no_bid_volume = self.registry.data[self.range_ticker][range_start_ticker]["no_bid_volume"]
                                # ab_start_no_bid_volume = self.registry.data[self.above_below_ticker][ab_start_ticker]["no_bid_volume"]
                                # ab_end_no_bid_volume = self.registry.data[self.above_below_ticker][ab_end_ticker]["no_bid_volume"]

                                if range_start_yes_ask_price is None or \
                                    ab_start_yes_ask_price is None or \
                                    ab_end_yes_ask_price is None or \
                                    range_start_no_ask_price is None or \
                                    ab_start_no_ask_price is None or \
                                    ab_end_no_ask_price is None:
                                    # range_start_yes_bid_price is None or \
                                    # ab_start_yes_bid_price is None or \
                                    # ab_end_yes_bid_price is None or \
                                    # range_start_no_bid_price is None or \
                                    # ab_start_no_bid_price is None or \
                                    # ab_end_no_bid_price is None:

                                    continue

                                # check sell buy buy and buy sell sell

                                # buy = 100 - no price = buying yes
                                # sell = 100 - yes price = buying no

                                # sell buy buy:
                                sbb_profit = 100 - (ab_start_no_ask_price + ab_end_yes_ask_price + range_start_yes_ask_price)

                                sbb_fees = 0
                                sbb_total_volume = min(ab_start_no_ask_volume, ab_end_yes_ask_volume, range_start_yes_ask_volume)
                                sbb_fees += calc_fees(ab_start_no_ask_price, sbb_total_volume)
                                sbb_fees += calc_fees(ab_end_yes_ask_price, sbb_total_volume)
                                sbb_fees += calc_fees(range_start_yes_ask_price, sbb_total_volume)
                                
                                sbb_profit -= sbb_fees

                                # buy sell sell
                                bss_profit = 200 - (ab_start_yes_ask_price + ab_end_no_ask_price + range_start_no_ask_price)
                                
                                bss_fees = 0
                                bss_total_volume = min(ab_start_yes_ask_volume, ab_end_no_ask_volume, range_start_no_ask_volume)
                                bss_fees += calc_fees(ab_start_yes_ask_price, bss_total_volume)
                                bss_fees += calc_fees(ab_end_no_ask_price, bss_total_volume)
                                bss_fees += calc_fees(range_start_no_ask_price, bss_total_volume)

                                bss_profit -= bss_fees

                                # print("sbb, bss profit", sbb_profit, bss_profit)
                                if sbb_profit > best_orders["profit"]:
                                        best_orders["profit"] = sbb_profit
                                        best_orders["volume"] = sbb_total_volume
                                        best_orders["cost"] = (ab_start_no_ask_price + ab_end_yes_ask_price + range_start_yes_ask_price) * sbb_total_volume + sbb_fees
                                        best_orders["orders"] = {
                                            ab_start_unique_ticker: {"side": "no"},
                                            ab_end_unique_ticker: {"side": "yes"},
                                            range_unique_ticker: {"side": "yes"}
                                        }

                                        # bid_price_abs = self.registry.data[self.above_below_ticker][ab_start_ticker]["no_bid_price"]
                                        # bid_price_abe = self.registry.data[self.above_below_ticker][ab_end_ticker]["yes_bid_price"]
                                        # bid_price_r = self.registry.data[self.range_ticker][range_start_ticker]["yes_bid_price"]
                                        # print("spread abs", ab_start_no_price - bid_price_abs)
                                        # print("spread abe", ab_end_yes_price - bid_price_abe)
                                        # print("spread range", range_start_yes_price - bid_price_r)


                                
                                elif bss_profit > best_orders["profit"]:
                                        best_orders["profit"] = bss_profit
                                        best_orders["volume"] = bss_total_volume
                                        best_orders["cost"] = (ab_start_yes_ask_price + ab_end_no_ask_price + range_start_no_ask_price) * bss_total_volume + bss_fees
                                        best_orders["orders"] = {
                                            ab_start_unique_ticker: {"side": "yes"},
                                            ab_end_unique_ticker: {"side": "no"},
                                            range_unique_ticker: {"side": "no"}
                                        }
                                        # bid_price_abs = self.registry.data[self.above_below_ticker][ab_start_ticker]["yes_bid_price"]
                                        # bid_price_abe = self.registry.data[self.above_below_ticker][ab_end_ticker]["no_bid_price"]
                                        # bid_price_r = self.registry.data[self.range_ticker][range_start_ticker]["no_bid_price"]
                                        # print("spread abs", ab_start_yes_price - bid_price_abs)
                                        # print("spread abe", ab_end_no_price - bid_price_abe)
                                        # print("spread range", range_start_no_price - bid_price_r)
                                
                            else:
                                raise ValueError("Range and above/below mismatch; check markets manually for alignment")
                        
                        if best_orders["profit"] > self.profit_threshold:
                            total_cost = best_orders["cost"]
                            num_contracts = best_orders["volume"]
                            total_profit = best_orders["profit"]

                            print(best_orders)
                            
                            # make orders

                            for ticker in best_orders["orders"]:
                                if best_orders["orders"][ticker]["side"] == "yes":
                                    # print("buy yes arb")
                                    self.buy_yes_market_order(ticker=ticker, amount=1) #TODO: CHANGE TO num_contracts ONCE DONE TESTING
                                else:
                                    # print("buy no arb")
                                    self.buy_no_market_order(ticker=ticker, amount=1)

                            print("volume", num_contracts)
                            print("total profit:", "$" + str(total_profit))
                            print("amount staked:", "$" + str(total_cost))
                            print("percentage return:", str(round(total_profit / total_cost * 100, 2)) + "%")
                            print("time elapsed", time.time() - self.registry.last_data_recv_ts)

                            await asyncio.sleep(15)

            await asyncio.sleep(0.01)