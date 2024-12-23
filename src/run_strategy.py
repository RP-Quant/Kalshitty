from arbitrage_strategy import Arbitrage
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
    time = datetime.now(tz)

    day = time.day

    if day < 10:
        day = "0" + str(day)
    else:
        day = str(day)

    BTC_PRICE_TICKER += str(time.year)[2:] + months[time.month - 1] + day + str(time.hour + 1)
    BTC_PRICE_RANGE_TICKER += str(time.year)[2:] + months[time.month - 1] + day + str(time.hour + 1)

    # event_tickers = [BTC_PRICE_TICKER, BTC_PRICE_RANGE_TICKER]
    event_tickers = ["KXBTCD-24DEC2317", "KXBTC-24DEC2317"]

    print(event_tickers)

    registry = Registry()
    registry_mutex = asyncio.Lock()

    async with aiohttp.ClientSession() as session:
        client = ExchangeClient(exchange_api_base=api_base, key_id=KEY_ID, private_key=private_key, session=session)
        data_puller = DataPuller(registry=registry, registry_mutex=registry_mutex, event_tickers=event_tickers, client=client, key_id=KEY_ID, private_key=private_key)

        strategies = [
            Arbitrage(registry=registry, event_tickers=event_tickers, client=client, registry_mutex=registry_mutex)
        ]

        tasks = [strategy.run() for strategy in strategies]
        tasks.append(data_puller.get_data())
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())