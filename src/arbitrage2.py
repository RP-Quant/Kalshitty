from marketdata import Event
from config import KEY_ID
import asyncio
from util import load_private_key_from_file
from KalshiClientsBaseV2ApiKey import ExchangeClient

class Arbitrage:
    def __init__(self, api_base, key_id:str, private_key):
        self.exchange_client = ExchangeClient(api_base, key_id, private_key)
        self.above_event = Event("KXBTCD-24NOV2917", self.exchange_client)
        self.range_event = Event("KXBTC-24NOV2917", self.exchange_client)

    async def run(self):
        self.above_event.initialize()
        self.range_event.initialize()

        above_task = asyncio.create_task(self.above_event.start_listen())
        range_task = asyncio.create_task(self.range_event.start_listen())

        try:
            while True:
                # Fetch data asynchronously
                above_data = await self.above_event.get_data("KXBTCD-24NOV2917-T98249.99", "no")
                range_data = await self.range_event.get_data("KXBTC-24NOV2917-B98000", "no")
                print(f"Above: {above_data}, Range: {range_data}")
                await asyncio.sleep(1)  # Avoid tight loop, sleep for a second
        except asyncio.CancelledError:
            print("Main loop cancelled. Cleaning up...")
        finally:
            # Ensure the WebSocket task is cancelled when the main loop exits
            above_task.cancel()
            range_task.cancel()
            try:
                await above_task
                await range_task
            except asyncio.CancelledError:
                pass

private_key = load_private_key_from_file("src/kalshi.key")
api_base = "https://api.elections.kalshi.com/trade-api/v2"

arb = Arbitrage(api_base=api_base, key_id=KEY_ID, private_key=private_key)

asyncio.run(arb.run())