"""Helpers for interacting with the Hotmart API."""

from __future__ import annotations

import base64
import time
from typing import Any, Dict

import requests
from flask import current_app

# Simple in-memory cache for the access token
_token_cache: Dict[str, Any] | None = None


def _token_expired() -> bool:
    """Return True if the cached token is missing or expired."""
    global _token_cache
    if not _token_cache:
        return True
    return _token_cache.get("expires_at", 0) <= time.time()


def get_hotmart_token() -> str:
    """Retrieve a Hotmart access token using the client credentials flow.

    The token is cached in memory until shortly before its expiration.
    If a valid token is present, it is returned without making a new
    request. When expired, a new token is automatically requested.
    """

    global _token_cache

    if not _token_expired():
        return _token_cache["access_token"]

    client_id = current_app.config.get("HOTMART_CLIENT_ID", "")
    client_secret = current_app.config.get("HOTMART_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError("Hotmart credentials not configured")

    auth_bytes = f"{client_id}:{client_secret}".encode()
    auth_header = base64.b64encode(auth_bytes).decode()

    use_sandbox = current_app.config.get("HOTMART_USE_SANDBOX", False)
    base_url = "https://sandbox.hotmart.com" if use_sandbox else "https://api.hotmart.com"
    url = f"{base_url}/oauth/token"

    headers = {"Authorization": f"Basic {auth_header}"}
    data = {"grant_type": "client_credentials"}

    resp = requests.post(url, headers=headers, data=data, timeout=10)
    resp.raise_for_status()
    payload = resp.json()

    access_token = payload.get("access_token")
    expires_in = int(payload.get("expires_in", 0))

    _token_cache = {
        "access_token": access_token,
        # Renew one minute before actual expiration
        "expires_at": time.time() + max(expires_in - 60, 0),
    }

    return access_token


__all__ = ["get_hotmart_token"]

