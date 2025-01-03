import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
# from utils.util import Webscraper
from utils.KalshiClient import ExchangeClient
from config import API_BASE, KEY_ID
from utils.util import load_private_key_from_file, filter_digits
import math
import asyncio
import csv
from datetime import datetime, timedelta
import time
from pytz import timezone

btc = yf.Ticker("BTC-USD")
data = btc.history(period="5d", interval="1m")
data["Returns"] = np.log(data["Close"] / data["Close"].shift(1))
data = data.dropna()

past_hour_volume = sum(data.tail(60)["Volume"].values)

N = len(data)
drift = 0  # Assuming drift is 0 for simplicity
volatility1 = data["Returns"].std() * 10000

data = btc.history(period="1d", interval="1m")
data["Returns"] = np.log(data["Close"] / data["Close"].shift(1))
data = data.dropna()

past_hour_volume = sum(data.tail(60)["Volume"].values)

N = len(data)
drift = 0  # Assuming drift is 0 for simplicity
volatility2 = data["Returns"].std() * 10000

data = btc.history(period="1d", interval="1m").tail(120)[:60]
data["Returns"] = np.log(data["Close"] / data["Close"].shift(1))
data = data.dropna()


N = len(data)
drift = 0  # Assuming drift is 0 for simplicity
volatility3 = data["Returns"].std() * 10000

print(volatility1, volatility2, volatility3)