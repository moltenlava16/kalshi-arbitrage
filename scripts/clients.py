import requests
import base64
import time
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
import json

from requests.exceptions import HTTPError

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

import websockets

class Environment(Enum):
    DEMO = "demo"
    PROD = "prod"

class KalshiBaseClient:
    """Base client class for interacting with the Kalshi API."""
    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ):
        """Initializes the client with the provided API key and private key.

        Args:
            key_id (str): Your Kalshi API key ID.
            private_key (rsa.RSAPrivateKey): Your RSA private key.
            environment (Environment): The API environment to use (DEMO or PROD).
        """
        self.key_id = key_id
        self.private_key = private_key
        self.environment = environment
        self.last_api_call = datetime.now()

        if self.environment == Environment.DEMO:
            self.HTTP_BASE_URL = "https://demo-api.kalshi.co"
            self.WS_BASE_URL = "wss://demo-api.kalshi.co"
        elif self.environment == Environment.PROD:
            self.HTTP_BASE_URL = "https://api.elections.kalshi.com"
            self.WS_BASE_URL = "wss://api.elections.kalshi.com"
        else:
            raise ValueError("Invalid environment")

    def request_headers(self, method: str, path: str) -> Dict[str, Any]:
        """Generates the required authentication headers for API requests."""
        current_time_milliseconds = int(time.time() * 1000)
        timestamp_str = str(current_time_milliseconds)

        # Remove query params from path
        path_parts = path.split('?')

        msg_string = timestamp_str + method + path_parts[0]
        signature = self.sign_pss_text(msg_string)

        headers = {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
        }
        return headers

    def sign_pss_text(self, text: str) -> str:
        """Signs the text using RSA-PSS and returns the base64 encoded signature."""
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

