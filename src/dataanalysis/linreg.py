import yfinance as yf
from scipy.stats import linregress
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

btc = yf.Ticker("BTC-USD")
volume_data = btc.history(period="5d", interval="1h")["Volume"]
volatility_data = btc.history(period="5d", interval="1m")

data = tuple(volume_data.items())

def get_volatility(data):
    data["Returns"] = np.log(data["Close"] / data["Close"].shift(1))
    data = data.dropna()

    return data["Returns"].std()

volumes = []
volatilities = []

for i in range(len(data)-1):
    start_time, volume = data[i]
    end_time, _ = data[i+1]

    closes = volatility_data[
        (volatility_data.index >= pd.Timestamp(start_time)) &
        (volatility_data.index < pd.Timestamp(end_time))
    ].copy()

    #if volume > 0.1*10**10:
    volumes.append(volume)
    volatilities.append(get_volatility(closes))

x = np.array(volumes)
y = np.array(volatilities)

slope, intercept, r_value, p_value, std_err = linregress(x, y)

# Print results
print(f"Slope: {slope}")
print(f"Intercept: {intercept}")
print(f"R-squared: {r_value**2}")

# Prediction
y_pred = slope * x + intercept

# Plot data and regression line
plt.scatter(x, y, label="Data")
plt.plot(x, y_pred, color='red', label="Fitted line")
plt.legend()
plt.xlabel("X")
plt.ylabel("Y")
plt.title("Linear Regression with scipy.stats.linregress")
plt.show()





