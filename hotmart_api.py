"""High level functions for Hotmart API interactions."""

from __future__ import annotations

from typing import Any, Dict

import requests
from flask import current_app

from hotmart import get_hotmart_token


def _base_url() -> str:
    """Return the base URL for the Hotmart API."""
    use_sandbox = current_app.config.get("HOTMART_USE_SANDBOX", False)
    return "https://sandbox.hotmart.com" if use_sandbox else "https://api.hotmart.com"


def list_subscriptions(offset: int = 0, limit: int = 20) -> Dict[str, Any]:
    """List subscriptions from the Hotmart API.

    Parameters
    ----------
    offset: int
        The result offset for pagination.
    limit: int
        The maximum number of items to return.

    Returns
    -------
    Dict[str, Any]
        The JSON response from the Hotmart API.
    """
    token = get_hotmart_token()
    url = f"{_base_url()}/payments/v1/subscriptions"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"offset": offset, "limit": limit}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
    except requests.RequestException:
        current_app.logger.exception("Failed to request Hotmart subscriptions")
        raise

    if resp.status_code == 401:
        current_app.logger.error("Hotmart API unauthorized when listing subscriptions")
    elif resp.status_code == 404:
        current_app.logger.error("Hotmart subscriptions endpoint not found")
    elif resp.status_code == 500:
        current_app.logger.error("Hotmart API internal server error listing subscriptions")

    resp.raise_for_status()
    return resp.json()


__all__ = ["list_subscriptions"]
