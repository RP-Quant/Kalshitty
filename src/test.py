from KalshiClientsBaseV2ApiKey import ExchangeClient
import uuid
import json
from cryptostuff import load_private_key_from_file
from config import KEY_ID
from pprint import pprint
import time

key_id = KEY_ID
private_key = load_private_key_from_file("src/kalshi.key")
api_base = "https://api.elections.kalshi.com/trade-api/v2"

exchange_client = ExchangeClient(exchange_api_base = api_base, key_id = key_id, private_key = private_key)

cursor = None
ticker = "KXBTCD-24NOV1217-T91249.99"

order_params = {'ticker':ticker,
                    'client_order_id':str(uuid.uuid4()),
                    'type':'limit',
                    'action':'buy',
                    'side':'no',
                    'count':1,
                    'yes_price':None, # yes_price = 100 - no_price
                    'no_price':1, # no_price = 100 - yes_price
                    'expiration_ts':None,
                    'sell_position_floor':None,
                    'buy_max_cost':None}

exchange_client.create_order(**order_params)