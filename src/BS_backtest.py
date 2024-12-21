import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from scipy.stats import norm
import numpy as np

df = pd.read_csv("src/records/DEC2012.csv")

# Parameters
ticker = "KXBTCD-24DEC2012-T95249.99"
LOWER = 95250
EXPIRY = pd.Timestamp('2024-12-20 12:00:00').tz_localize("US/Eastern").tz_convert("UTC")

slope, intercept = 1.9006255565649333e-13, 0.0006782181344299619

# Safely create a copy of the relevant data
market_data = df[["time", "BTC"]].copy()

# Add new columns explicitly
market_data["yes_ask"] =  df[ticker]
market_data["time"] = pd.to_datetime(market_data["time"])
print(market_data.head())

btc = yf.Ticker("BTC-USD")
DATA = btc.history(period="5d", interval="1m")
# print(DATA.head())
# print(DATA.tail())

def predict(row):
    end_time = pd.Timestamp(row["time"]).tz_localize("US/Eastern").tz_convert("UTC")
    curr = row["BTC"]
    TTE = EXPIRY-end_time
    TTE = TTE.total_seconds()//60
    print(TTE)

    # Fetch historical data
    

    # Filter up to end_time
    filtered_data = DATA[DATA.index <= end_time]
    if filtered_data.empty:
        print(end_time)
        raise ValueError("Historical data is empty. Check the end_time or data range.")

    #data = data.tail(300)
    past_hour = filtered_data.tail(60)
    #nonzero = (past_hour['Volume'] != 0).sum()
    past_hour_volume = sum(past_hour["Volume"].values)
    print(past_hour_volume)
    
    # Compute Returns
    filtered_data["Returns"] = np.log(filtered_data["Close"] / filtered_data["Close"].shift(1))
    filtered_data = filtered_data.dropna()

    # Calculate drift and volatility
    drift = 0  # Assuming drift is 0 for simplicity
    #volatility = filtered_data["Returns"].std()

    volatility = slope*past_hour_volume+intercept

    # Define helper function for CDF
    def c(tau, strike, b, mu, sigma):
        return (np.log(strike / b) - tau * mu) / (np.sqrt(tau) * sigma)

    # Compute probabilities
    p1 = norm.cdf(c(tau=TTE, strike=LOWER, b=curr, mu=drift, sigma=volatility))
    
    return 100*(1-p1)

market_data = market_data.copy()  # Create a copy of the slice to avoid the warning
market_data["prediction"] = market_data.apply(predict, axis=1)  # Apply predict
#market_data["prediction"] = market_data["prediction"].shift(TTE//10)  # Shift the predictions by 6 rows
market_data = market_data.dropna()  # Drop NaNs caused by the shift
print(market_data.head())
#idk_ask = market_data.loc[market_data['prediction'] - market_data['yes_ask'] >= 5, ['prediction', 'time']].values.tolist()
#idk_bid = market_data.loc[market_data['prediction'] - market_data['yes_bid'] <= -5, ['prediction', 'time']].values.tolist()


import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Assuming `market_data` and `ticker` are defined and the data is already processed
# Replace `market_data["prediction"]` and `market_data[ticker]` with your actual columns
# Make sure `TTE` is defined somewhere if you want to include it in the title.

fig = make_subplots(rows=2, cols=1)

# Plot the Kalshi Ask (blue line) on the first subplot
fig.add_trace(go.Scatter(
    x=market_data["time"],  # Use the index or any column with time data
    y=market_data["yes_ask"],  # The Kalshi Ask price
    mode='lines',
    name="Yes Ask",  # Label for the Kalshi Ask line
    line=dict(color='red', dash='dash')
), row=1, col=1)  # Correct way to specify row and col

# fig.add_trace(go.Scatter(
#     x=market_data["time"],  # Use the index or any column with time data
#     y=market_data["yes_bid"],  # The Kalshi Ask price
#     mode='lines',
#     name="Yes Bid",  # Label for the Kalshi Ask line
#     line=dict(color='green', dash='dash')
# ), row=1, col=1)  # Correct way to specify row and col

# fig.add_trace(go.Scatter(
#     x=market_data["time"],  # Use the index or any column with time data
#     y=market_data["no_ask"],  # The Kalshi Ask price
#     mode='lines',
#     name="No Ask",  # Label for the Kalshi Ask line
#     line=dict(color='orange', dash='dash')
# ), row=1, col=1)  # Correct way to specify row and col

