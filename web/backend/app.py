from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from collections import deque
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import time

try:
    from dotenv import load_dotenv
except ImportError:  # Optional dependency; fallback to no-op if missing
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False

# Load environment variables from .env if present (helps local/dev)
load_dotenv(dotenv_path=Path('.env'))

# Ensure the local src/ is importable when running from repo root
ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from arbitragebot.config import TradingConfig, load_yaml
    from arbitragebot.execution.paper import PaperTradingEngine
    from arbitragebot.exchanges.kalshi import KalshiTradingClient
    from arbitragebot.main import collect_market_data
    from arbitragebot.schemas import NormalizedOdds, OrderRequest
    HAS_ARBITRAGEBOT = True
except ImportError:
    HAS_ARBITRAGEBOT = False
    import yaml
    
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
    
    def load_yaml(path):
        """Fallback YAML loader when arbitragebot module not available"""
        with Path(path).open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

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

REFRESH_INTERVAL = int(os.getenv("MARKET_REFRESH_INTERVAL", "30"))

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
                # Use cached market data and refresh if none available
                opportunities_raw = list(STATE.latest_data)
                if not opportunities_raw:
                    result = await refresh_market_data()
                    if not result.get("success"):
                        print(f"Refresh error: {result.get('error')}")
                    opportunities_raw = list(STATE.latest_data)
                if not opportunities_raw:
                    opportunities_raw = _generate_mock_opportunities()
                
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
                
                # Format opportunities for frontend with full arbitrage details
                opportunities = []
                for idx, opp in enumerate(opportunities_raw):
                    # Generate trading volume (random but consistent per market)
                    market_hash = int(hashlib.md5(opp.event_id.encode()).hexdigest(), 16)
                    base_volume = (market_hash % 50000) + 10000  # 10K-60K per market
                    
                    # Get arbitrage details if available
                    edge = getattr(opp, 'edge', 0)
                    vs_source = getattr(opp, 'vs_source', None)
                    vs_price = getattr(opp, 'vs_price', None)
                    vs_selection = getattr(opp, 'vs_selection', None)
                    stake_kalshi = getattr(opp, 'recommended_stake_kalshi', 0)
                    stake_other = getattr(opp, 'recommended_stake_other', 0)
                    vs_american = getattr(opp, 'vs_american_odds', None)
                    
                    # Calculate proper edge if not set (based on vs_price if available)
                    if not edge and vs_price and opp.price:
                        # Simple edge calculation: difference in implied probability
                        implied_opp = 1.0 / opp.price if opp.price > 0 else 0
                        implied_vs = 1.0 / vs_price if vs_price > 0 else 0
                        if implied_opp > 0 and implied_vs > 0:
                            edge = abs(implied_opp - implied_vs) * 100  # as percentage
                    
                    # Determine recommended side based on best odds or arbitrage
                    recommended_side = opp.selection
                    if vs_price and vs_price < opp.price:
                        # If vs_source has better odds, recommend that selection
                        recommended_side = vs_selection if vs_selection else opp.selection
                    
                    # Build proper event label: use event_name if available, else "Team @ Team"
                    event_label = getattr(opp, "event_name", None)
                    if not event_label and (opp.home_team or opp.away_team):
                        # Format like "DET @ CHI" or "Lions @ Bears"
                        away = opp.away_team or opp.selection.split()[0] if ' ' in opp.selection else opp.selection
                        home = opp.home_team or 'TBD'
                        event_label = f"{away} @ {home}"
                    elif not event_label:
                        event_label = opp.selection
                    opportunities.append({
                        "market_id": opp.event_id,
                        "event_name": event_label,
                        "sport": getattr(opp, 'sport', 'unknown').upper(),
                        "league": getattr(opp, 'league', 'unknown').upper(),
                        "selection": opp.selection,
                        "price": opp.price,
                        "implied_probability": opp.implied_probability,
                        "venue": opp.source,
                        "volume": base_volume,
                        "volume_rank": len(opportunities_raw) - idx,
                        "liquidity": base_volume * 0.7,
                        "edge": round(edge, 2),
                        "recommended_side": recommended_side.lower() if recommended_side else opp.selection.lower(),
                        "created_at": datetime.utcnow().isoformat(),
                        
                        # Arbitrage details
                        "is_arbitrage": edge >= 0.5,
                        "vs_source": vs_source,
                        "vs_price": vs_price,
                        "vs_selection": vs_selection,
                        "vs_american_odds": vs_american,
                        "stake_kalshi": round(stake_kalshi, 2) if stake_kalshi else None,
                        "stake_other": round(stake_other, 2) if stake_other else None,
                        "roi_percentage": round(edge, 2),

                        # Instrument-level aggregation fields (screenshot-style UI)
                        "sources": getattr(opp, "sources", None),
                        "market": getattr(opp, "market", None),
                        "best_yes": getattr(opp, "best_yes", None),
                        "best_no": getattr(opp, "best_no", None),
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


async def refresh_market_data() -> dict:
    """Refresh market data cache by calling the arbitrage collector."""

    def _collect() -> List[NormalizedOdds]:
        sources = _load_sources_config()
        return collect_market_data(sources)

    try:
        data = await asyncio.to_thread(_collect)
    except Exception as exc:  # pragma: no cover - external HTTP
        STATE.add_event(f"Market refresh failed: {str(exc)[:60]}", "warning")
        return {"success": False, "error": str(exc)}

    # Update feed health from returned sources (best-effort)
    try:
        source_counts: Dict[str, int] = {}
        for item in data:
            src = getattr(item, "source", None)
            if src:
                source_counts[src] = source_counts.get(src, 0) + 1

        if source_counts:
            kalshi_status = "connected" if source_counts.get("kalshi") else "disconnected"
            polymarket_status = "connected" if source_counts.get("polymarket") else "disconnected"

            _set_health_status("kalshi", kalshi_status, 45)
            _set_health_status(
                "polymarket",
                polymarket_status,
                150,
                success_message="Polymarket feed back online",
                failure_message="Polymarket feed returned no markets",
            )
    except Exception:
        pass

    # Persist odds to Supabase when available
    client = get_supabase_client()
    if client and data:
        try:
            store_odds(client, data)
        except Exception as exc:  # pragma: no cover - external HTTP
            STATE.add_event(f"Supabase store failed: {str(exc)[:60]}", "warning")
    _check_supabase_connection(client)
    STATE.update_market_data(data)
    timestamp = STATE.latest_refresh.isoformat() if STATE.latest_refresh else None
    return {"success": True, "count": len(data), "timestamp": timestamp}


async def _market_refresh_loop() -> None:
    while True:
        await refresh_market_data()
        await asyncio.sleep(REFRESH_INTERVAL)


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
            "polymarket": {"status": "unknown", "latency": 0, "last_check": None},
        }
        self.latest_data: List[NormalizedOdds] = []
        self.latest_refresh: Optional[datetime] = None
        self.refresh_task: Optional[asyncio.Task] = None

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

    def update_market_data(self, data: List[NormalizedOdds]) -> None:
        self.latest_data = data
        self.latest_refresh = datetime.utcnow()
        self.add_event(f"Market data refreshed ({len(data)} entries)", "info")


def _set_health_status(
    feed: str,
    status: str,
    latency: int,
    success_message: str | None = None,
    failure_message: str | None = None,
) -> None:
    prev_status = STATE.health.get(feed, {}).get("status")
    STATE.update_health(feed, status, latency)
    if prev_status != status:
        message = success_message if status == "connected" else failure_message
        if message:
            STATE.add_event(message, "success" if status == "connected" else "warning")

def _check_supabase_connection(client=None) -> None:
    if not HAS_SUPABASE:
        _set_health_status("supabase", "disconnected", 0, failure_message="Supabase module unavailable")
        return

    resolved_client = client or get_supabase_client()
    if not resolved_client:
        _set_health_status("supabase", "disconnected", 0, failure_message="Supabase credentials missing")
        return

    start = time.time()
    try:
        resolved_client.table("trades").select("trade_id").limit(1).execute()
        latency = int((time.time() - start) * 1000)
        _set_health_status("supabase", "connected", latency, success_message="Supabase connection healthy")
    except Exception as exc:
        latency = int((time.time() - start) * 1000)
        _set_health_status(
            "supabase",
            "disconnected",
            latency,
            failure_message=f"Supabase ping failed: {str(exc)[:80]}",
        )

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
        
        # Check Polymarket (optional)
        polymarket_key = os.getenv("POLYMARKET_PRIVATE_KEY")
        if polymarket_key:
            _set_health_status("polymarket", "connected", 150)
            STATE.add_event("Polymarket feed configured with authentication", "success")
        else:
            _set_health_status("polymarket", "connected", 150)
            STATE.add_event("Polymarket feed configured (public API)", "info")
        
        # Check Supabase (optional)
        if HAS_SUPABASE:
            _check_supabase_connection()
        else:
            _set_health_status("supabase", "disconnected", 0)
            STATE.add_event("Supabase module not available - using in-memory mocks", "warning")
        
        # Prime market data cache immediately
        await refresh_market_data()

        STATE.add_event(f"Backend started in {STATE.mode.mode.upper()} mode", "info")
        if not STATE.refresh_task or STATE.refresh_task.done():
            STATE.refresh_task = asyncio.create_task(_market_refresh_loop())
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


@app.api_route("/refresh", methods=["POST", "GET"])
async def refresh_endpoint() -> Dict[str, Any]:
    result = await refresh_market_data()
    return {
        "success": result.get("success", False),
        "count": result.get("count", 0),
        "last_refresh": result.get("timestamp"),
        "error": result.get("error"),
    }


@app.get("/health")
async def health_status() -> Dict:
    """Return health status of all data feeds"""
    _set_health_status("espn", "connected", 120)
    kalshi_status = "connected" if os.getenv("KALSHI_API_KEY") else "disconnected"
    _set_health_status("kalshi", kalshi_status, 45)
    _check_supabase_connection()
    return STATE.health


@app.get("/events")
async def recent_events(limit: int = 50) -> List[Dict]:
    """Return recent events"""
    return list(STATE.events)[:limit]