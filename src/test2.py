from util import get_BTC_http
import time
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

data = []
n = 300
prev = 0

while len(data) < n + 1:
    # s = time.time()
    curr = get_BTC_http()
    if int(curr * 100) != int(prev * 100):
        data.append(curr)
    prev = curr
    # print(p, "time", time.time() - s)

data = pd.Series(data)

log_returns = np.log(data / data.shift(1))
log_returns = log_returns.dropna()
print(log_returns)


log_returns.hist(bins = 10)
plt.show()