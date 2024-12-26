from strategies.cryptoarbitrage import BTCArbitrage, ETHArbitrage
from config import API_BASE, KEY_ID
from utils.util import load_private_key_from_file
import asyncio

if __name__ == "__main__":
    private_key = load_private_key_from_file("src/kalshi.key")
    #token = login()
    btc_arb = BTCArbitrage(api_base=API_BASE, key_id=KEY_ID, private_key=private_key, threshold=2, prod=True, mode="sbb")

    #eth_arb = ETHArbitrage(api_base=API_BASE, key_id=KEY_ID, private_key=private_key, threshold=2, prod=False, mode="sbb")
    
    asyncio.run(btc_arb.run())