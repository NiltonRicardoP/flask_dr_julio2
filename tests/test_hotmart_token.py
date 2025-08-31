import time

import hotmart


class DummyResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


def test_token_is_cached(client, monkeypatch):
    hotmart._token_cache = None
    app = client.application
    calls = []

    def fake_post(url, headers=None, data=None, timeout=None):
        calls.append(url)
        return DummyResponse({"access_token": "tok1", "expires_in": 3600})

    monkeypatch.setattr(hotmart.requests, "post", fake_post)

    with app.app_context():
        app.config["HOTMART_CLIENT_ID"] = "id"
        app.config["HOTMART_CLIENT_SECRET"] = "secret"
        tok_a = hotmart.get_hotmart_token()
        tok_b = hotmart.get_hotmart_token()

    assert tok_a == "tok1"
    assert tok_b == "tok1"
    assert len(calls) == 1


def test_token_refreshes_when_expired(client, monkeypatch):
    hotmart._token_cache = None
    app = client.application
    first_calls = []

    def first_post(url, headers=None, data=None, timeout=None):
        first_calls.append(url)
        return DummyResponse({"access_token": "tok1", "expires_in": 1})

    monkeypatch.setattr(hotmart.requests, "post", first_post)

    with app.app_context():
        app.config["HOTMART_CLIENT_ID"] = "id"
        app.config["HOTMART_CLIENT_SECRET"] = "secret"
        tok1 = hotmart.get_hotmart_token()

    # Expire the token
    hotmart._token_cache["expires_at"] = time.time() - 1

    second_calls = []

    def second_post(url, headers=None, data=None, timeout=None):
        second_calls.append(url)
        return DummyResponse({"access_token": "tok2", "expires_in": 3600})

    monkeypatch.setattr(hotmart.requests, "post", second_post)

    with app.app_context():
        tok2 = hotmart.get_hotmart_token()

    assert tok1 == "tok1"
    assert tok2 == "tok2"
    assert len(first_calls) == 1
    assert len(second_calls) == 1
