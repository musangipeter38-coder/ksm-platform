import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

key = os.environ.get("MPESA_CONSUMER_KEY")
secret = os.environ.get("MPESA_CONSUMER_SECRET")

credentials = f"{key}:{secret}"
encoded = base64.b64encode(credentials.encode()).decode()

url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
headers = {
    "Authorization": f"Basic {encoded}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

response = requests.get(url, headers=headers, timeout=15)

print("\nStatus code:", response.status_code)
print("Response body:", repr(response.text))