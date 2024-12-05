from arbitrage_strategy import Arbitrage
from config import KEY_ID
from util import load_private_key_from_file
from datetime import datetime
from pytz import timezone
import time
from registry import Registry
import asyncio
from KalshiClientV3 import ExchangeClient
from base_strategy import BaseStrategy
from data_puller import DataPuller

async def run_strategies(strategies: list[BaseStrategy], data_puller: DataPuller):
    tasks = [strategy.run() for strategy in strategies]
    tasks.append(data_puller.get_data())
    await asyncio.gather(*tasks)

def main():
    private_key = load_private_key_from_file("src/kalshi.key")
    api_base = "https://api.elections.kalshi.com/trade-api/v2"

    BTC_PRICE_TICKER = "KXBTCD-"
    BTC_PRICE_RANGE_TICKER = "KXBTC-"

    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

    tz = timezone('EST')
    time = datetime.now(tz)

    day = time.day

    # if it's past 5 pm, use tomorrow's day
    if time.hour >= 17:
        day += 1

    if day < 10:
        day = "0" + str(day)
    else:
        day = str(day)

    BTC_PRICE_TICKER += str(time.year)[2:] + months[time.month - 1] + day + "17"
    BTC_PRICE_RANGE_TICKER += str(time.year)[2:] + months[time.month - 1] + day + "17"

    event_tickers = [BTC_PRICE_TICKER, BTC_PRICE_RANGE_TICKER]

    print(event_tickers)

    registry = Registry()
    client = ExchangeClient(api_base=api_base, key_id=KEY_ID, private_key=private_key)
    registry_mutex = asyncio.Lock()
    data_puller = DataPuller(registry=registry, registry_mutex=registry_mutex, event_tickers=event_tickers, client=client)

    strategies = [
        Arbitrage(registry=registry, event_tickers=event_tickers, client=client, registry_mutex=registry_mutex)
    ]

    asyncio.run(run_strategies(strategies=strategies, data_puller=data_puller))

if __name__ == "__main__":
    main()