from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from selenium.webdriver.common.by import By
from selenium import webdriver
import re

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

class Webscraper:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)

    def get_BTC_price(self):
        endpoint = "https://www.cfbenchmarks.com/data/indices/BRTI?ref=blog.cfbenchmarks.com"
        self.driver.get(endpoint)
        return filter_digits(self.driver.find_element(By.CSS_SELECTOR, r'span.text-sm.font-semibold.tabular-nums.md\:text-2xl').text)