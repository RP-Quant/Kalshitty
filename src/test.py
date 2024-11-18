from KalshiClientsBaseV2ApiKey import ExchangeClient, HTTPError
import uuid
from config import KEY_ID
from pprint import pprint
import requests
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support.ui import Select
import time
from collections import defaultdict
import re
import math
from util import load_private_key_from_file, filter_digits, Webscraper
import time

class algo:
    def __init__(self):
        key_id = KEY_ID
        private_key = load_private_key_from_file("src/kalshi.key")
        api_base = "https://api.elections.kalshi.com/trade-api/v2"
        self.last_price_check = 0
        self.current_btc_price = 0
        self.exchange_client = ExchangeClient(exchange_api_base = api_base, key_id = key_id, private_key = private_key)
        self.range = 1000

        self.webscraper = Webscraper()

        self.tradable_markets = []
        
    def test(self):
        start = time.time()
        print(self.exchange_client.get_orderbook(ticker="KXBTC-24NOV1817-B88250", depth=32))
        print(time.time()-start)

alg = algo()
try:
    alg.test()
except HTTPError as e:
    print(str(e))