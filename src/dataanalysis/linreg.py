import yfinance as yf
from scipy.optimize import curve_fit
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Download BTC data
btc = yf.Ticker("BTC-USD")

# Get volume and volatility data
volume_data = btc.history(period="5d", interval="1h")["Volume"]
volatility_data = btc.history(period="5d", interval="1m")

# Convert volume data to tuples
data = list(volume_data.items())

# Function to calculate volatility
def get_volatility(data):
    if data.empty:  # Handle empty data
        return np.nan
    data["Returns"] = np.log(data["Close"] / data["Close"].shift(1))
    data = data.dropna()
    return data["Returns"].std()

# Initialize lists
volumes = []
volatilities = []
past_hour_volatilities = []

# Loop through each volume timestamp and calculate volatilities
for i in range(len(data) - 1):
    # Current interval
    start_time, volume = data[i]
    end_time, _ = data[i + 1]

    # Get minute-level data for current interval
    closes = volatility_data[
        (volatility_data.index >= pd.Timestamp(start_time)) &
        (volatility_data.index < pd.Timestamp(end_time))
    ].copy()

    # Get minute-level data for the past hour
    past_closes = volatility_data[
        (volatility_data.index >= pd.Timestamp(start_time) - pd.Timedelta(hours=1)) &
        (volatility_data.index < pd.Timestamp(start_time))
    ].copy()

    # Compute volatilities
    vol = get_volatility(closes)
    past_vol = get_volatility(past_closes)

    # Collect data points
    if not np.isnan(vol) and not np.isnan(past_vol):  # Filter valid data
        volumes.append(volume)
        volatilities.append(vol)
        past_hour_volatilities.append(past_vol)

# Convert to numpy arrays
X1 = np.array(volumes)
X2 = np.array(past_hour_volatilities)
Y = np.array(volatilities)

# Define the regression model: y = a1*x1 + a2*x2 + c
def model(X, a1, a2, c):
    x1, x2 = X
    return a1 * x1 + a2 * x2 + c

# Perform curve fitting
popt, pcov = curve_fit(model, (X1, X2), Y)
a1, a2, c = popt

print(f"Coefficients: a1 = {a1}, a2 = {a2}")
print(f"Intercept: c = {c}")

# Predictions
Y_pred = model((X1, X2), a1, a2, c)

# Calculate R²
residuals = Y - Y_pred
ss_res = np.sum(residuals**2)  # Residual sum of squares
ss_tot = np.sum((Y - np.mean(Y))**2)  # Total sum of squares
r_squared = 1 - (ss_res / ss_tot)

# Adjusted R²
n = len(Y)  # Number of observations
p = 2       # Number of predictors (X1, X2)
adjusted_r_squared = 1 - (1 - r_squared) * ((n - 1) / (n - p - 1))

print(f"R-squared: {r_squared}")
print(f"Adjusted R-squared: {adjusted_r_squared}")

# Pearson Correlation Coefficients
corr_x1_y = np.corrcoef(X1, Y)[0, 1]
corr_x2_y = np.corrcoef(X2, Y)[0, 1]

print(f"Correlation between Volume and Volatility: {corr_x1_y}")
print(f"Correlation between Past Hour Volatility and Current Volatility: {corr_x2_y}")

# Plot results
fig = plt.figure(figsize=(10, 6))
ax = fig.add_subplot(111, projection='3d')

ax.scatter(X1, X2, Y, label="Data")
ax.scatter(X1, X2, Y_pred, color='red', label="Fitted line")

ax.set_xlabel("Volume")
ax.set_ylabel("Past Hour Volatility")
ax.set_zlabel("Volatility")
ax.set_title("Multiple Linear Regression with Correlation")
plt.legend()
plt.show()
