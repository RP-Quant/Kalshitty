from strategies.cryptoarbitrage import BTCArbitrage
from config import API_BASE, KEY_ID, EMAIL, PASSWORD
from utils.util import load_private_key_from_file
import asyncio
import requests

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

if __name__ == "__main__":
    private_key = load_private_key_from_file("src/kalshi.key")
    token = login()
    #btc1_arb = BTCArbitrage(api_base=API_BASE, key_id=KEY_ID, private_key=private_key, auth_token=token, threshold=2, prod=False, mode="sbb")
    btc2_arb = BTCArbitrage(api_base=API_BASE, key_id=KEY_ID, private_key=private_key, auth_token=token, threshold=2, prod=False, mode="bss")
    async def main():
        #t1 = asyncio.create_task(btc1_arb.run())
        t2 = asyncio.create_task(btc2_arb.run())

        #await t1
        await t2
    
    asyncio.run(main())