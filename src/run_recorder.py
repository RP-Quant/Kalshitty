from utils.util import get_month_day, load_private_key_from_file, login
from config import API_BASE, KEY_ID
import asyncio
from datacollection.cryptorecord import CryptoRecorder

private_key = load_private_key_from_file("src/kalshi.key")
token = login()

recorder = CryptoRecorder(api_base=API_BASE, key_id=KEY_ID, private_key=private_key, auth_token=token)
asyncio.run(recorder.run())