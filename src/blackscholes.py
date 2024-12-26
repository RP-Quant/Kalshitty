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

coef_volume = 1.4256347818436605e-13
coef_volatility = 0.49007674857889527
intercept = 0.00033010979511836235

# Asynchronous prediction function
# Updated prediction function with coefficients for volume and past volatility
def get_prediction(tte, lower, upper=None, coef_volume=coef_volume, coef_volatility=coef_volatility, intercept=intercept):
    # Fetch BTC data
    btc = yf.Ticker("BTC-USD")
    data = btc.history(period="5d", interval="1m")
    
    # Calculate returns
    data["Returns"] = np.log(data["Close"] / data["Close"].shift(1))
    data = data.dropna()

    # Calculate past hour metrics
    past_hour_data = data.tail(60)  # Last 60 minutes
    past_hour_volume = sum(past_hour_data["Volume"].values)
    past_hour_volatility = past_hour_data["Returns"].std()

    # Calculate volatility using coefficients
    volatility = (
        coef_volume * past_hour_volume + 
        coef_volatility * past_hour_volatility + 
        intercept
    )

    # Time to expiry (tau)
    tau = tte
    drift = 0  # Assuming drift is 0 for simplicity

    # Get current BTC price
    curr = ws.get_BTC_price()

    # Black-Scholes function for cumulative distribution
    def c(tau, strike, b, mu, sigma):
        return (np.log(strike / b) - tau * mu) / (np.sqrt(tau) * sigma)

    # Compute probabilities
    p1 = norm.cdf(c(tau=tau, strike=lower, b=curr, mu=drift, sigma=volatility))
    p2 = 1
    if upper:
        p2 = norm.cdf(c(tau=tau, strike=upper, b=curr, mu=drift, sigma=volatility))
    return p2 - p1


while 1:
    for strike in [99750]:
        print(strike, ": ", get_prediction(60-datetime.now().minute, strike, None))
    print("===========================")
    time.sleep(0.1)
