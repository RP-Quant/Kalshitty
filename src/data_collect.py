from strategies.cryptoarbitrage import BTCArbitrage
import asyncio
from config import API_BASE, KEY_ID
from utils.util import load_private_key_from_file, Webscraper
from datetime import datetime
import pandas as pd
import atexit

private_key = load_private_key_from_file("src/kalshi.key")
btc_arb = BTCArbitrage(api_base=API_BASE, key_id=KEY_ID, private_key=private_key, threshold=3, prod=False, mode="sbb")
ws = Webscraper()

# btc_arb.above_event.initialize()
# btc_arb.range_event.initialize()

fieldnames = ["time", "BTC"] + btc_arb.get_markets()
print(fieldnames)
# yes_df = pd.DataFrame(columns=fieldnames)
# no_df = pd.DataFrame(columns=fieldnames)

yes_df = pd.read_csv("DEC6_KALSHI_YES.csv")
no_df = pd.read_csv("DEC6_KALSHI_NO.csv")

# Function to asynchronously listen for data
async def listen():
    try:
        while True:
            # Get the current time
            n = datetime.now()

            # Check if it's the start of a new minute
            if n.second == 0:
                # Record "yes" and "no" data from btc_arb
                yes, no = await btc_arb.record()
                
                # Get the current BTC price from the WebSocket
                curr_price = ws.get_BTC_price()

                # Update the BTC price in both "yes" and "no" DataFrames
                yes["BTC"] = curr_price
                no["BTC"] = curr_price
                
                # Print the data to check
                print(yes, no)

                # Append data to DataFrames (this can be optimized for performance)
                yes_df.loc[len(yes_df)] = yes.values()
                no_df.loc[len(no_df)] = no
                print("data written to DataFrames")
                print(yes_df, no_df)

            # Wait 1 second before checking again
            await asyncio.sleep(1)
    
    except Exception as e:
        print(f"An error occurred: {e}")

def save_to_csv():
    print("Saving data to CSV files...")
    yes_df.to_csv("DEC6_KALSHI_YES.csv", index=False)
    no_df.to_csv("DEC6_KALSHI_NO.csv", index=False)
    print("Data saved to files.")

# Register the save function to be called upon program termination
atexit.register(save_to_csv)

async def main():
    t1 = asyncio.create_task(btc_arb.run())
    t2 = asyncio.create_task(listen())

    await t1
    await t2

asyncio.run(main())