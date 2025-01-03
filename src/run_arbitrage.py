from strategies.cryptoarbitrage import BTCArbitrage
from config import API_BASE, KEY_ID, EMAIL, PASSWORD
from utils.util import load_private_key_from_file, login
import asyncio
import requests

if __name__ == "__main__":
    private_key = load_private_key_from_file("src/kalshi.key")
    #token = login()
    btc_arb = BTCArbitrage(api_base=API_BASE, key_id=KEY_ID, private_key=private_key, threshold=2, prod=False, mode="sbb")
    
    asyncio.run(btc_arb.run())