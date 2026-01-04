"""Trade management router for the backend.

This module exposes a small APIRouter that can be mounted into the
main FastAPI app. It delegates persistence to the existing
`arbitragebot.storage.supabase` helpers when a Supabase client is
available via environment variables.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from arbitragebot.storage.supabase import (
	get_supabase_client,
	record_trade,
	fetch_trades,
)

from pydantic import BaseModel


router = APIRouter(prefix="/trades", tags=["trades"])


class CreateTradeRequest(BaseModel):
	event_id: str
	price: float
	stake: float
	status: str = "unknown"
	mode: str = "paper"


@router.post("/", response_model=dict)
async def create_trade(payload: CreateTradeRequest) -> dict:
	try:
		client = get_supabase_client()
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))

	timestamp = datetime.utcnow()
	trade_id = record_trade(
		client,
		event_id=payload.event_id,
		price=payload.price,
		stake=payload.stake,
		status=payload.status,
		mode=payload.mode,
		timestamp=timestamp,
	)
	return {"trade_id": trade_id}


@router.get("/", response_model=List[dict])
async def list_trades() -> List[dict]:
	try:
		client = get_supabase_client()
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))

	rows = fetch_trades(client)
	return rows


__all__ = ["router", "CreateTradeRequest"]
