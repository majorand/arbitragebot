from __future__ import annotations

import logging
import os
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from supabase import Client, create_client

from arbitragebot.schemas import NormalizedOdds

LOGGER = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        LOGGER.warning("Supabase credentials not configured; running in mock mode")
        return None  # type: ignore
    try:
        return create_client(url, key)
    except Exception as exc:
        LOGGER.warning("Supabase client creation failed: %s", exc)
        return None  # type: ignore


def _odds_row(item: NormalizedOdds) -> Dict[str, object]:
    odds_id = f"{item.event_id}:{item.source}:{item.market_type}:{item.selection}"
    payload = asdict(item)
    payload.update(
        {
            "odds_id": odds_id,
            "start_time": item.start_time.isoformat(),
            "last_updated": item.last_updated.isoformat(),
        }
    )
    return payload


def store_odds(client: Client, odds: List[NormalizedOdds]) -> None:
    if not client or not odds:
        return
    # Deduplicate on odds_id within the batch to avoid ON CONFLICT multi-hit errors
    dedup: Dict[str, Dict[str, object]] = {}
    for item in odds:
        row = _odds_row(item)
        dedup[row["odds_id"]] = row
    rows = list(dedup.values())
    ids = [row["odds_id"] for row in rows]
    if len(ids) != len(set(ids)):
        dupes = {oid for oid in ids if ids.count(oid) > 1}
        LOGGER.warning("Duplicate odds_id after dedup step: %s", list(dupes))
    try:
        resp = client.table("odds").upsert(rows, on_conflict="odds_id").execute()
        # Log non-successful responses to diagnose insert failures in Supabase
        status = getattr(resp, "status_code", None)
        if status and status >= 400:
            LOGGER.warning("Supabase upsert odds returned status %s: %s", status, getattr(resp, "data", None))
    except Exception as exc:
        message = str(exc)
        # If the odds table is missing event_name (older schema), retry without that column
        if "event_name" in message:
            LOGGER.warning("Supabase odds table missing event_name; retrying upsert without it")
            trimmed_rows: List[Dict[str, object]] = []
            for row in rows:
                row_copy = dict(row)
                row_copy.pop("event_name", None)
                trimmed_rows.append(row_copy)
            try:
                client.table("odds").upsert(trimmed_rows, on_conflict="odds_id").execute()
            except Exception as exc_inner:
                LOGGER.warning("Failed to upsert odds after trimming event_name: %s", exc_inner)
        else:
            LOGGER.warning("Failed to upsert odds to Supabase: %s", exc)


def record_trade(
    client: Client,
    event_id: str,
    price: float,
    stake: float,
    status: str,
    mode: str,
    timestamp: datetime,
) -> str:
    if not client:
        return str(uuid4())
    trade_id = str(uuid4())
    client.table("trades").insert(
        {
            "trade_id": trade_id,
            "event_id": event_id,
            "price": price,
            "stake": stake,
            "status": status,
            "mode": mode,
            "timestamp": timestamp.isoformat(),
        }
    ).execute()
    return trade_id


def fetch_trades(client: Client) -> List[Dict[str, object]]:
    """Fetch all trades ordered by timestamp (newest first)."""
    if not client:
        return []
    try:
        response = (
            client.table("trades").select("*").order("timestamp", desc=True).execute()
        )
        return list(response.data or [])
    except Exception as e:
        LOGGER.debug("Could not fetch trades: %s", e)
        return []


def adjust_position(client: Client, event_id: str, delta: float) -> None:
    """Adjust position size by delta. Gracefully handles missing table."""
    if not client:
        return
    try:
        response = (
            client.table("positions").select("size").eq("event_id", event_id).execute()
        )
        current_size = 0.0
        if response.data:
            current_size = response.data[0].get("size", 0.0) or 0.0
        new_size = current_size + delta
        client.table("positions").upsert(
            {"event_id": event_id, "size": new_size}, on_conflict="event_id"
        ).execute()
    except Exception as e:
        LOGGER.debug("Could not adjust position (table may not exist): %s", e)
        # This is non-critical; positions table may not exist in development


def fetch_positions(client: Client) -> Dict[str, float]:
    """Fetch all positions. Returns empty dict if table doesn't exist."""
    if not client:
        return {}
    try:
        response = client.table("positions").select("*").execute()
        return {row["event_id"]: row.get("size", 0.0) for row in response.data or []}
    except Exception as e:
        LOGGER.debug("Could not fetch positions (table may not exist): %s", e)
        return {}


def count_trades(client: Client) -> int:
    if not client:
        return 0
    response = client.table("trades").select("trade_id", count="exact").execute()
    return response.count or 0