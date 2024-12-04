from KalshiClientsBaseV2ApiKey import ExchangeClient
from config import API_BASE, KEY_ID
from util import load_private_key_from_file
import uuid
import asyncio

private_key = load_private_key_from_file("src/kalshi.key")

ec = ExchangeClient(exchange_api_base=API_BASE, key_id=KEY_ID, private_key=private_key)

async def test():
    order1 = {
        'ticker': "POPVOTEMOVSMALLER-24-R-B1.4",
        'client_order_id': str(uuid.uuid4()),
        'type': 'market',
        'action': 'buy',
        'side': "yes",
        'count': 1,  # Adjust as needed
    }
    order2 = {
        'ticker': "HOUSECA13-24-D",
        'client_order_id': str(uuid.uuid4()),
        'type': 'market',
        'action': 'buy',
        'side': "yes",
        'count': 1,  # Adjust as needed
    }
    order3 = {
        'ticker': "POPVOTEMOVSMALL-24-R-B1.4",
        'client_order_id': str(uuid.uuid4()),
        'type': 'market',
        'action': 'buy',
        'side': "yes",
        'count': 1,  # Adjust as needed
    }
    t1 = asyncio.create_task(ec.create_order(**order1))
    t2 = asyncio.create_task(ec.create_order(**order3))
    t3 = asyncio.create_task(ec.create_order(**order3))

    await t1
    await t2
    await t3

asyncio.run(test())