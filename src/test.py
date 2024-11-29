from arbitrage import SpreadCover, Mint
from config import KEY_ID, BTC_PRICE_TICKER, BTC_PRICE_RANGE_TICKER, ETH_PRICE_TICKER, ETH_PRICE_RANGE_TICKER
from util import load_private_key_from_file
from marketdata import Event
import asyncio
from KalshiClientsBaseV2ApiKey import ExchangeClient

private_key = load_private_key_from_file("src/kalshi.key")
api_base = "https://api.elections.kalshi.com/trade-api/v2"

ec = ExchangeClient(exchange_api_base=api_base, key_id=KEY_ID, private_key=private_key)

event = Event("KXBTC-24NOV2917", exchange_client=ec)

async def main():
    # Initialize event markets
    event.initialize()
    
    # Run WebSocket listener in the background
    websocket_task = asyncio.create_task(event.start_listen())
    
    # Periodically print market data
    try:
        while True:
            # Fetch data asynchronously
            data = await event.get_data("KXBTC-24NOV2917-B98000", "no")
            print(data)
            await asyncio.sleep(1)  # Avoid tight loop, sleep for a second
    except asyncio.CancelledError:
        print("Main loop cancelled. Cleaning up...")
    finally:
        # Ensure the WebSocket task is cancelled when the main loop exits
        websocket_task.cancel()
        try:
            await websocket_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    asyncio.run(main())
