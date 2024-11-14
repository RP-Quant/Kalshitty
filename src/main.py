from arbitrage import SpreadCover, Mint
from config import KEY_ID, BTC_PRICE_TICKER, BTC_PRICE_RANGE_TICKER, ETH_PRICE_TICKER, ETH_PRICE_RANGE_TICKER
from util import load_private_key_from_file

private_key = load_private_key_from_file("src/kalshi.key")
api_base = "https://api.elections.kalshi.com/trade-api/v2"

arb = Mint(api_base=api_base, key_id=KEY_ID, private_key=private_key, above_event=BTC_PRICE_TICKER, between_event=BTC_PRICE_RANGE_TICKER, side="yes")
arb.run()