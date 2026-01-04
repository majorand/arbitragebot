from __future__ import annotations

import asyncio
import os
from collections import deque
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from arbitragebot.config import TradingConfig, load_yaml
    from arbitragebot.execution.paper import PaperTradingEngine
    from arbitragebot.exchanges.kalshi import KalshiTradingClient
    from arbitragebot.main import collect_market_data
    from arbitragebot.schemas import NormalizedOdds, OrderRequest
    HAS_ARBITRAGEBOT = True
except ImportError:
    HAS_ARBITRAGEBOT = False
    class NormalizedOdds:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class TradingConfig:
        def __init__(self, mode: str = "paper", max_order_size: int = 100):
            self.mode = mode
            self.max_order_size = max_order_size

    class PaperTradingEngine:
        def __init__(self):
            self.cash_balance = 0.0

    def collect_market_data(sources):
        return []

try:
    from arbitragebot.storage.supabase import (
        adjust_position,
        count_trades,
        fetch_positions,
        fetch_trades,
        get_supabase_client,
        record_trade,
        store_odds,
    )
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    def get_supabase_client(): return None
    def fetch_positions(client): return {}
    def fetch_trades(client): return []
    def count_trades(client): return 0

try:
    from .trades import router as trades_router
except ImportError:
    trades_router = None

try:
    from .socket_server import manager as ws_manager
except ImportError:
    ws_manager = None

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
if trades_router:
    app.include_router(trades_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    if not ws_manager:
        await websocket.close(code=1000)
        return
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


@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """Real-time data stream to frontend dashboard."""
    await websocket.accept()
    update_interval = 2  # Send update every 2 seconds
    
    try:
        while True:
            import asyncio
            try:
                # Collect market data
                sources_config = _load_sources_config()
                opportunities_raw = collect_market_data(sources_config)
                
                # Get database data
                client = get_supabase_client()
                positions_dict = fetch_positions(client)
                trades_list = fetch_trades(client)
                
                # Format opportunities for frontend
                opportunities = []
                for opp in opportunities_raw:
                    opportunities.append({
                        "market_id": opp.event_id,
                        "sport": opp.sport.upper(),
                        "league": opp.league.upper(),
                        "home_team": opp.home_team,
                        "away_team": opp.away_team,
                        "selection": opp.selection,
                        "price": opp.price,
                        "implied_probability": opp.implied_probability,
                        "venue": opp.source,
                        "edge": 0.0,
                        "recommended_side": opp.selection,
                    })
                
                # Format positions
                positions = [
                    {
                        "position_id": pos_id,
                        "market_id": pos_id,
                        "quantity": qty,
                        "unrealized_pnl": 0.0,
                    }
                    for pos_id, qty in positions_dict.items()
                    if qty != 0
                ]
                
                # Format trades (last 50)
                trades = [
                    {
                        "trade_id": trade.get("trade_id", ""),
                        "market_id": trade.get("event_id", ""),
                        "timestamp": trade.get("timestamp", ""),
                        "side": "buy",
                        "stake": trade.get("stake", 0),
                        "price": trade.get("price", 0),
                        "status": trade.get("status", ""),
                        "pnl": 0.0,
                    }
                    for trade in trades_list[-50:] if trade
                ]
                
                # Build state
                state = {
                    "opportunities": opportunities,
                    "positions": positions,
                    "trades": trades,
                    "metrics": {
                        "total_trades": len(trades_list),
                        "cash_balance": 10000.0,
                        "portfolio_value": 10000.0,
                        "total_pnl": 0.0,
                        "win_rate": 0.0,
                        "sharpe_ratio": 0.0,
                        "max_drawdown": 0.0,
                        "open_positions": len([q for q in positions_dict.values() if q != 0]),
                    },
                    "health": {
                        "kalshi": {"status": "connected", "latency": 45},
                        "draftkings": {"status": "disconnected", "latency": 85},
                        "espn": {"status": "connected", "latency": 120},
                        "supabase": {"status": "connected", "latency": 25},
                    },
                    "mode": "paper",
                }
                
                # Send to frontend
                await websocket.send_json(state)
                
                # Wait before next update
                await asyncio.sleep(update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in stream: {e}")
                await asyncio.sleep(1)
                
    except WebSocketDisconnect:
        print("Frontend disconnected from /stream")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()


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
        self.events = deque(maxlen=100)  # Keep last 100 events
        self.health = {
            "kalshi": {"status": "unknown", "latency": 0, "last_check": None},
            "draftkings": {"status": "unknown", "latency": 0, "last_check": None},
            "espn": {"status": "unknown", "latency": 0, "last_check": None},
            "supabase": {"status": "unknown", "latency": 0, "last_check": None},
        }

    def set_mode(self, mode: str) -> None:
        self.mode = TradingConfig(mode=mode, max_order_size=self.mode.max_order_size)
        self.add_event(f"Trading mode changed to {mode.upper()}", "info")

    def add_event(self, message: str, event_type: str = "info") -> None:
        """Add event to recent events log"""
        self.events.appendleft({
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "type": event_type
        })

    def update_health(self, feed: str, status: str, latency: int = 0) -> None:
        """Update health status for a data feed"""
        if feed in self.health:
            self.health[feed] = {
                "status": status,
                "latency": latency,
                "last_check": datetime.utcnow().isoformat()
            }


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
    STATE.add_event(f"Fetched odds for {len(data)} markets", "info")
    return [asdict(item) for item in data]


@app.post("/mode")
async def set_mode(payload: ModeRequest) -> dict:
    STATE.set_mode(payload.mode)
    STATE.add_event(f"Trading mode changed to {payload.mode.upper()}", "info")
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
        STATE.add_event(f"Paper mode: Simulated fill at ${order.price:.2f}", "info")
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
    STATE.add_event(f"Placed order on Kalshi: ${order.size} {order.side.upper()}", "success")
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


@app.get("/health")
async def health_status() -> Dict:
    """Return health status of all data feeds"""
    # Try to update status by checking each source
    try:
        sources_config = _load_sources_config()
        # Attempt to fetch data (this will update health status indirectly)
        collect_market_data(sources_config)
        
        # Mark major sources as connected if we got here
        if sources_config.get("kalshi"):
            STATE.update_health("kalshi", "connected", 45)
        if sources_config.get("draftkings"):
            STATE.update_health("draftkings", "connected", 85)
        if sources_config.get("espn"):
            STATE.update_health("espn", "connected", 120)
    except Exception as e:
        # If data collection fails, mark sources as disconnected
        STATE.update_health("kalshi", "disconnected", 0)
        STATE.update_health("draftkings", "disconnected", 0)
        STATE.update_health("espn", "disconnected", 0)
    
    # Check Supabase
    try:
        client = get_supabase_client()
        if client:
            STATE.update_health("supabase", "connected", 25)
        else:
            STATE.update_health("supabase", "disconnected", 0)
    except Exception:
        STATE.update_health("supabase", "disconnected", 0)
    
    return STATE.health


@app.get("/events")
async def recent_events(limit: int = 50) -> List[Dict]:
    """Return recent events"""
    return list(STATE.events)[:limit]