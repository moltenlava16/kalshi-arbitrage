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



trades = client.get_trades()
print(trades)


# # Choose one of the Bitcoin markets from your list
# ticker = "KXBTCD-25JUL0709-T108499.99"

# # Generate unique client order IDs
# yes_client_order_id = str(uuid.uuid4())
# no_client_order_id = str(uuid.uuid4())

# try:
#    # Place market sell order for Yes contracts
#    yes_order = client.create_order(
#        action="sell",
#        count=1,  # Number of contracts
#        side="yes",
#        ticker=ticker,
#        type="market",
#        client_order_id=yes_client_order_id,
#        yes_price=50  # 50 cents
#    )
#    print(f"Yes sell order placed: {yes_order.get('order', {}).get('order_id')}")
   
#    # Place market sell order for No contracts
#    no_order = client.create_order(
#        action="sell",
#        count=1,  # Number of contracts
#        side="no",
#        ticker=ticker,
#        type="market",
#        client_order_id=no_client_order_id,
#        no_price=50  # 50 cents
#    )
#    print(f"No sell order placed: {no_order.get('order', {}).get('order_id')}")
   
# except Exception as e:
#    print(f"Error placing orders: {str(e)}")