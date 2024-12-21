from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from selenium.webdriver.common.by import By
from selenium import webdriver
import re
import math
from datetime import datetime
import requests
from config import EMAIL, PASSWORD

def load_private_key_from_file(file_path):
    with open(file_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,  # or provide a password if your key is encrypted
            backend=default_backend()
        )
    return private_key

def filter_digits(input_string):
    return float(''.join(re.findall(r'[\d.]', input_string)))
def login():
    try:
        r = requests.post(
            "https://api.elections.kalshi.com/trade-api/v2/login",
            json={"email": EMAIL, "password": PASSWORD}
        )
        r.raise_for_status()  # Raise exception for HTTP errors
        response = r.json()
        token = response.get("token")
        if not token:
            raise ValueError("No token in response")
        return token
    except Exception as e:
        print(f"Error during authentication: {e}")
        exit(1)
class Webscraper:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)

    def get_BTC_price(self):
        endpoint = "https://www.cfbenchmarks.com/data/indices/BRTI?ref=blog.cfbenchmarks.com"
        self.driver.get(endpoint)
        return filter_digits(self.driver.find_element(By.CSS_SELECTOR, r'span.text-sm.font-semibold.tabular-nums.md\:text-2xl').text)
    
def calc_fees(chance, num_contracts): # returns in USD, not cents
    return math.ceil((chance/100)*(1-chance/100)*num_contracts*0.07*100)/100

def cut_down(num):
    return ((math.ceil(num)-250)//500)-156 #bitcoin cut down
    #return ((math.ceil(num))//40)-60 #ethereum cut down

def get_month_day():
    current_date = datetime.now()
    month_code = current_date.strftime("%b")  # 3-letter month code
    day_code = current_date.strftime("%d")
    return month_code, day_code

def get_digits(inp: str):
    return int(''.join([i for i in inp if str.isdecimal(i)]))