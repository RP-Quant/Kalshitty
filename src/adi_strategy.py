from strategy import Strategy
from config import KEY_ID
from util import load_private_key_from_file
from datetime import datetime
from pytz import timezone
import time
from registry import Registry

private_key = load_private_key_from_file("src/kalshi.key")
api_base = "https://api.elections.kalshi.com/trade-api/v2"

BTC_PRICE_TICKER = "KXBTCD-"
BTC_PRICE_RANGE_TICKER = "KXBTC-"

months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

tz = timezone('EST')
time = datetime.now(tz)

day = time.day

# if it's past 5 pm, use tomorrow's day
if time.hour >= 17:
    day += 1

BTC_PRICE_TICKER += str(time.year)[2:] + months[time.month - 1] + str(day) + "17"
BTC_PRICE_RANGE_TICKER += str(time.year)[2:] + months[time.month - 1] + str(day) + "17"

registry = Registry()
event_tickers = [BTC_PRICE_TICKER]
strat = Strategy(api_base=api_base, key_id=KEY_ID, private_key=private_key, registry=registry, event_tickers=event_tickers)
strat.run()
# s = datetime.now()
# print(strat.get_data_for_event(BTC_PRICE_TICKER))
# print(datetime.now() - s)