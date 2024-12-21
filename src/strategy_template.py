from base_strategy import BaseStrategy
from registry import Registry
import asyncio
import time
from utils.util import calc_fees, get_digits
from utils.KalshiClientV3 import ExchangeClient

class YourStrategy(BaseStrategy):
    def __init__(self, registry: Registry, event_tickers: list[str], client: ExchangeClient, registry_mutex: asyncio.Lock):
        super().__init__(registry, event_tickers, client, registry_mutex)
        
    async def run(self):
        # Your strategy here
        pass