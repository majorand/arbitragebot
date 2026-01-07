import pytest
from requests.exceptions import ConnectTimeout, HTTPError

from arbitragebot.data_sources.fanatics import FanaticsDataSource


class DummyResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise HTTPError(f"status {self.status_code}")

    def json(self):
        return self._json


class DummySession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    def get(self, *args, **kwargs):
        self.requests.append((args, kwargs))
        if self.error:
            raise self.error
        return self.response


def test_fetch_markets_success(monkeypatch):
    source = FanaticsDataSource()
    session = DummySession(response=DummyResponse({"events": [{"event_id": "123"}]}))
    source._session = session
    monkeypatch.setattr(FanaticsDataSource, "_normalize_markets", lambda self, markets: ["normalized"])

    result = source.fetch_markets()

    assert result == ["normalized"]
    assert source._cached == ["normalized"]
    assert session.requests


def test_fetch_markets_timeout_returns_cache():
    source = FanaticsDataSource()
    source._session = DummySession(error=ConnectTimeout("timeout"))
    source._cached = ["cached"]

    result = source.fetch_markets()

    assert result == ["cached"]


def test_fetch_markets_http_error(monkeypatch):
    source = FanaticsDataSource()
    response = DummyResponse({"events": []}, status_code=503)
    source._session = DummySession(response=response)
    # Avoid normalization being executed by raising on use
    monkeypatch.setattr(FanaticsDataSource, "_normalize_markets", lambda self, markets: [])

    result = source.fetch_markets()

    assert result == []
