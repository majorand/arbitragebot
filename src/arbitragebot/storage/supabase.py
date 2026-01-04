from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from supabase import Client, create_client

from arbitragebot.schemas import NormalizedOdds


def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(url, key)


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
    if not odds:
        return
    rows = [_odds_row(item) for item in odds]
    client.table("odds").upsert(rows, on_conflict="odds_id").execute()


def record_trade(
    client: Client,
    event_id: str,
    price: float,
    stake: float,
    status: str,
    mode: str,
    timestamp: datetime,
) -> str:
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


def adjust_position(client: Client, event_id: str, delta: float) -> None:
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


def fetch_trades(client: Client) -> List[Dict[str, object]]:
    response = (
        client.table("trades").select("*").order("timestamp", desc=True).execute()
    )
    return list(response.data or [])


def fetch_positions(client: Client) -> Dict[str, float]:
    response = client.table("positions").select("*").execute()
    return {row["event_id"]: row.get("size", 0.0) for row in response.data or []}


def count_trades(client: Client) -> int:
    response = client.table("trades").select("trade_id", count="exact").execute()
    return response.count or 0