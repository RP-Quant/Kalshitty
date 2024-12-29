import requests
from pprint import pprint

endpoint = "https://gamma-api.polymarket.com/markets?slug=bitcoin-above-94000-on-january-3"

r = requests.get(endpoint)
response = r.json()[0]

print(response['outcomePrices'])
print(response['clobTokenIds'])