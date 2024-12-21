import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from utils.util import Webscraper
from utils.KalshiClient import ExchangeClient
from config import API_BASE, KEY_ID
from utils.util import load_private_key_from_file, filter_digits
import math
import asyncio
from marketdata import Event
import uuid
from datetime import datetime, timedelta

private_key = load_private_key_from_file("src/kalshi.key")

ec = ExchangeClient(exchange_api_base=API_BASE, key_id=KEY_ID, private_key=private_key)

order = {'ticker': 'KXBTCD-24DEC0617-T101749.99', 'client_order_id': str(uuid.uuid4()), 'type': 'market', 'action': 'buy', 'side': 'no', 'count': 10, 'expiration_ts': None, 'sell_position_floor': None, 'buy_max_cost': None}

ec.create_order(**order)