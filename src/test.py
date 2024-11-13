from KalshiClientsBaseV2ApiKey import ExchangeClient
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
        
    def get_markets(self):
        self.tradable_markets.clear()
        cursor = None
        self.current_btc_price = self.webscraper.get_BTC_price()
        for _ in range(3):
            market_params = {'limit':1000,
                    'cursor':cursor, # passing in the cursor from the previous get_markets call
                    'event_ticker': None,
                    'series_ticker':None,
                    'max_close_ts':None, # pass in unix_ts
                    'min_close_ts':None, # pass in unix_ts
                    'status':None,
                    'tickers':None
                    }
            markets_response = self.exchange_client.get_markets(**market_params)
            cursor = markets_response['cursor']
            for market in markets_response["markets"]:
                if "Bitcoin" in market["title"] and "Nov 12" in market["title"] and "range" not in market["title"]:
                    if self.current_btc_price-1000 <= filter_digits(market["subtitle"]) <= self.current_btc_price+1000:
                        self.tradable_markets.append((market["title"], market["subtitle"], market["ticker"]))

        self.last_price_check = time.time()
    
    def get_asks(self):
        market_asks = {}
        for title, subtitle, ticker in self.tradable_markets:
            market_history_params = {'ticker':ticker, 'depth': 1}
            orderbook_response = self.exchange_client.get_orderbook(**market_history_params)
            market_asks[title+subtitle] = orderbook_response["orderbook"]["yes"][0]

        return market_asks
    
    def run(self):
        while 1:
            if time.time() - self.last_price_check >= 120:
                self.get_markets()

            pprint(self.get_asks())
            time.sleep(5)


        
    

algorithm = algo()
algorithm.run()