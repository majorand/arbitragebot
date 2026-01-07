import os
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from arbitragebot.schemas import NormalizedOdds
from arbitragebot.storage import supabase as supabase_module
from arbitragebot.storage.supabase import get_supabase_client, store_odds


def _build_sample_odds() -> NormalizedOdds:
    now = datetime.utcnow()
    return NormalizedOdds(
        sport="test",
        league="test",
        event_id="TEST-123",
        event_name="Test Match",
        start_time=now,
        home_team="Home",
        away_team="Away",
        market_type="moneyline",
        selection="yes",
        price=0.5,
        implied_probability=0.5,
        source="fanatics",
        last_updated=now,
    )


def test_get_supabase_client_missing_credentials(caplog, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    with caplog.at_level("WARNING"):
        client = get_supabase_client()

    assert client is None
    assert "Supabase credentials not configured" in caplog.text


def test_get_supabase_client_creation_failure(monkeypatch, caplog):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "secret")
    monkeypatch.setattr(
        "arbitragebot.storage.supabase.create_client",
        lambda url, key: (_ for _ in ()).throw(Exception("network error")),
    )

    with caplog.at_level("WARNING"):
        client = get_supabase_client()

    assert client is None
    assert "Supabase client creation failed" in caplog.text


def test_get_supabase_client_success(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "secret")

    sentinel = object()
    monkeypatch.setattr("arbitragebot.storage.supabase.create_client", lambda url, key: sentinel)

    assert get_supabase_client() is sentinel


def test_store_odds_handles_missing_client():
    sample = _build_sample_odds()
    # Should not raise even when client is None
    store_odds(None, [sample])


def test_store_odds_logs_on_upsert_failure(monkeypatch, caplog):
    sample = _build_sample_odds()

    class DummyTable:
        def upsert(self, rows, on_conflict):
            raise Exception("insert failed")

    class DummyClient:
        def table(self, _name):
            return DummyTable()

    client = DummyClient()
    with caplog.at_level("WARNING"):
        store_odds(client, [sample])

    assert "Failed to upsert odds to Supabase" in caplog.text
