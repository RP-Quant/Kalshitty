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
data = btc.history(period="1d", interval="1m")
data["Returns"] = np.log(data["Close"] / data["Close"].shift(1))
data = data.dropna()

past_hour_volume = sum(data.tail(60)["Volume"].values)

N = len(data)
drift = 0  # Assuming drift is 0 for simplicity
volatility = data["Returns"].std() * 1.5

# tau in minutes
# d1 = (np.log(S/K) + (s ** 2)/2 * tau) / (s * np.sqrt(tau))
# d2 = d1 - s * np.sqrt(tau)

# out = norm.cdf(d2)
# s = time.time()
def c(tau, strike, b, mu, sigma):
    return (np.log(strike / b) - tau * mu) / (np.sqrt(tau) * sigma)

def d(tau, currprice, k, volatility):
    d1 = (np.log(currprice / k) + (volatility ** 2) / 2 * tau) / (volatility * np.sqrt(tau))
    return norm.cdf(d1 - volatility * np.sqrt(tau))

t = [i/100 for i in range(100, 170)]
currs = [i for i in range(95000, 97000, 10)]
k = 96000
out = []
out2 = []
z = np.zeros((len(t), len(currs)))  # Pre-allocate the z array
z2 = np.zeros((len(t), len(currs)))  # Pre-allocate the z array

for i, curr in enumerate(currs):
    for j, m in enumerate(t):
        z[j, i] = d(15, curr, k, volatility * m)
        # z2[j, i] = 1 - norm.cdf(c(tau=20, strike=k, b=curr, mu=0, sigma=volatility * tau))  # Populate z directly

ax = plt.axes(projection='3d')
x, y = np.meshgrid(currs, t)  # Create meshgrid

# Plot the 3D surface
ax.plot_surface(x, y, z, cmap='viridis')
# ax.plot_surface(x, y, z2, cmap='viridis')

# Add axis labels
ax.set_xlabel('Strike Price (k)')
ax.set_ylabel('vol')
ax.set_zlabel('CDF Value')

plt.show()

# want vol s.t. chance with tau=15min is 90% at +500

# print(d(15, 95500, 96000, volatility*1.2))
# print(d(50, 95500, 96000, volatility*1.2))