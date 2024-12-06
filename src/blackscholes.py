import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from util import Webscraper
from KalshiClientsBaseV2ApiKey import ExchangeClient
from config import API_BASE, KEY_ID
from util import load_private_key_from_file, filter_digits
import math
import asyncio
from marketdata import Event
import csv
from datetime import datetime, timedelta

private_key = load_private_key_from_file("src/kalshi.key")

ec = ExchangeClient(exchange_api_base=API_BASE, key_id=KEY_ID, private_key=private_key)
ws = Webscraper()

# Asynchronous prediction function
def get_prediction(tte, lower, upper=None):
    btc = yf.Ticker("BTC-USD")
    data = btc.history(period="5d", interval="1m")
    data["Returns"] = np.log(data["Close"] / data["Close"].shift(1))
    data = data.dropna()

    N = len(data)
    drift = 0  # Assuming drift is 0 for simplicity
    volatility = data["Returns"].std()
    tau = tte
    curr = ws.get_BTC_price()

    def c(tau, strike, b, mu, sigma):
        return (np.log(strike / b) - tau * mu) / (np.sqrt(tau) * sigma)

    p1 = norm.cdf(c(tau=tau, strike=lower, b=curr, mu=drift, sigma=volatility))
    p2 = 1
    if upper:
        p2 = norm.cdf(c(tau=tau, strike=upper, b=curr, mu=drift, sigma=volatility))
    return p2 - p1

# Initialize events
btc_range_event = Event("KXBTC-24DEC0517", ec)
btc_above_event = Event("KXBTCD-24DEC0517", ec)
btc_range_event.initialize()
btc_above_event.initialize()

# Prepare CSV files
fieldnames = ["time", "BTC"] + btc_range_event.get_markets() + btc_above_event.get_markets()

async def record_predict():
    with open("btc_price_record.csv", "w", newline='', encoding="utf-8") as price_file:
        
        # Initialize CSV writers
        price_writer = csv.DictWriter(price_file, fieldnames=fieldnames)
        price_writer.writeheader()

        while True:
            now = datetime.now()
            if now.hour == 17:
                break

            if now.second == 0:  # Only log on the first second of each minute
                minute = now.minute
                if minute%10 == 0:
                    print(f"Logging data at {now}...")  # Debugging timestamp
                    
                    # Initialize data dictionaries
                    price_data = {"time": now, "BTC" : ws.get_BTC_price()}
                    #pred30_data = {"time": now}
                    #pred60_data = {"time": now}

                    for ticker in btc_above_event.get_markets():
                        strike = math.ceil(filter_digits(ticker.split("-")[-1]))
                        try:
                            market_data = await btc_above_event.get_data(ticker=ticker, side="no")
                            price_data[ticker] = 100 - market_data[1]
                            #     pred30_data[ticker] = get_prediction(tte=30, lower=strike, upper=None)
                            # if minute == 0:
                            #     pred60_data[ticker] = get_prediction(tte=60, lower=strike, upper=None)
                        except Exception as e:
                            print(f"Error processing {ticker}: {e}")

                    for ticker in btc_range_event.get_markets():
                        strike = math.ceil(filter_digits(ticker.split("-")[-1]))
                        try:
                            market_data = await btc_range_event.get_data(ticker=ticker, side="no")
                            price_data[ticker] = 100 - market_data[1]
                            #     pred30_data[ticker] = get_prediction(tte=30, lower=strike - 250, upper=strike + 250)
                            # if minute == 0:
                            #     pred60_data[ticker] = get_prediction(tte=60, lower=strike - 250, upper=strike + 250)
                        except Exception as e:
                            print(f"Error processing {ticker}: {e}")

                    # Write to CSV files and flush to ensure immediate writing
                    print(f"Writing data to files for {now}")  # Debugging write
                    price_writer.writerow(price_data)
                    # pred30_writer.writerow(pred30_data)
                    # pred60_writer.writerow(pred60_data)
                    price_file.flush()
                    # pred30_file.flush()
                    # pred60_file.flush()

            await asyncio.sleep(1)  # Prevent tight loop

async def main():
    t1 = asyncio.create_task(btc_above_event.start_listen())
    t2 = asyncio.create_task(btc_range_event.start_listen())
    t3 = asyncio.create_task(record_predict())

    await asyncio.gather(t1, t2, t3)

# Run the program
#asyncio.run(main())

print(get_prediction(60, 96750, None))