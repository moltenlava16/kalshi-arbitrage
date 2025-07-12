import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
import asyncio
import requests
import uuid


from clients import KalshiHttpClient, KalshiWebSocketClient, Environment

# Load environment variables
load_dotenv()
env = Environment.DEMO # toggle environment here
KEYID = os.getenv('DEMO_KEYID') if env == Environment.DEMO else os.getenv('PROD_KEYID')
KEYFILE = os.getenv('DEMO_KEYFILE') if env == Environment.DEMO else os.getenv('PROD_KEYFILE')

try:
    with open(KEYFILE, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None  # Provide the password if your key is encrypted
        )
except FileNotFoundError:
    raise FileNotFoundError(f"Private key file not found at {KEYFILE}")
except Exception as e:
    raise Exception(f"Error loading private key: {str(e)}")

# Initialize the HTTP client
client = KalshiHttpClient(
    key_id=KEYID,
    private_key=private_key,
    environment=env
)

# Get account balance
balance = client.get_balance()
print("Balance:", balance)

# Initialize the WebSocket client
ws_client = KalshiWebSocketClient(
    key_id=KEYID,
    private_key=private_key,
    environment=env
)


# Instead of hardcoding the ticker, find a valid one:
try:
    # Get open markets
    markets_response = client.get_markets(status="open", limit=1)
    markets = markets_response.get('markets', [])
    
    if markets:
        ticker = markets[0].get('ticker')
        print(f"Using ticker: {ticker}")
        
        # Then place your order with the valid ticker
        buy_order = client.create_order(
            action="buy",
            count=1,
            side="yes",
            ticker=ticker,
            type="market",
            client_order_id=str(uuid.uuid4()),
            buy_max_cost=50  # Add this to prevent overspending
        )
        print(f"Order placed: {buy_order}")
    else:
        print("No open markets found")
        
except Exception as e:
    print(f"Error: {str(e)}")