import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from scipy.stats import norm
import numpy as np

df = pd.read_csv("btc_price_record.csv")
ticker = "KXBTC-24DEC0517-B100500"
UPPER = 100_750
LOWER = 100_250
TTE = 60

market_data = df[["time", "BTC", ticker]]

def predict(row):
    end_time = pd.Timestamp(row["time"]).tz_localize("UTC")
    curr = row["BTC"]

    # Fetch historical data
    btc = yf.Ticker("BTC-USD")
    data = btc.history(period="5d", interval="1m")

    # Filter up to end_time
    data = data[data.index <= end_time]
    if data.empty:
        raise ValueError("Historical data is empty. Check the end_time or data range.")
    
    # Compute Returns
    data["Returns"] = np.log(data["Close"] / data["Close"].shift(1))
    data = data.dropna()

    # Calculate drift and volatility
    drift = 0  # Assuming drift is 0 for simplicity
    volatility = data["Returns"].std()

    # Define helper function for CDF
    def c(tau, strike, b, mu, sigma):
        return (np.log(strike / b) - tau * mu) / (np.sqrt(tau) * sigma)

    # Compute probabilities
    p1 = norm.cdf(c(tau=TTE, strike=LOWER, b=curr, mu=drift, sigma=volatility))
    p2 = 1
    if UPPER:
        p2 = norm.cdf(c(tau=TTE, strike=UPPER, b=curr, mu=drift, sigma=volatility))
    
    return 100*(p2 - p1)

market_data = market_data.copy()  # Create a copy of the slice to avoid the warning
market_data["prediction"] = market_data.apply(predict, axis=1)  # Apply predict
market_data["prediction"] = market_data["prediction"].shift(6)  # Shift the predictions by 6 rows
market_data = market_data.dropna()  # Drop NaNs caused by the shift

import plotly.graph_objects as go

# Assuming `market_data` and `ticker` are defined and the data is already processed
# Replace `market_data["prediction"]` and `market_data[ticker]` with your actual columns

fig = go.Figure()

# Plot the Kalshi Ask (blue line)
fig.add_trace(go.Scatter(
    x=market_data.index,  # Use the index or any column with time data
    y=market_data[ticker],  # The Kalshi Ask price
    mode='lines',
    name="Kalshi Ask",  # Label for the Kalshi Ask line
    line=dict(color='blue')
))

# Plot the Fair Price (green line)
fig.add_trace(go.Scatter(
    x=market_data.index,  # Use the index or any column with time data
    y=market_data["prediction"],  # The calculated Fair Price
    mode='lines',
    name=f"Fair Price Calculated {TTE} Minutes Ago",  # Label for the Fair Price line
    line=dict(color='green')
))

# Add labels and title
fig.update_layout(
    title=f"Kalshi Ask vs Fair Price for {ticker}",
    xaxis_title="Time",  # Adjust this if you want to label the x-axis differently
    yaxis_title="Price",
    legend_title="Legend"
)

# Show the plot
fig.show()
