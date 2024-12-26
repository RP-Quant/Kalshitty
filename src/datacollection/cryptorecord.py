from datacollection.DataListeners import EventListener
from utils.util import get_month_day, Webscraper
from utils.KalshiClient import ExchangeClient
import asyncio
from datetime import datetime
from pandas import DataFrame
import pandas as pd

class CryptoRecorder:
    def __init__(self, api_base, key_id: str, private_key):
        month, day = get_month_day()
        self.ticker = "KX" + "BTC" + "D-24" + month.upper() + str(day) + "12"

        self.exchange_client = ExchangeClient(api_base, key_id, private_key)
        self.event = EventListener(exchange_client=self.exchange_client, private_key=private_key, key_id=key_id, event_ticker=self.ticker)
        self.webscraper = Webscraper()
        self.df = None

    def set_df(self):
        self.df = DataFrame(columns=["time", "BTC"] + list(self.event.get_market_tickers()))

    async def start_record(self):
        print("Starting recording...")
        while True:
            print(datetime.now().second)
            if datetime.now().second == 0 and datetime.now().hour==10:
                print("recording...")
                data_raw = await self.event.get_snapshot("yes")
                data = {"time": datetime.now(),
                        "BTC" : self.webscraper.get_BTC_price()} 
                for market in data_raw:
                    data[market] = data_raw[market][1]
                print(data)
                self.df = pd.concat([self.df, pd.DataFrame([data])], ignore_index=True)
            if datetime.now().hour>11:
                self.df.to_csv("src/records/DEC2411.csv")
                print("Ending collection")
                break
            await asyncio.sleep(1)

    async def run(self):
        self.set_df()
        listen = asyncio.create_task(self.event.start_listen())
        record = asyncio.create_task(self.start_record())

        try:
            while True:
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            print("Main loop cancelled. Cleaning up...")
        finally:
            listen.cancel()
            record.cancel()
            
            try:
                await listen
                await record
            except asyncio.CancelledError:
                pass