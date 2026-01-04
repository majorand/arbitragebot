from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from arbitragebot.config import TradingConfig, load_yaml
from arbitragebot.execution.paper import PaperTradingEngine
from arbitragebot.exchanges.kalshi import KalshiTradingClient
from arbitragebot.main import collect_market_data
from arbitragebot.schemas import NormalizedOdds, OrderRequest
from arbitragebot.storage.supabase import (
    adjust_position,
    count_trades,
    fetch_positions,
    fetch_trades,
    get_supabase_client,
    record_trade,
    store_odds,
)
from .trades import router as trades_router
from .socket_server import manager as ws_manager

app = FastAPI(title="ArbitrageBot API")
allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount additional routers
app.include_router(trades_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        while True:
            try:
                data = await websocket.receive_text()
            except Exception:
                break
            # simple echo/ack for now
            await ws_manager.send_personal_message(f"ack:{data}", websocket)
    finally:
        ws_manager.disconnect(websocket)


def _load_sources_config() -> dict:
    sources_path = Path(os.getenv("SOURCES_CONFIG", "config/example_sources.yaml"))
    return load_yaml(sources_path).get("sources", {})


class ModeRequest(BaseModel):
    mode: str = Field(..., pattern="^(paper|live)$")


class TradeRequest(BaseModel):
    event_id: str
    stake: float


class TradeRecord(BaseModel):
    trade_id: str
    event_id: str
    status: str
    mode: str
    price: float
    stake: float
    timestamp: datetime


class MetricsResponse(BaseModel):
    total_trades: int
    cash_balance: float
    open_positions: int


class TradingState:
    def __init__(self) -> None:
        self.mode = TradingConfig(mode=os.getenv("TRADING_MODE", "paper"), max_order_size=100)
        self.paper_engine = PaperTradingEngine()

    def set_mode(self, mode: str) -> None:
        self.mode = TradingConfig(mode=mode, max_order_size=self.mode.max_order_size)


STATE = TradingState()


def _pick_kalshi_odds(data: List[NormalizedOdds], event_id: str) -> NormalizedOdds:
    candidates = [item for item in data if item.event_id == event_id and item.source == "kalshi"]
    if not candidates:
        raise HTTPException(status_code=404, detail="Kalshi odds not found for event")
    return max(candidates, key=lambda item: item.implied_probability)


@app.get("/odds")
async def list_odds() -> List[dict]:
    sources_config = _load_sources_config()
    data = collect_market_data(sources_config)
    client = get_supabase_client()
    store_odds(client, data)
    return [asdict(item) for item in data]


@app.post("/mode")
async def set_mode(payload: ModeRequest) -> dict:
    STATE.set_mode(payload.mode)
    return {"mode": STATE.mode.mode}


@app.get("/mode")
async def get_mode() -> dict:
    return {"mode": STATE.mode.mode}


@app.post("/trade")
async def trigger_trade(payload: TradeRequest) -> TradeRecord:
    sources_config = _load_sources_config()
    data = collect_market_data(sources_config)
    market = _pick_kalshi_odds(data, payload.event_id)

    order = OrderRequest(
        market_id=market.event_id,
        side="buy",
        price=market.price,
        size=payload.stake,
        order_type="limit",
    )

    if STATE.mode.mode == "paper":
        result = STATE.paper_engine.submit_order(order, reference_price=order.price)
        client = get_supabase_client()
        timestamp = datetime.utcnow()
        trade_id = record_trade(
            client,
            event_id=order.market_id,
            price=order.price,
            stake=order.size,
            status=result.status,
            mode=STATE.mode.mode,
            timestamp=timestamp,
        )
        adjust_position(
            client,
            event_id=order.market_id,
            delta=order.size if order.side == "buy" else -order.size,
        )
        return TradeRecord(
            trade_id=trade_id,
            event_id=order.market_id,
            status=result.status,
            mode=STATE.mode.mode,
            price=order.price,
            stake=order.size,
            timestamp=timestamp,
        )

    client = KalshiTradingClient(
        base_url=os.getenv("KALSHI_API", "https://api.kalshi.com"),
        api_key=os.getenv("KALSHI_API_KEY"),
    )
    result = client.place_order(order)
    supabase_client = get_supabase_client()
    timestamp = datetime.utcnow()
    trade_id = record_trade(
        supabase_client,
        event_id=order.market_id,
        price=order.price,
        stake=order.size,
        status=result.status,
        mode=STATE.mode.mode,
        timestamp=timestamp,
    )
    adjust_position(
        supabase_client,
        event_id=order.market_id,
        delta=order.size if order.side == "buy" else -order.size,
    )
    return TradeRecord(
        trade_id=trade_id,
        event_id=order.market_id,
        status=result.status,
        mode=STATE.mode.mode,
        price=order.price,
        stake=order.size,
        timestamp=timestamp,
    )


@app.get("/trades")
async def trade_history() -> List[TradeRecord]:
    client = get_supabase_client()
    rows = fetch_trades(client)
    return [
        TradeRecord(
            trade_id=row["trade_id"],
            event_id=row["event_id"],
            status=row["status"],
            mode=row["mode"],
            price=row["price"],
            stake=row["stake"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )
        for row in rows
    ]


@app.get("/positions")
async def open_positions() -> Dict[str, float]:
    client = get_supabase_client()
    return fetch_positions(client)


@app.get("/metrics")
async def metrics() -> MetricsResponse:
    client = get_supabase_client()
    positions = fetch_positions(client)
    return MetricsResponse(
        total_trades=count_trades(client),
        cash_balance=STATE.paper_engine.cash_balance,
        open_positions=len([pos for pos in positions.values() if pos != 0]),
    )