# fig.add_trace(go.Scatter(
#     x=market_data["time"],  # Use the index or any column with time data
#     y=market_data["no_bid"],  # The Kalshi Ask price
#     mode='lines',
#     name="No Bid",  # Label for the Kalshi Ask line
#     line=dict(color='yellow', dash='dash')
# ), row=1, col=1)  # Correct way to specify row and col

# Plot the Fair Price (green line) on the first subplot
fig.add_trace(go.Scatter(
    x=market_data["time"],  # Use the index or any column with time data
    y=market_data["prediction"],  # The calculated Fair Price
    mode='lines',
    name=f"Fair Price",  # Label for the Fair Price line
    line=dict(color='blue')
), row=1, col=1)  # Correct way to specify row and col

# Plot the BTC Price (red line) on the second subplot
fig.add_trace(go.Scatter(
    x=market_data["time"],  # Use the index or any column with time data
    y=market_data["BTC"],  # The BTC price
    mode='lines',
    name="BTC Price",  # Label for the BTC Price line
    line=dict(color='red')
), row=2, col=1)  # Correct way to specify row and col

# for idfk, time in idk_ask:
#     fig.add_shape(
#         type='line',  # Shape type is line
#         x0=time,  # Start of the line (x-coordinate)
#         x1=market_data.iloc[-1]['time'],  # End of the line (x-coordinate)
#         y0=idfk,  # Y-coordinate for the horizontal line (adjust as needed)
#         y1=idfk,  # Y-coordinate for the horizontal line (adjust as needed)
#         line=dict(
#             color='purple',  # Line color
#             width=2,  # Line width
#             dash='dash'  # Dash type for the line (dashed)
#         ),
#         row=1, col=1  # Apply the shape to the second subplot
#     )

# for idfk, time in idk_bid:
#     fig.add_shape(
#         type='line',  # Shape type is line
#         x0=time,  # Start of the line (x-coordinate)
#         x1=market_data.iloc[-1]['time'],  # End of the line (x-coordinate)
#         y0=idfk,  # Y-coordinate for the horizontal line (adjust as needed)
#         y1=idfk,  # Y-coordinate for the horizontal line (adjust as needed)
#         line=dict(
#             color='black',  # Line color
#             width=2,  # Line width
#             dash='dash'  # Dash type for the line (dashed)
#         ),
#         row=1, col=1  # Apply the shape to the second subplot
#     )

# if UPPER:
#     fig.add_shape(
#         type='line',  # Shape type is line
#         x0=market_data.iloc[0]['time'],  # Start of the line (x-coordinate)
#         x1=market_data.iloc[-1]['time'],  # End of the line (x-coordinate)
#         y0=UPPER,  # Y-coordinate for the horizontal line (adjust as needed)
#         y1=UPPER,  # Y-coordinate for the horizontal line (adjust as needed)
#         line=dict(
#             color='black',  # Line color
#             width=2,  # Line width
#             dash='dash'  # Dash type for the line (dashed)
#         ),
#         row=2, col=1  # Apply the shape to the second subplot
#     )

fig.add_shape(
    type='line',  # Shape type is line
    x0=market_data.iloc[0]['time'],  # Start of the line (x-coordinate)
    x1=market_data.iloc[-1]['time'],  # End of the line (x-coordinate)
    y0=LOWER,  # Y-coordinate for the horizontal line (adjust as needed)
    y1=LOWER,  # Y-coordinate for the horizontal line (adjust as needed)
    line=dict(
        color='black',  # Line color
        width=2,  # Line width
        dash='dash'  # Dash type for the line (dashed)
    ),
    row=2, col=1  # Apply the shape to the second subplot
)

# Add labels, title, and axis titles
fig.update_layout(
    title=f"Kalshi Ask vs Fair Price for {ticker}",
    xaxis_title="Time",  # Adjust this if you want to label the x-axis differently
    yaxis_title="Price",  # Common y-axis title for both subplots
    legend_title="Legend",
    showlegend=True
)

# Optional: Update each subplot with separate y-axis titles
fig.update_yaxes(title_text="Price (Kalshi Ask & Fair Price)", row=1, col=1)
fig.update_yaxes(title_text="BTC Price", row=2, col=1)
fig.update_xaxes(type='date', row=1, col=1)
fig.update_xaxes(type='date', row=2, col=1)

# Show the plot
fig.show()
