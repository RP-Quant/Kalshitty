from base_strategy import BaseStrategy
from registry import Registry
import asyncio
import time
from util import calc_fees, get_digits
from KalshiClientV3 import ExchangeClient

class Arbitrage(BaseStrategy):
    def __init__(self, registry: Registry, event_tickers: list[str], client: ExchangeClient, registry_mutex: asyncio.Lock):
        super().__init__(registry, event_tickers, client, registry_mutex)
        
        self.above_below_ticker = event_tickers[0] if event_tickers[0].startswith("KXBTCD-") else event_tickers[1]
        self.range_ticker = event_tickers[0] if event_tickers[0].startswith("KXBTC-") else event_tickers[1]

        self.set_up = False
        self.event_to_sorted_market_indices = {e : None for e in event_tickers} # event ticker -> list of ints
        self.index_to_market_ticker = {e : {} for e in event_tickers} # event ticker -> index int -> actual market ticker

    async def run(self):
        while True:
            async with self.mutex:
                # Your strategy here
                if not self.set_up:
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

                        if (above_below_indices_filtered[-1] + 500) in ab_idx_set:
                            above_below_indices_filtered.append(above_below_indices_filtered[-1] + 500)
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

                        best_orders = [] #profit, ("no"/"yes", ticker1), ("no"/"yes", ticker2), ("no"/"yes", ticker3)

                        for idx in range(len(range_starts)):
                            range_start = range_starts[idx]
                            ab_start = above_below[idx]
                            ab_end = above_below[idx + 1]

                            if range_start == ab_start and ab_end - ab_start == 500:
                                range_start_ticker = self.index_to_market_ticker[self.range_ticker][range_start]
                                ab_start_ticker = self.index_to_market_ticker[self.above_below_ticker][ab_start]
                                ab_end_ticker = self.index_to_market_ticker[self.above_below_ticker][ab_end]

                                range_unique_ticker = self.registry.data[self.range_ticker][range_start_ticker]["unique_ticker"]
                                ab_start_unique_ticker = self.registry.data[self.above_below_ticker][ab_start_ticker]["unique_ticker"]
                                ab_end_unique_ticker = self.registry.data[self.above_below_ticker][ab_end_ticker]["unique_ticker"]

                                range_start_yes_price = self.registry.data[self.range_ticker][range_start_ticker]["yes_price"]
                                ab_start_yes_price = self.registry.data[self.above_below_ticker][ab_start_ticker]["yes_price"]
                                ab_end_yes_price = self.registry.data[self.above_below_ticker][ab_end_ticker]["yes_price"]

                                range_start_no_price = self.registry.data[self.range_ticker][range_start_ticker]["no_price"]
                                ab_start_no_price = self.registry.data[self.above_below_ticker][ab_start_ticker]["no_price"]
                                ab_end_no_price = self.registry.data[self.above_below_ticker][ab_end_ticker]["no_price"]

                                range_start_yes_volume = self.registry.data[self.range_ticker][range_start_ticker]["yes_volume"]
                                ab_start_yes_volume = self.registry.data[self.above_below_ticker][ab_start_ticker]["yes_volume"]
                                ab_end_yes_volume = self.registry.data[self.above_below_ticker][ab_end_ticker]["yes_volume"]

                                range_start_no_volume = self.registry.data[self.range_ticker][range_start_ticker]["no_volume"]
                                ab_start_no_volume = self.registry.data[self.above_below_ticker][ab_start_ticker]["no_volume"]
                                ab_end_no_volume = self.registry.data[self.above_below_ticker][ab_end_ticker]["no_volume"]

                                if range_start_yes_price is None or \
                                    ab_start_yes_price is None or \
                                    ab_end_yes_price is None or \
                                    range_start_no_price is None or \
                                    ab_start_no_price is None or \
                                    ab_end_no_price is None:

                                    continue

                                # check sell buy buy and buy sell sell

                                # buy = 100 - no price = buying yes
                                # sell = 100 - yes price = buying no

                                # sell buy buy:
                                sbb_profit = 100 - (100 - ab_start_yes_price) - (100 - ab_end_no_price) - (100 - range_start_no_price)

                                # buy sell sell
                                bss_profit = 200 - (100 - ab_start_no_price) - (100 - ab_end_yes_price) - (100 - range_start_yes_price)
                                # print(sbb_profit, bss_profit)
                                if sbb_profit > 0:
                                    if len(best_orders) == 0 or sbb_profit > best_orders[0]:
                                        best_orders = [sbb_profit, ("no", ab_start_unique_ticker, (100 - ab_start_yes_price), ab_start_yes_volume), ("yes", ab_end_unique_ticker, (100 - ab_end_no_price), ab_end_no_volume), ("yes", range_unique_ticker, (100 - range_start_no_price), range_start_no_volume)]
                                        print("sbb, profit:", sbb_profit, ab_start_no_price, ab_end_yes_price, range_start_yes_price, ab_start, ab_end)
                                       
                                        bid_price_abs = self.registry.data[self.above_below_ticker][ab_start_ticker]["no_bid_price"]
                                        bid_price_abe = self.registry.data[self.above_below_ticker][ab_end_ticker]["yes_bid_price"]
                                        bid_price_r = self.registry.data[self.range_ticker][range_start_ticker]["yes_bid_price"]
                                        print("spread abs", ab_start_no_price - bid_price_abs)
                                        print("spread abe", ab_end_yes_price - bid_price_abe)
                                        print("spread range", range_start_yes_price - bid_price_r)


                                
                                elif bss_profit > 0:
                                    if len(best_orders) == 0 or bss_profit > best_orders[0]:
                                        best_orders = [bss_profit, ("yes", ab_start_unique_ticker, (100 - ab_start_no_price), ab_start_no_volume), ("no", ab_end_unique_ticker, (100 - ab_end_yes_price), ab_end_yes_volume), ("no", range_unique_ticker, (100 - range_start_yes_price), range_start_yes_volume)]
                                        print("bss, profit:", bss_profit, range_start_no_price, ab_start_yes_price, ab_end_no_price, ab_start)

                                        bid_price_abs = self.registry.data[self.above_below_ticker][ab_start_ticker]["yes_bid_price"]
                                        bid_price_abe = self.registry.data[self.above_below_ticker][ab_end_ticker]["no_bid_price"]
                                        bid_price_r = self.registry.data[self.range_ticker][range_start_ticker]["no_bid_price"]
                                        print("spread abs", ab_start_yes_price - bid_price_abs)
                                        print("spread abe", ab_end_no_price - bid_price_abe)
                                        print("spread range", range_start_no_price - bid_price_r)
                                
                            else:
                                raise ValueError("Range and above/below mismatch; check markets manually for alignment")
                        
                        if len(best_orders) > 0 and best_orders[0] > 2:
                            # get fees

                            num_contracts = min(best_orders[1][3], best_orders[2][3], best_orders[3][3])
                            total_fees = 0

                            total_fees += calc_fees(best_orders[1][2], num_contracts)
                            total_fees += calc_fees(best_orders[2][2], num_contracts)
                            total_fees += calc_fees(best_orders[3][2], num_contracts)

                            total_profit = best_orders[0] * num_contracts / 100 - total_fees

                            # if total_profit > 0:
                            total_cost = num_contracts * (best_orders[1][2] / 100 + best_orders[2][2] / 100 + best_orders[3][2] / 100)
                            
                            # make orders

                            for order in best_orders[1:]:
                                if order[0] == "yes":
                                    print(time.time())
                                    # self.buy_yes_market_order(client=client, ticker=order[1], amount=1) #TODO: CHANGE TO num_contracts ONCE DONE TESTING
                                else:
                                    print(time.time())
                                    # self.buy_no_market_order(client=client, ticker=order[1], amount=1)

                            print("volumes", best_orders[1][3], best_orders[2][3], best_orders[3][3])
                            print("total profit:", "$" + str(total_profit))
                            print("amount staked:", "$" + str(total_cost))
                            print("percentage return:", str(round(total_profit / total_cost * 100, 2)) + "%")
                            print("time elapsed", time.time() - self.registry.last_data_recv_ts)

                            # sleep globally to reset TPS

                            await asyncio.sleep(4)



                # for market in self.registry.data[self.above_below_ticker]:
                #     print(market + " bid:", self.registry.data[self.above_below_ticker][market]["yes_bid_price"], "ask:", self.registry.data[self.above_below_ticker][market]["yes_ask_price"])
                # for market in self.registry.data[self.range_ticker]:
                #     print(market + " bid:", self.registry.data[self.range_ticker][market]["yes_bid_price"], "ask:", self.registry.data[self.range_ticker][market]["yes_ask_price"])
            
            await asyncio.sleep(.01)