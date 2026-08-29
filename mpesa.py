import base64
import requests
from datetime import datetime
from flask import current_app

SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE = "https://api.safaricom.co.ke"


def _base_url():
    return PRODUCTION_BASE if current_app.config.get("MPESA_ENV") == "production" else SANDBOX_BASE


def get_access_token():
    url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    key = current_app.config["MPESA_CONSUMER_KEY"]
    secret = current_app.config["MPESA_CONSUMER_SECRET"]

    response = requests.get(url, auth=(key, secret), timeout=15)
    response.raise_for_status()
    return response.json()["access_token"]


def _password_and_timestamp():
    shortcode = current_app.config["MPESA_SHORTCODE"]
    passkey = current_app.config["MPESA_PASSKEY"]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{shortcode}{passkey}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


def stk_push(phone_number, amount, account_reference, description="KSM Donation"):
    token = get_access_token()
    password, timestamp = _password_and_timestamp()
    shortcode = current_app.config["MPESA_SHORTCODE"]

    url = f"{_base_url()}/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": current_app.config["MPESA_CALLBACK_URL"],
        "AccountReference": account_reference[:12],
        "TransactionDesc": description[:13],
    }

    response = requests.post(url, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


def normalize_phone(raw_phone):
    phone = raw_phone.strip().replace(" ", "").replace("+", "")
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("7") or phone.startswith("1"):
        phone = "254" + phone
    return phone