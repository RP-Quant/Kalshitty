from arbitrage_strategy import Arbitrage
from bsm_strategy import BSMStrategy
from config import KEY_ID
from utils.util import load_private_key_from_file
from datetime import datetime
from pytz import timezone
import time
from registry import Registry
import asyncio
from utils.KalshiClientV3 import ExchangeClient
from base_strategy import BaseStrategy
from data_puller import DataPuller
import aiohttp
from utils.util import login

async def main():
    private_key = load_private_key_from_file("src/kalshi.key")
    api_base = "https://api.elections.kalshi.com/trade-api/v2"

    BTC_PRICE_TICKER = "KXBTCD-"
    BTC_PRICE_RANGE_TICKER = "KXBTC-"

    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

    tz = timezone('EST')
    curr_time = datetime.now(tz)

    day = curr_time.day

    if day < 10:
        day = "0" + str(day)
    else:
        day = str(day)

    BTC_PRICE_TICKER += str(curr_time.year)[2:] + months[curr_time.month - 1] + day + str(curr_time.hour + 1)
    BTC_PRICE_RANGE_TICKER += str(curr_time.year)[2:] + months[curr_time.month - 1] + day + str(curr_time.hour + 1)

    all_tickers = [BTC_PRICE_TICKER, BTC_PRICE_RANGE_TICKER]
    arb_tickers = [BTC_PRICE_TICKER, BTC_PRICE_RANGE_TICKER]
    bsm_ticker = BTC_PRICE_TICKER

    registry = Registry()
    registry_mutex = asyncio.Lock()

    async with aiohttp.ClientSession() as session:
        client = ExchangeClient(exchange_api_base=api_base, key_id=KEY_ID, private_key=private_key, session=session)
        data_puller = DataPuller(registry=registry, registry_mutex=registry_mutex, event_tickers=all_tickers, client=client, key_id=KEY_ID, private_key=private_key)

        strategies = [
            # Arbitrage(registry=registry, event_tickers=arb_tickers, client=client, registry_mutex=registry_mutex),
            BSMStrategy(registry=registry, event_ticker=bsm_ticker, client=client, registry_mutex=registry_mutex)
        ]

        tasks = [asyncio.create_task(strategy.run()) for strategy in strategies]
        tasks.append(asyncio.create_task(data_puller.get_data()))
        tasks.append(asyncio.create_task(data_puller.get_btc_data()))

        while True:
            curr_time = datetime.now()
            curr_minute = curr_time.minute
            if curr_minute >= 55:
                print("end of current market, cleaning up and waiting for next market")

                for task in tasks:
                    task.cancel()

                await asyncio.sleep((61 - curr_minute) * 60)

                print("setting up next market")

                BTC_PRICE_TICKER = "KXBTCD-"
                BTC_PRICE_RANGE_TICKER = "KXBTC-"

                months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

                tz = timezone('EST')
                curr_time = datetime.now(tz)

                day = curr_time.day

                if day < 10:
                    day = "0" + str(day)
                else:
                    day = str(day)

                BTC_PRICE_TICKER += str(curr_time.year)[2:] + months[curr_time.month - 1] + day + str(curr_time.hour + 1)
                BTC_PRICE_RANGE_TICKER += str(curr_time.year)[2:] + months[curr_time.month - 1] + day + str(curr_time.hour + 1)

                all_tickers = [BTC_PRICE_TICKER, BTC_PRICE_RANGE_TICKER]
                arb_tickers = [BTC_PRICE_TICKER, BTC_PRICE_RANGE_TICKER]
                bsm_ticker = BTC_PRICE_TICKER

                data_puller = DataPuller(registry=registry, registry_mutex=registry_mutex, event_tickers=all_tickers, client=client, key_id=KEY_ID, private_key=private_key)

                strategies = [
                    # Arbitrage(registry=registry, event_tickers=arb_tickers, client=client, registry_mutex=registry_mutex),
                    BSMStrategy(registry=registry, event_ticker=bsm_ticker, client=client, registry_mutex=registry_mutex)
                ]

                tasks = [asyncio.create_task(strategy.run()) for strategy in strategies]
                tasks.append(asyncio.create_task(data_puller.get_data()))
                tasks.append(asyncio.create_task(data_puller.get_btc_data()))

            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())