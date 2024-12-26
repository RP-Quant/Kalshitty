from utils.util import get_month_day, load_private_key_from_file, login
from config import API_BASE, KEY_ID
import asyncio
from datacollection.cryptorecord import CryptoRecorder
from datetime import datetime
import time

private_key = load_private_key_from_file("src/kalshi.key")

recorder = CryptoRecorder(api_base=API_BASE, key_id=KEY_ID, private_key=private_key)
while datetime.now().hour != 10:
    print("waiting...")
    time.sleep(1)

asyncio.run(recorder.run())