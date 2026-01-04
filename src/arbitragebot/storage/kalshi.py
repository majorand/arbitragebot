from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List

from arbitragebot.schemas import NormalizedOdds, OrderRequest
from arbitragebot.storage.supabase import get_supabase_client


"""Kalshi storage helpers.

This module provides small helpers to persist normalized market data
and orders produced by strategies. It supports writing to a local JSON
file (useful for testing) and upserting rows into a Supabase `odds`
table using the project's existing Supabase helpers.
"""


def save_kalshi_markets_to_file(path: str | Path, markets: Iterable[NormalizedOdds]) -> None:
    """Serialize a list of NormalizedOdds to a JSON file.

    The output is a simple list of dictionaries containing the key
    fields used by the app. This is intended for debugging and local
    snapshots.
    """
    rows: List[Dict] = []
    for m in markets:
        rows.append(
            {
                "event_id": m.event_id,
                "source": m.source,
                "market_type": m.market_type,
                "selection": m.selection,
                "price": m.price,
                "implied_probability": m.implied_probability,
                "start_time": m.start_time.isoformat(),
                "last_updated": m.last_updated.isoformat(),
            }
        )
    Path(path).write_text(json.dumps(rows, indent=2), encoding="utf-8")


def upsert_kalshi_markets_to_supabase(markets: Iterable[NormalizedOdds]) -> None:
    """Upsert Kalshi markets to Supabase using the configured client.

    The function constructs an `odds_id` per row and mirrors the
    payload structure expected by the Supabase helper utilities.
    """
    client = get_supabase_client()
    rows = []
    for m in markets:
        odds_id = f"{m.event_id}:{m.source}:{m.market_type}:{m.selection}"
        payload = asdict(m)
        payload.update(
            {
                "odds_id": odds_id,
                "start_time": m.start_time.isoformat(),
                "last_updated": m.last_updated.isoformat(),
            }
        )
        rows.append(payload)

    if rows:
        client.table("odds").upsert(rows, on_conflict="odds_id").execute()


def serialize_order(order: OrderRequest) -> Dict[str, object]:
    """Serialize an OrderRequest for persistence or logging.

    Returns a JSON-serializable dict.
    """
    payload = asdict(order)
    payload["market_id"] = order.market_id
    return payload


__all__ = [
    "save_kalshi_markets_to_file",
    "upsert_kalshi_markets_to_supabase",
    "serialize_order",
]