class KalshiHttpClient(KalshiBaseClient):
    """Client for handling HTTP connections to the Kalshi API."""
    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ):
        super().__init__(key_id, private_key, environment)
        self.host = self.HTTP_BASE_URL
        self.exchange_url = "/trade-api/v2/exchange"
        self.markets_url = "/trade-api/v2/markets"
        self.portfolio_url = "/trade-api/v2/portfolio"

    def rate_limit(self) -> None:
        """Built-in rate limiter to prevent exceeding API rate limits."""
        THRESHOLD_IN_MILLISECONDS = 100
        now = datetime.now()
        threshold_in_microseconds = 1000 * THRESHOLD_IN_MILLISECONDS
        threshold_in_seconds = THRESHOLD_IN_MILLISECONDS / 1000
        if now - self.last_api_call < timedelta(microseconds=threshold_in_microseconds):
            time.sleep(threshold_in_seconds)
        self.last_api_call = datetime.now()

    def raise_if_bad_response(self, response: requests.Response) -> None:
        """Raises an HTTPError if the response status code indicates an error."""
        if response.status_code not in range(200, 299):
            response.raise_for_status()

    def post(self, path: str, body: dict) -> Any:
        """Performs an authenticated POST request to the Kalshi API."""
        self.rate_limit()
        response = requests.post(
            self.host + path,
            json=body,
            headers=self.request_headers("POST", path)
        )
        self.raise_if_bad_response(response)
        return response.json()

    def get(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """Performs an authenticated GET request to the Kalshi API."""
        self.rate_limit()
        response = requests.get(
            self.host + path,
            headers=self.request_headers("GET", path),
            params=params
        )
        self.raise_if_bad_response(response)
        return response.json()

    def delete(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """Performs an authenticated DELETE request to the Kalshi API."""
        self.rate_limit()
        response = requests.delete(
            self.host + path,
            headers=self.request_headers("DELETE", path),
            params=params
        )
        self.raise_if_bad_response(response)
        return response.json()

    def get_balance(self) -> Dict[str, Any]:
        """Retrieves the account balance."""
        return self.get(self.portfolio_url + '/balance')

    def get_exchange_status(self) -> Dict[str, Any]:
        """Retrieves the exchange status."""
        return self.get(self.exchange_url + "/status")

    def get_trades(
        self,
        ticker: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        max_ts: Optional[int] = None,
        min_ts: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieves trades based on provided filters."""
        params = {
            'ticker': ticker,
            'limit': limit,
            'cursor': cursor,
            'max_ts': max_ts,
            'min_ts': min_ts,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.markets_url + '/trades', params=params)
    
    def get_events(
        self,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
        with_nested_markets: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Retrieves events based on provided filters.
        
        Args:
            limit: Number of results per page (1-200, defaults to 100)
            cursor: Pagination cursor for next page
            status: Filter by status (unopened, open, closed, settled)
            series_ticker: Series ticker to retrieve contracts for
            with_nested_markets: Include nested markets in response
        """
        params = {
            'limit': limit,
            'cursor': cursor,
            'status': status,
            'series_ticker': series_ticker,
            'with_nested_markets': with_nested_markets,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get('/trade-api/v2/events', params=params)
    
    def get_event(
        self,
        event_ticker: str,
        with_nested_markets: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Retrieves data about a specific event by its ticker.
        
        Args:
            event_ticker: The ticker of the event (required)
            with_nested_markets: Include nested markets in response
        """
        params = {}
        if with_nested_markets is not None:
            params['with_nested_markets'] = with_nested_markets
        
        return self.get(f'/trade-api/v2/events/{event_ticker}', params=params)
    
    def get_markets(
        self,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        event_ticker: Optional[str] = None,
        series_ticker: Optional[str] = None,
        max_close_ts: Optional[int] = None,
        min_close_ts: Optional[int] = None,
        status: Optional[str] = None,
        tickers: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves markets based on provided filters.
        
        Args:
            limit: Number of results per page (1-1000, defaults to 100)
            cursor: Pagination cursor for next page
            event_ticker: Event ticker to retrieve markets for
            series_ticker: Series ticker to retrieve contracts for
            max_close_ts: Markets closing in or before this timestamp
            min_close_ts: Markets closing in or after this timestamp
            status: Filter by status (unopened, open, closed, settled)
            tickers: Comma separated list of specific tickers
        """
        params = {
            'limit': limit,
            'cursor': cursor,
            'event_ticker': event_ticker,
            'series_ticker': series_ticker,
            'max_close_ts': max_close_ts,
            'min_close_ts': min_close_ts,
            'status': status,
            'tickers': tickers,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.markets_url, params=params)
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Retrieves a single order by its ID.
        
        Args:
            order_id: The UUID of the order (required)
        """
        return self.get(f'{self.portfolio_url}/orders/{order_id}')
    
    def get_fills(
        self,
        ticker: Optional[str] = None,
        order_id: Optional[str] = None,
        min_ts: Optional[int] = None,
        max_ts: Optional[int] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves all fills (executed trades) for the member.
        
        Args:
            ticker: Restricts response to trades in a specific market
            order_id: Restricts response to trades related to a specific order
            min_ts: Restricts response to trades after this timestamp
            max_ts: Restricts response to trades before this timestamp
            limit: Number of results per page (1-1000, defaults to 100)
            cursor: Pagination cursor for next page of results
        
        Returns:
            Dict containing fills data with pagination info
        """
        params = {
            'ticker': ticker,
            'order_id': order_id,
            'min_ts': min_ts,
            'max_ts': max_ts,
            'limit': limit,
            'cursor': cursor,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.portfolio_url + '/fills', params=params)
    
    def get_orders(
        self,
        ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        min_ts: Optional[int] = None,
        max_ts: Optional[int] = None,
        status: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieves all orders for the member.
        
        Args:
            ticker: Restricts response to orders in a single market
            event_ticker: Restricts response to orders in a single event
            min_ts: Restricts response to orders after this timestamp (Unix timestamp)
            max_ts: Restricts response to orders before this timestamp (Unix timestamp)
            status: Restricts response to orders with certain status (resting, canceled, or executed)
            cursor: Pagination cursor for next page of results
            limit: Number of results per page (1-1000, defaults to 100)
        
        Returns:
            Dict containing orders data with pagination info
        """
        params = {
            'ticker': ticker,
            'event_ticker': event_ticker,
            'min_ts': min_ts,
            'max_ts': max_ts,
            'status': status,
            'cursor': cursor,
            'limit': limit,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.portfolio_url + '/orders', params=params)
    
    def create_order(
        self,
        action: str,
        count: int,
        side: str,
        ticker: str,
        type: str,
        client_order_id: str,
        buy_max_cost: Optional[int] = None,
        expiration_ts: Optional[int] = None,
        no_price: Optional[int] = None,
        post_only: Optional[bool] = None,
        sell_position_floor: Optional[int] = None,
        time_in_force: Optional[str] = None,
        yes_price: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Creates a new order in a market.
        
        Args:
            action: "buy" or "sell" - specifies if this is a buy or sell order (required)
            count: Number of contracts to be bought or sold (required)
            side: "yes" or "no" - specifies if this is a 'yes' or 'no' order (required)
            ticker: The ticker of the market the order will be placed in (required)
            type: "market" or "limit" - specifies order type (required)
            client_order_id: Client-specified order ID for tracking (required)
            buy_max_cost: Maximum cents that can be spent to acquire a position (for buy orders)
            expiration_ts: Expiration time of the order in unix seconds
            no_price: Submitting price of the No side of the trade, in cents
            post_only: If true, order will be rejected if it crosses the spread and executes
            sell_position_floor: Will not let you flip position for a market order if set to 0
            time_in_force: Currently only "fill_or_kill" is supported
            yes_price: Submitting price of the Yes side of the trade, in cents
        
        Note:
            - For limit orders: Either yes_price or no_price must be provided (not both)
            - If buy_max_cost is provided for market orders, it represents the maximum cents
            that can be spent to acquire a position
            - If expiration_ts is not provided, order won't expire until explicitly cancelled (GTC)
        
        Returns:
            Dict containing the created order details
        """
        body = {
            'action': action,
            'count': count,
            'side': side,
            'ticker': ticker,
            'type': type,
            'client_order_id': client_order_id,
        }
        
        # Add optional parameters if provided
        if buy_max_cost is not None:
            body['buy_max_cost'] = buy_max_cost
        if expiration_ts is not None:
            body['expiration_ts'] = expiration_ts
        if no_price is not None:
            body['no_price'] = no_price
        if post_only is not None:
            body['post_only'] = post_only
        if sell_position_floor is not None:
            body['sell_position_floor'] = sell_position_floor
        if time_in_force is not None:
            body['time_in_force'] = time_in_force
        if yes_price is not None:
            body['yes_price'] = yes_price
        
        return self.post(self.portfolio_url + '/orders', body)
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancels an order by its ID.
        
        Args:
            order_id: The UUID of the order to cancel (required)
        
        Returns:
            Dict containing the cancelled order details
        """ 
        return self.delete(f'{self.portfolio_url}/orders/{order_id}')
    
    def amend_order(
        self,
        order_id: str,
        action: str,
        client_order_id: str,
        count: int,
        side: str,
        ticker: str,
        updated_client_order_id: str,
        no_price: Optional[int] = None,
        yes_price: Optional[int] = None,
        ) -> Dict[str, Any]:
        """Amends an existing order by changing the max number of fillable contracts and/or price.
        
        Args:
            order_id: ID of the order to be amended (required)
            action: "buy" or "sell" - specifies if this is a buy or sell order (required)
            client_order_id: Client-specified order ID for tracking (required)
            count: Number of contracts to be bought or sold (required)
            side: "yes" or "no" - specifies if this is a 'yes' or 'no' order (required)
            ticker: The ticker of the market the order will be placed in (required)
            updated_client_order_id: Updated client-specified order ID (required)
            no_price: Submitting price of the No side of the trade, in cents
            yes_price: Submitting price of the Yes side of the trade, in cents
        
        Note:
            - Exactly one of yes_price or no_price must be passed (not both)
            - Max fillable contracts is remaining_count + fill_count
        
        Returns:
            Dict containing the amended order details
        """
        body = {
            'action': action,
            'client_order_id': client_order_id,
            'count': count,
            'side': side,
            'ticker': ticker,
            'updated_client_order_id': updated_client_order_id,
        }
        
        # Add optional parameters if provided
        if no_price is not None:
            body['no_price'] = no_price
        if yes_price is not None:
            body['yes_price'] = yes_price
        
        return self.post(f'{self.portfolio_url}/orders/{order_id}/amend', body)
    
    def decrease_order(
        self,
        order_id: str,
        reduce_by: Optional[int] = None,
        reduce_to: Optional[int] = None,
        ) -> Dict[str, Any]:
        """Decreases the number of contracts in an existing order.
        
        Args:
            order_id: ID of the order to be decreased (required)
            reduce_by: Number of contracts to decrease the order's count by
            reduce_to: Number of contracts to decrease the order to
        
        Note:
            - One of reduce_by or reduce_to must be provided (not both)
            - If the order's remaining count is lower, it does nothing
            - Cancelling an order is equivalent to decreasing an order amount to zero
        
        Returns:
            Dict containing the decreased order details
        """
        body = {}
        
        if reduce_by is not None:
            body['reduce_by'] = reduce_by
        if reduce_to is not None:
            body['reduce_to'] = reduce_to
        
        return self.post(f'{self.portfolio_url}/orders/{order_id}/decrease', body)
    

    
    def get_positions(
        self,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        count_filter: Optional[str] = None,
        settlement_status: Optional[str] = None,
        ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        ) -> Dict[str, Any]:
        """Retrieves all market positions for the member.
        
        Args:
            cursor: Pagination cursor for next page of results
            limit: Number of results per page (1-1000, defaults to 100)
            count_filter: Restricts positions to those with any of following fields with non-zero values, 
                            as a comma separated list. Accepted values: position, total_traded, resting_order_count
            settlement_status: Settlement status of the markets to return (all, settled, unsettled)
            ticker: Ticker of desired positions
            event_ticker: Event ticker of desired positions
        
        Returns:
            Dict containing positions data with pagination info
        """
        params = {
            'cursor': cursor,
            'limit': limit,
            'count_filter': count_filter,
            'settlement_status': settlement_status,
            'ticker': ticker,
            'event_ticker': event_ticker,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.portfolio_url + '/positions', params=params)
    


class KalshiWebSocketClient(KalshiBaseClient):
    """Client for handling WebSocket connections to the Kalshi API."""
    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ):
        super().__init__(key_id, private_key, environment)
        self.ws = None
        self.url_suffix = "/trade-api/ws/v2"
        self.message_id = 1  # Add counter for message IDs

    async def connect(self):
        """Establishes a WebSocket connection using authentication."""
        host = self.WS_BASE_URL + self.url_suffix
        auth_headers = self.request_headers("GET", self.url_suffix)
        async with websockets.connect(host, additional_headers=auth_headers) as websocket:
            self.ws = websocket
            await self.on_open()
            await self.handler()

    async def on_open(self):
        """Callback when WebSocket connection is opened."""
        print("WebSocket connection opened.")
        await self.subscribe_to_tickers()

    async def subscribe_to_tickers(self):
        """Subscribe to ticker updates for all markets."""
        subscription_message = {
            "id": self.message_id,
            "cmd": "subscribe",
            "params": {
                "channels": ["ticker"]
            }
        }
        await self.ws.send(json.dumps(subscription_message))
        self.message_id += 1

    async def handler(self):
        """Handle incoming messages."""
        try:
            async for message in self.ws:
                await self.on_message(message)
        except websockets.ConnectionClosed as e:
            await self.on_close(e.code, e.reason)
        except Exception as e:
            await self.on_error(e)

    async def on_message(self, message):
        """Callback for handling incoming messages."""
        print("Received message:", message)

    async def on_error(self, error):
        """Callback for handling errors."""
        print("WebSocket error:", error)

    async def on_close(self, close_status_code, close_msg):
        """Callback when WebSocket connection is closed."""
        print("WebSocket connection closed with code:", close_status_code, "and message:", close_msg)