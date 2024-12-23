import json
from datetime import datetime as dt
from urllib3.exceptions import HTTPError
from dateutil import parser
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from datetime import timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
import base64
import asyncio
import aiohttp
import time

class KalshiClient:
    """A simple client that allows utils to call authenticated Kalshi API endpoints."""
    def __init__(
        self,
        host: str,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        session: aiohttp.ClientSession,
        user_id: Optional[str] = None
    ):
        """Initializes the client and logs in the specified user.
        Raises an HttpError if the user could not be authenticated.
        """

        self.host = host
        self.key_id = key_id
        self.private_key = private_key
        self.user_id = user_id
        self.session = session

        self.get_requests = [0, time.time()]
        self.post_requests = [0, time.time()]
        self.mutex = asyncio.Lock()

        self.get_limit = 10 # limit per second
        self.post_limit = 10 # limit per second
        self.version = "V3"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async def post(self, path: str, body: dict) -> Any:
        """POSTs to an authenticated Kalshi HTTP endpoint.
        Returns the response body. Raises an HttpError on non-2XX results.
        """

        # check that we're within the rate limits
        async with self.mutex:
            curr_time = time.time()

            if curr_time - self.post_requests[1] > 1.05: # every 1.05 seconds, reset counting period (not 1 exactly for buffer)
                self.post_requests[0] = 0
                self.post_requests[1] = time.time()
                
            self.post_requests[0] += 1

            if self.post_requests[0] >= self.post_limit:
                print("Exceeded post rate limit, sleeping to reset it")
                await asyncio.sleep(1.05 - (curr_time - self.post_requests[1]))
                self.post_requests[0] = 1
                self.post_requests[1] = time.time()

        url = self.host + path
        headers = self.request_headers("POST", path)
        async with self.session.post(url, data=body, headers=headers) as response:
            await self.raise_if_bad_response(response)
            return await response.json()

    async def get(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """GETs from an authenticated Kalshi HTTP endpoint.
        Returns the response body. Raises an HttpError on non-2XX results."""
        # check that we're within the rate limits
        async with self.mutex:
            curr_time = time.time()

            if curr_time - self.get_requests[1] > 1.05: # every 1.05 seconds, reset counting period (not exactly 1 for buffer)
                self.get_requests[0] = 0
                self.get_requests[1] = time.time()
                
            self.get_requests[0] += 1

            if self.get_requests[0] >= self.get_limit:
                print("Exceeded get rate limit, sleeping to reset it")
                await asyncio.sleep(1.05 - (curr_time - self.get_requests[1]))
                self.get_requests[0] = 1
                self.get_requests[1] = time.time()
        
        url = self.host + path
        headers = self.request_headers("GET", path)
        async with self.session.get(url, headers=headers, params=params) as response:
            await self.raise_if_bad_response(response)
            return await response.json()

    async def delete(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """Deletes from an authenticated Kalshi HTTP endpoint.
        Returns the response body. Raises an HttpError on non-2XX results."""

        # check that we're within the rate limits
        async with self.mutex:
            curr_time = time.time()

            if curr_time - self.post_requests[1] > 1.05: # every 1.05 seconds, reset counting period (not 1 exactly for buffer)
                self.post_requests[0] = 0
                self.post_requests[1] = time.time()
                
            self.post_requests[0] += 1

            if self.post_requests[0] >= self.post_limit:
                print("Exceeded delete/post rate limit, sleeping to reset it")
                await asyncio.sleep(1.05 - (curr_time - self.post_requests[1]))
                self.post_requests[0] = 1
                self.post_requests[1] = time.time()
        
        url = self.host + path
        headers = self.request_headers("DELETE", path)
        async with self.session.delete(url, headers=headers, params=params) as response:
            await self.raise_if_bad_response(response)
            return await response.json()

    def request_headers(self, method: str, path: str) -> Dict[str, Any]:
        # Get the current time
        current_time = datetime.now()

        # Convert the time to a timestamp (seconds since the epoch)
        timestamp = current_time.timestamp()

        # Convert the timestamp to milliseconds
        current_time_milliseconds = int(timestamp * 1000)
        timestampt_str = str(current_time_milliseconds)

        # remove query params
        path_parts = path.split('?')

        msg_string = timestampt_str + method + '/trade-api/v2' + path_parts[0]
        signature = self.sign_pss_text(msg_string)

        headers = {"Content-Type": "application/json"}

        headers["KALSHI-ACCESS-KEY"] = self.key_id
        headers["KALSHI-ACCESS-SIGNATURE"] = signature
        headers["KALSHI-ACCESS-TIMESTAMP"] = timestampt_str
        # print(headers)
        return headers

    def sign_pss_text(self, text: str) -> str:
        # Before signing, we need to hash our message.
        # The hash is what we actually sign.
        # Convert the text to bytes
        message = text.encode('utf-8')
        try:
            signature = self.private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH
                ),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except InvalidSignature as e:
            raise ValueError("RSA sign PSS failed") from e

    async def raise_if_bad_response(self, response: aiohttp.ClientResponse) -> None:
        # print(response.json())
        if response.status not in range(200, 299):
            text = await response.text()
            raise HttpError(response.reason, response.status, text)
        
    def query_generation(self, params:dict) -> str:
        relevant_params = {k:v for k,v in params.items() if v != None}
        if len(relevant_params):
            query = '?'+''.join("&"+str(k)+"="+str(v) for k,v in relevant_params.items())[1:]
        else:
            query = ''
        return query


class HttpError(Exception):
    """Represents an HTTP error with reason and status code."""
    def __init__(self, reason: str, status: int, body: Optional[str] = None):
        super().__init__(reason)
        self.reason = reason
        self.status = status
        self.body = body

    def __str__(self) -> str:
        return f"HttpError({self.status} {self.reason}): {self.body}"


class ExchangeClient(KalshiClient):
    def __init__(self, 
                    exchange_api_base: str,
                    key_id: str, 
                    private_key: rsa.RSAPrivateKey,
                    session: aiohttp.ClientSession):
        super().__init__(
            exchange_api_base,
            key_id,
            private_key,
            session
        )
        self.key_id = key_id
        self.private_key = private_key
        self.exchange_url = "/exchange"
        self.markets_url = "/markets"
        self.events_url = "/events"
        self.series_url = "/series"
        self.portfolio_url = "/portfolio"

    async def logout(self):
        result = await self.post("/logout", body={})
        return result

    async def get_exchange_status(self):
        result = await self.get(self.exchange_url + "/status")
        return result

    # market endpoints!

    async def get_markets(self,
                            limit: Optional[int] = None,
                            cursor: Optional[str] = None,
                            event_ticker: Optional[str] = None,
                            series_ticker: Optional[str] = None,
                            max_close_ts: Optional[int] = None,
                            min_close_ts: Optional[int] = None,
                            status: Optional[str] = None,
                            tickers: Optional[str] = None,
                                ):
        query_string = self.query_generation(params={k: v for k,v in locals().items()})
        dictr = await self.get(self.markets_url + query_string)
        return dictr

    def get_market_url(self, 
                        ticker: str):
        return self.markets_url + '/' + ticker

    async def get_market(self, 
                        ticker: str):
        market_url = self.get_market_url(ticker=ticker)
        dictr = await self.get(market_url)
        return dictr

    async def get_event(self, 
                        event_ticker: str):
        dictr = await self.get(self.events_url + '/' + event_ticker)
        return dictr

    async def get_events(self, 
                        event_ticker: str):
        cursor = None
        dictr = {}
        for _ in range(3):
            response = await self.get(self.events_url + '/' + event_ticker, params={"limit": 200, "cursor": cursor})
            cursor = response.get("cursor")
            dictr.update(response)
        return dictr

    async def get_series(self, 
                        series_ticker: str):
        dictr = await self.get(self.series_url + '/' + series_ticker)
        return dictr

    async def get_market_history(self, 
                                ticker: str,
                                limit: Optional[int] = None,
                                cursor: Optional[str] = None,
                                max_ts: Optional[int] = None,
                                min_ts: Optional[int] = None,
                                ):
        relevant_params = {k: v for k,v in locals().items() if k!= 'ticker'}                            
        query_string = self.query_generation(params = relevant_params)
        market_url = self.get_market_url(ticker = ticker)
        dictr = await self.get(market_url + '/history' + query_string)
        return dictr

    async def get_orderbook(self, 
                            ticker: str,
                            depth: Optional[int] = None,
                            ):
        relevant_params = {k: v for k, v in locals().items() if k != 'ticker'}
        query_string = self.query_generation(params=relevant_params)
        market_url = self.get_market_url(ticker=ticker)
        dictr = await self.get(market_url + "/orderbook" + query_string)
        return dictr

    async def get_trades(self,
                        ticker: Optional[str] = None,
                        limit: Optional[int] = None,
                        cursor: Optional[str] = None,
                        max_ts: Optional[int] = None,
                        min_ts: Optional[int] = None,
                        ):
        query_string = self.query_generation(params={k: v for k,v in locals().items()})
        if ticker != None:
            if len(query_string):
                query_string += '&'
            else:
                query_string += '?'
            query_string += "ticker="+str(ticker)
            
        trades_url = self.markets_url + '/trades'
        dictr = await self.get(trades_url + query_string)
        return dictr

    # portfolio endpoints!

    async def get_balance(self):
        dictr = await self.get(self.portfolio_url + '/balance')
        return dictr

    async def create_order(self,
                            ticker: str,
                            client_order_id: str,
                            side: str,
                            action: str,
                            count: int,
                            type: str,
                            yes_price: Optional[int] = None,
                            no_price: Optional[int] = None,
                            expiration_ts: Optional[int] = None,
                            sell_position_floor: Optional[int] = None,
                            buy_max_cost: Optional[int] = None,
                            ):

        relevant_params = {k: v for k, v in locals().items() if k != 'self' and v is not None}

        # print(relevant_params)
        order_json = json.dumps(relevant_params)
        orders_url = self.portfolio_url + '/orders'
        result = await self.post(path=orders_url, body=order_json)
        return result

    async def batch_create_orders(self, 
                                    orders: list
            ):
        orders_json = json.dumps({'orders': orders})
        print(orders_json)
        batched_orders_url = self.portfolio_url + '/orders/batched'
        result = await self.post(path=batched_orders_url, body=orders_json)
        return result

    async def decrease_order(self, 
                            order_id: str,
                            reduce_by: int,
                            ):
        order_url = self.portfolio_url + '/orders/' + order_id
        decrease_json = json.dumps({'reduce_by': reduce_by})
        result = await self.post(path=order_url + '/decrease', body=decrease_json)
        return result

    async def cancel_order(self,
                            order_id: str):
        order_url = self.portfolio_url + '/orders/' + order_id
        result = await self.delete(path=order_url + '/cancel')
        return result

    async def batch_cancel_orders(self, 
                                    order_ids: list
            ):
        order_ids_json = json.dumps({"ids": order_ids})
        batched_orders_url = self.portfolio_url + '/orders/batched'
        result = await self.delete(path=batched_orders_url, params=order_ids_json)
        return result

    async def get_fills(self,
                            ticker: Optional[str] = None,
                            order_id: Optional[str] = None,
                            min_ts: Optional[int] = None,
                            max_ts: Optional[int] = None,
                            limit: Optional[int] = None,
                            cursor: Optional[str] = None):
        fills_url = self.portfolio_url + '/fills'
        query_string = self.query_generation(params={k: v for k,v in locals().items()})
        dictr = await self.get(fills_url + query_string)
        return dictr

    async def get_orders(self,
                            ticker: Optional[str] = None,
                            event_ticker: Optional[str] = None,
                            min_ts: Optional[int] = None,
                            max_ts: Optional[int] = None,
                            limit: Optional[int] = None,
                            cursor: Optional[str] = None
                            ):
        orders_url = self.portfolio_url + '/orders'
        query_string = self.query_generation(params={k: v for k,v in locals().items()})
        dictr = await self.get(orders_url + query_string)
        return dictr

    async def get_order(self,
                        order_id: str):
        orders_url = self.portfolio_url + '/orders'
        dictr = await self.get(orders_url + '/' + order_id)
        return dictr

    async def get_positions(self,
                            limit: Optional[int] = None,
                            cursor: Optional[str] = None,
                            settlement_status: Optional[str] = None,
                            ticker: Optional[str] = None,
                            event_ticker: Optional[str] = None,
                            ):
        positions_url = self.portfolio_url + '/positions'
        query_string = self.query_generation(params={k: v for k,v in locals().items()})
        dictr = await self.get(positions_url + query_string)
        return dictr

    async def get_portfolio_settlements(self,
                                        limit: Optional[int] = None,
                                        cursor: Optional[str] = None,):

        positions_url = self.portfolio_url + '/settlements'
        query_string = self.query_generation(params={k: v for k,v in locals().items()})
        dictr = await self.get(positions_url + query_string)
        return dictr
