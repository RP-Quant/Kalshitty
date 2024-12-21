import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from utils.util import Webscraper
from utils.KalshiClient import ExchangeClient
from config import API_BASE, KEY_ID
from utils.util import load_private_key_from_file, filter_digits
import math
import asyncio
import csv
from datetime import datetime, timedelta
import time

ws = Webscraper()

slope, intercept = 1.9006255565649333e-13, 0.0006782181344299619

# Asynchronous prediction function
def get_prediction(tte, lower, upper=None):
    btc = yf.Ticker("BTC-USD")
    data = btc.history(period="5d", interval="1m")
    data["Returns"] = np.log(data["Close"] / data["Close"].shift(1))
    data = data.dropna()

    past_hour_volume = sum(data.tail(60)["Volume"].values)

    N = len(data)
    drift = 0  # Assuming drift is 0 for simplicity
    #volatility = data["Returns"].std()
    volatility = slope*past_hour_volume+intercept
    tau = tte
    curr = ws.get_BTC_price()

    def c(tau, strike, b, mu, sigma):
        return (np.log(strike / b) - tau * mu) / (np.sqrt(tau) * sigma)

    p1 = norm.cdf(c(tau=tau, strike=lower, b=curr, mu=drift, sigma=volatility))
    p2 = 1
    if upper:
        p2 = norm.cdf(c(tau=tau, strike=upper, b=curr, mu=drift, sigma=volatility))
    return p2 - p1

while 1:
    for strike in [97000, 97250, 97500]:
        print(strike, ": ", get_prediction(60-datetime.now().minute, strike, None))
    print("===========================")
    time.sleep(1)
