from utils.util import load_private_key_from_file
from utils.KalshiClient import ExchangeClient
from config import API_BASE, KEY_ID
from datacollection.DataListeners import EventListener, MarketListener
import asyncio

private_key = load_private_key_from_file("src/kalshi.key")
client = ExchangeClient(exchange_api_base=API_BASE, key_id=KEY_ID, private_key=private_key)
#token = login()

#listener = MarketListener(auth_token=token, market_ticker="KXSECVA-26DEC31-DC")
listener = EventListener(exchange_client=client, private_key= private_key, key_id=KEY_ID, event_ticker="KXBTC-24DEC2220")

async def get_asks():
    while 1:
        print(f"Yes ask: {await listener.get_ask("KXBTC-24DEC2220-B95125", "yes")}")
        print(f"No ask: {await listener.get_ask("KXBTC-24DEC2220-B95125", "no")}")
        await asyncio.sleep(1)

async def main():
    t1 = asyncio.create_task(listener.start_listen())
    t2 = asyncio.create_task(get_asks())
    await asyncio.gather(t1, t2)

# Start the asyncio event loop
asyncio.run(main())