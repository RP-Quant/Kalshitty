import csv
import asyncio
from datetime import datetime
from marketdata import Event
from config import API_BASE, KEY_ID
from KalshiClientsBaseV2ApiKey import ExchangeClient
from util import load_private_key_from_file, Webscraper

# Load private key and initialize Exchange Client
private_key = load_private_key_from_file("src/kalshi.key")
ec = ExchangeClient(exchange_api_base=API_BASE, key_id=KEY_ID, private_key=private_key)
ws = Webscraper()

# Initialize events
btc_range_event = Event("KXBTC-24DEC0417", ec)
btc_above_event = Event("KXBTCD-24DEC0417", ec)
btc_range_event.initialize()
btc_above_event.initialize()

range_markets = btc_range_event.get_markets()
above_markets = btc_above_event.get_markets()

fieldnames = ["time", "BTC"] + range_markets + above_markets

yes_file = open("btc_morning_record_yes.csv", "w", newline='', encoding="utf-8")
yes_writer = csv.DictWriter(yes_file, fieldnames=fieldnames)
yes_writer.writeheader()

no_file = open("btc_morning_record_no.csv", "w", newline='', encoding="utf-8")
no_writer = csv.DictWriter(no_file, fieldnames=fieldnames)
no_writer.writeheader()

async def record():
    try:
        while now := datetime.now():
            if int(now.strftime("%M")) > 20:
                break
            
            current_btc = ws.get_BTC_price()

            # Example of collecting data for each market
            yes_data = {"time" : now, "BTC" : current_btc}
            for market in range_markets:
                yes_data[market] = await btc_range_event.get_data(market, "yes")
            for market in above_markets:
                yes_data[market] = await btc_above_event.get_data(market, "yes")
                
            no_data = {"time" : now, "BTC" : current_btc}
            for market in range_markets:
                no_data[market] = await btc_range_event.get_data(market, "no")
            for market in above_markets:
                no_data[market] = await btc_above_event.get_data(market, "no")
            
            yes_writer.writerow(yes_data)
            no_writer.writerow(yes_data)
            print(f"Recorded data at {now}")
            
            await asyncio.sleep(5)  # Wait for 60 seconds before the next record
    finally:
        yes_file.close()
        no_file.close()
        print("File closed.")

if __name__ == "__main__":
    while datetime.now().strftime("%H") != "08":
        print("awaiting...")
    print(f"The BTC price is currently ${ws.get_BTC_price()}")
    async def main():
        t1 = asyncio.create_task(btc_above_event.start_listen())
        t2 = asyncio.create_task(btc_range_event.start_listen())
        t3 = asyncio.create_task(record())

        await t1
        await t2
        await t3

    asyncio.run(
        main()
    )
