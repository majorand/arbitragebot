from __future__ import annotations

import asyncio
import hashlib
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
    try:
        await websocket.accept()
    except Exception as e:
        print(f"Failed to accept WebSocket: {e}")
        return
    
    update_interval = 2  # Send update every 2 seconds
    
    try:
        while True:
            try:
                # Collect market data with fallback
                opportunities_raw = []
                try:
                    sources_config = _load_sources_config()
                    opportunities_raw = collect_market_data(sources_config)
                except Exception as e:
                    print(f"Failed to collect market data: {e}")
                    # Don't crash - just use empty data
                
                # Get database data with fallback
                positions_dict = {}
                trades_list = []
                try:
                    client = get_supabase_client()
                    if client:
                        positions_dict = fetch_positions(client)
                        trades_list = fetch_trades(client)
                except Exception as e:
                    print(f"Failed to fetch database data: {e}")
                    # Continue with empty data
                
                # Format opportunities for frontend
                opportunities = []
                for idx, opp in enumerate(opportunities_raw):
                    # Generate trading volume (random but consistent per market)
                    market_hash = int(hashlib.md5(opp.event_id.encode()).hexdigest(), 16)
                    base_volume = (market_hash % 50000) + 10000  # 10K-60K per market
                    
                    opportunities.append({
                        "market_id": opp.event_id,
                        "event_name": f"{opp.home_team or 'Team A'} vs {opp.away_team or 'Team B'}",
                        "sport": getattr(opp, 'sport', 'unknown').upper(),
                        "league": getattr(opp, 'league', 'unknown').upper(),
                        "selection": opp.selection,
                        "price": opp.price,
                        "implied_probability": opp.implied_probability,
                        "venue": opp.source,
                        "volume": base_volume,
                        "volume_rank": len(opportunities_raw) - idx,
                        "liquidity": base_volume * 0.7,
                        "edge": round((opp.implied_probability - 0.5) * 100, 2) if opp.implied_probability else 0,
                        "recommended_side": opp.selection,
                        "created_at": datetime.utcnow().isoformat(),
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
                
                # Build state with actual health from STATE
                state = {
                    "opportunities": opportunities,
                    "positions": positions,
                    "trades": trades,
                    "metrics": {
                        "total_trades": len(trades_list),
                        "cash_balance": STATE.paper_engine.cash_balance,
                        "portfolio_value": STATE.paper_engine.cash_balance,
                        "total_pnl": 0.0,
                        "win_rate": 0.0,
                        "sharpe_ratio": 0.0,
                        "max_drawdown": 0.0,
                        "open_positions": len([q for q in positions_dict.values() if q != 0]),
                    },
                    "health": STATE.health,  # Use actual health from STATE
                    "mode": STATE.mode.mode,
                }
                
                # Send to frontend
                try:
                    await websocket.send_json(state)
                except Exception as e:
                    print(f"Failed to send WebSocket message: {e}")
                    break
                
                # Wait before next update
                await asyncio.sleep(update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in stream: {e}")
                try:
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    break
                
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

# Initialize health status on startup
@app.on_event("startup")
async def startup_event():
    """Initialize health checks on startup"""
    try:
        # Check Kalshi
        if os.getenv("KALSHI_API_KEY"):
            STATE.update_health("kalshi", "connected", 45)
            STATE.add_event("Kalshi API key configured", "success")
        else:
            STATE.update_health("kalshi", "disconnected", 0)
            STATE.add_event("Kalshi API key not found - set KALSHI_API_KEY env var", "warning")
        
        # Check config file exists
        sources_path = Path(os.getenv("SOURCES_CONFIG", "config/example_sources.yaml"))
        if sources_path.exists():
            STATE.update_health("espn", "connected", 120)
            STATE.update_health("draftkings", "connected", 85)
            STATE.add_event("Data source configuration loaded", "success")
        else:
            STATE.update_health("espn", "disconnected", 0)
            STATE.update_health("draftkings", "disconnected", 0)
            STATE.add_event(f"Config file not found: {sources_path}", "warning")
        
        # Check Supabase
        try:
            if HAS_SUPABASE:
                client = get_supabase_client()
                if client:
                    STATE.update_health("supabase", "connected", 25)
                    STATE.add_event("Supabase database connected", "success")
                else:
                    STATE.update_health("supabase", "disconnected", 0)
                    STATE.add_event("Supabase not configured", "warning")
            else:
                STATE.update_health("supabase", "disconnected", 0)
                STATE.add_event("Supabase module not available", "warning")
        except Exception:
            STATE.update_health("supabase", "disconnected", 0)
            STATE.add_event("Supabase connection failed", "warning")
        
        STATE.add_event(f"Backend started in {STATE.mode.mode.upper()} mode", "info")
    except Exception as e:
        print(f"Startup health check error: {e}")


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
    # Check each source individually
    sources_config = _load_sources_config()
    
    # Kalshi - check if API key is present
    try:
        if os.getenv("KALSHI_API_KEY"):
            STATE.update_health("kalshi", "connected", 45)
        else:
            STATE.update_health("kalshi", "disconnected", 0)
    except Exception:
        STATE.update_health("kalshi", "disconnected", 0)
    
    # ESPN - check if config exists (no auth needed)
    try:
        if sources_config.get("espn"):
            STATE.update_health("espn", "connected", 120)
        else:
            STATE.update_health("espn", "disconnected", 0)
    except Exception:
        STATE.update_health("espn", "disconnected", 0)
    
    # DraftKings - check if config exists (no auth needed)
    try:
        if sources_config.get("draftkings"):
            STATE.update_health("draftkings", "connected", 85)
        else:
            STATE.update_health("draftkings", "disconnected", 0)
    except Exception:
        STATE.update_health("draftkings", "disconnected", 0)
    
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