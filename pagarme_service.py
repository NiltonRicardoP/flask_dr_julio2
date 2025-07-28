import os
import requests

API_KEY = os.getenv("PAGARME_API_KEY", "")
BASE_URL = os.getenv("PAGARME_BASE_URL", "https://api.pagar.me/1")


def create_transaction(amount, card_hash=None, **kwargs):
    """Create a transaction on Pagar.me returning response JSON."""
    url = f"{BASE_URL}/transactions"
    data = {"api_key": API_KEY, "amount": int(amount * 100)}
    if card_hash:
        data["card_hash"] = card_hash
    data.update(kwargs)
    resp = requests.post(url, data=data)
    resp.raise_for_status()
    return resp.json()
