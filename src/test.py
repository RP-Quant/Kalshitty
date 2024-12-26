from utils.KalshiClient import ExchangeClient
from config import API_BASE, KEY_ID
from utils.util import load_private_key_from_file
import uuid
from datetime import datetime, timedelta
import asyncio

private_key = load_private_key_from_file("src/kalshi.key")

ec = ExchangeClient(exchange_api_base=API_BASE, key_id=KEY_ID, private_key=private_key)

async def main():
    order1 = {'ticker': 'KXCOUNTRYBTC-26', 'client_order_id': str(uuid.uuid4()), 'type': 'market', 'action': 'buy', 'side': 'no', 'count': 1, 'expiration_ts': None, 'sell_position_floor': None, 'buy_max_cost': None}
    order2 = {'ticker': 'KXTEXASBTC-26', 'client_order_id': str(uuid.uuid4()), 'type': 'market', 'action': 'buy', 'side': 'no', 'count': 1, 'expiration_ts': None, 'sell_position_floor': None, 'buy_max_cost': None}
    order3 = {'ticker': 'KXBTCRESERVE-26-JAN01', 'client_order_id': str(uuid.uuid4()), 'type': 'market', 'action': 'buy', 'side': 'no', 'count': 10, 'expiration_ts': None, 'sell_position_floor': None, 'buy_max_cost': None}
    await ec.create_orders([order1, order2, order3])

asyncio.run(main())