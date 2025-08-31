import logging
import pytest
import requests

import hotmart_api


class DummyResponse:
    def __init__(self, status_code: int, data=None):
        self.status_code = status_code
        self._data = data or {}
        self.text = ""

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


def test_list_subscriptions_success(client, monkeypatch):
    called = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        called["url"] = url
        called["headers"] = headers
        called["params"] = params
        return DummyResponse(200, {"items": []})

    monkeypatch.setattr(hotmart_api, "get_hotmart_token", lambda: "tok")
    monkeypatch.setattr(hotmart_api.requests, "get", fake_get)

    with client.application.app_context():
        data = hotmart_api.list_subscriptions(offset=5, limit=10)

    assert called["headers"]["Authorization"] == "Bearer tok"
    assert called["params"] == {"offset": 5, "limit": 10}
    assert data == {"items": []}


@pytest.mark.parametrize("status", [401, 404, 500])
def test_list_subscriptions_logs_errors(client, monkeypatch, caplog, status):
    def fake_get(url, headers=None, params=None, timeout=None):
        return DummyResponse(status)

    monkeypatch.setattr(hotmart_api, "get_hotmart_token", lambda: "tok")
    monkeypatch.setattr(hotmart_api.requests, "get", fake_get)

    with client.application.app_context(), caplog.at_level(logging.ERROR), pytest.raises(requests.HTTPError):
        hotmart_api.list_subscriptions()

    assert any(record.levelno == logging.ERROR for record in caplog.records)
