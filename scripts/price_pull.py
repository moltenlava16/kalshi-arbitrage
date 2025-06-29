import requests
import json
import time
from datetime import datetime
import hmac
import hashlib
import base64

class KalshiClient:
    def __init__(self, api_key_id, private_key_file):
        self.api_key_id = api_key_id
        self.base_url = "https://demo-api.kalshi.co/trade-api/v2"
        
        # Read private key from file
        with open(private_key_file, 'r') as f:
            self.private_key = f.read().strip()
        
        self.session = requests.Session()
        self.token = None
        
    def _sign_request(self, method, path, body=""):
        """Create signature for API request"""
        timestamp = str(int(time.time()))
        
        # Create the string to sign
        string_to_sign = f"{timestamp}{method}{path}{body}"
        
        # Create signature
        signature = hmac.new(
            self.private_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return timestamp, signature
    
    def authenticate(self):
        """Authenticate with Kalshi API"""
        path = "/login"
        method = "POST"
        body = json.dumps({"email": "", "password": ""})  # For API key auth, these can be empty
        
        timestamp, signature = self._sign_request(method, path, body)
        
        headers = {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}{path}",
                headers=headers,
                data=body
            )
            response.raise_for_status()
            
            data = response.json()
            self.token = data.get('token')
            print("Successfully authenticated with Kalshi API")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Authentication failed: {e}")
            return False
    
    def _make_authenticated_request(self, method, path, params=None, body=None):
        """Make authenticated request to Kalshi API"""
        if not self.token:
            if not self.authenticate():
                return None
        
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, params=params)
            elif method == "POST":
                response = self.session.post(url, headers=headers, json=body)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
    
    def get_markets(self, limit=100, cursor=None):
        """Get list of available markets"""
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
            
        return self._make_authenticated_request("GET", "/markets", params=params)
    
    def get_market_orderbook(self, ticker):
        """Get orderbook for a specific market"""
        path = f"/markets/{ticker}/orderbook"
        return self._make_authenticated_request("GET", path)
    
    def get_market_history(self, ticker, limit=100):
        """Get trade history for a specific market"""
        path = f"/markets/{ticker}/history"
        params = {"limit": limit}
        return self._make_authenticated_request("GET", path, params=params)
    
    def get_live_prices(self, tickers=None, limit=20):
        """Get live prices for markets"""
        markets_data = self.get_markets(limit=limit)
        
        if not markets_data or 'markets' not in markets_data:
            print("Failed to fetch markets data")
            return None
        
        live_prices = []
        
        for market in markets_data['markets']:
            ticker = market['ticker']
            
            # If specific tickers requested, filter
            if tickers and ticker not in tickers:
                continue
            
            # Get orderbook for current prices
            orderbook = self.get_market_orderbook(ticker)
            
            if orderbook:
                price_info = {
                    'ticker': ticker,
                    'title': market.get('title', 'Unknown'),
                    'yes_price': None,
                    'no_price': None,
                    'last_price': None,
                    'volume': market.get('volume', 0),
                    'open_interest': market.get('open_interest', 0),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Extract prices from orderbook
                if 'yes' in orderbook and orderbook['yes']:
                    if orderbook['yes'].get('bids'):
                        price_info['yes_price'] = orderbook['yes']['bids'][0]['price']
                    elif orderbook['yes'].get('asks'):
                        price_info['yes_price'] = orderbook['yes']['asks'][0]['price']
                
                if 'no' in orderbook and orderbook['no']:
                    if orderbook['no'].get('bids'):
                        price_info['no_price'] = orderbook['no']['bids'][0]['price']
                    elif orderbook['no'].get('asks'):
                        price_info['no_price'] = orderbook['no']['asks'][0]['price']
                
                live_prices.append(price_info)
        
        return live_prices
    
    def monitor_prices(self, tickers=None, interval=30):
        """Continuously monitor prices"""
        print(f"Starting price monitoring (interval: {interval}s)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                print(f"\n--- Price Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
                
                prices = self.get_live_prices(tickers=tickers)
                
                if prices:
                    for price in prices:
                        yes_price = price['yes_price'] if price['yes_price'] else 'N/A'
                        no_price = price['no_price'] if price['no_price'] else 'N/A'
                        
                        print(f"{price['ticker']}: YES={yes_price}¢, NO={no_price}¢ | Vol: {price['volume']}")
                        print(f"  {price['title'][:80]}...")
                else:
                    print("No price data available")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nPrice monitoring stopped")

def main():
    # Initialize client
    api_key_id = "61e9a095-e66a-494d-9fbd-bccd71e6dafe"
    private_key_file = "scripts/Pierce.txt"
    
    client = KalshiClient(api_key_id, private_key_file)
    
    # Example usage
    print("Kalshi Live Price Monitor")
    print("=" * 40)
    
    # Get single price snapshot
    print("\nFetching current prices...")
    prices = client.get_live_prices(limit=10)
    
    if prices:
        print(f"\nFound {len(prices)} active markets:")
        for price in prices:
            yes_price = price['yes_price'] if price['yes_price'] else 'N/A'
            no_price = price['no_price'] if price['no_price'] else 'N/A'
            
            print(f"\n{price['ticker']}")
            print(f"  Title: {price['title']}")
            print(f"  YES Price: {yes_price}¢")
            print(f"  NO Price: {no_price}¢")
            print(f"  Volume: {price['volume']}")
            print(f"  Open Interest: {price['open_interest']}")
    
    # Uncomment to start continuous monitoring
    # client.monitor_prices(interval=30)

if __name__ == "__main__":
    main()