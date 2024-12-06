from arbitrage2 import BTCArbitrage, ETHArbitrage
from config import API_BASE, KEY_ID
from util import load_private_key_from_file
import asyncio

if __name__ == "__main__":
    private_key = load_private_key_from_file("src/kalshi.key")
    btc1_arb = BTCArbitrage(api_base=API_BASE, key_id=KEY_ID, private_key=private_key, threshold=2, prod=True, mode="sbb")
    btc2_arb = BTCArbitrage(api_base=API_BASE, key_id=KEY_ID, private_key=private_key, threshold=2, prod=True, mode="bss")
    async def main():
        t1 = asyncio.create_task(btc1_arb.run())
        t2 = asyncio.create_task(btc2_arb.run())

        await t1
        await t2
    
    asyncio.run(main())