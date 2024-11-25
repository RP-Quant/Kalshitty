from base_strategy import BaseStrategy
from registry import Registry
import asyncio
import time

class Strategy(BaseStrategy):
    def __init__(self, api_base: str, key_id: str, private_key, registry: Registry, event_tickers: list[str]):
        super().__init__(api_base, key_id, private_key, registry, event_tickers)

        sorted_tickers = {e : None for e in event_tickers}

    async def strategy(self, client):
        while True:
            async with self.mutex:
                # Your strategy here
                pass
            await asyncio.sleep(0.1)