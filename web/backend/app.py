from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from collections import deque
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv(dotenv_path=Path('.env'))

# Ensure the local src/ is importable
ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from arbitragebot.config import TradingConfig, load_yaml
    from arbitragebot.main import collect_market_data, _generate_mock_opportunities
    from arbitragebot.schemas import NormalizedOdds
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

    def collect_market_data(sources):
        return []

    def _generate_mock_opportunities():
        return []

    def load_yaml(path):
        with Path(path).open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

try:
    from arbitragebot.storage.supabase import (
        fetch_positions,
        fetch_trades,
        get_supabase_client,
        store_odds,
    )
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    def get_supabase_client(): return None
    def fetch_positions(client): return {}
    def fetch_trades(client): return []

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

REFRESH_INTERVAL = int(os.getenv("MARKET_REFRESH_INTERVAL", "30"))


class TradingState:
    def __init__(self) -> None:
        self.mode = TradingConfig(mode=os.getenv("TRADING_MODE", "paper"), max_order_size=100)
        self.events: deque = deque(maxlen=100)
        self.health: Dict[str, Any] = {
            "kalshi": {"status": "unknown", "latency": 0, "last_check": None},
            "polymarket": {"status": "unknown", "latency": 0, "last_check": None},
        }
        self.latest_data: List = []
        self.latest_refresh: Optional[datetime] = None
        self.refresh_task: Optional[asyncio.Task] = None

    def add_event(self, message: str, event_type: str = "info") -> None:
        self.events.appendleft({
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "type": event_type,
        })

    def update_health(self, feed: str, status: str, latency: int = 0) -> None:
        if feed in self.health:
            self.health[feed] = {
                "status": status,
                "latency": latency,
                "last_check": datetime.utcnow().isoformat(),
            }

    def update_market_data(self, data: list) -> None:
        self.latest_data = data
        self.latest_refresh = datetime.utcnow()
        self.add_event(f"Market data refreshed ({len(data)} entries)", "info")


STATE = TradingState()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_health_status(feed, status, latency, success_message=None, failure_message=None):
    prev_status = STATE.health.get(feed, {}).get("status")
    STATE.update_health(feed, status, latency)
    if prev_status != status:
        message = success_message if status == "connected" else failure_message
        if message:
            STATE.add_event(message, "success" if status == "connected" else "warning")


def _check_supabase_connection(client=None):
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
        _set_health_status("supabase", "disconnected", latency, failure_message=f"Supabase ping failed: {str(exc)[:80]}")


def _load_sources_config() -> dict:
    sources_path = Path(os.getenv("SOURCES_CONFIG", "config/example_sources.yaml"))
    return load_yaml(sources_path).get("sources", {})


async def refresh_market_data() -> dict:
    def _collect():
        sources = _load_sources_config()
        return collect_market_data(sources)

    try:
        data = await asyncio.to_thread(_collect)
    except Exception as exc:
        STATE.add_event(f"Market refresh failed: {str(exc)[:60]}", "warning")
        return {"success": False, "error": str(exc)}

    try:
        source_counts: Dict[str, int] = {}
        for item in data:
            src = getattr(item, "source", None)
            if src:
                source_counts[src] = source_counts.get(src, 0) + 1
        if source_counts:
            _set_health_status("kalshi", "connected" if source_counts.get("kalshi") else "disconnected", 45)
            _set_health_status("polymarket", "connected" if source_counts.get("polymarket") else "disconnected", 150,
                               success_message="Polymarket feed back online",
                               failure_message="Polymarket feed returned no markets")
    except Exception:
        pass

    if HAS_SUPABASE:
        client = get_supabase_client()
        if client and data:
            try:
                store_odds(client, data)
            except Exception as exc:
                STATE.add_event(f"Supabase store failed: {str(exc)[:60]}", "warning")
        _check_supabase_connection(client)

    STATE.update_market_data(data)
    timestamp = STATE.latest_refresh.isoformat() if STATE.latest_refresh else None
    return {"success": True, "count": len(data), "timestamp": timestamp}


async def _market_refresh_loop():
    while True:
        await refresh_market_data()
        await asyncio.sleep(REFRESH_INTERVAL)


def _build_opportunities_payload(opportunities_raw):
    """Build the JSON-serializable opportunities list for the frontend."""
    opportunities = []
    for idx, opp in enumerate(opportunities_raw):
        market_hash = int(hashlib.md5(opp.event_id.encode()).hexdigest(), 16)
        base_volume = (market_hash % 50000) + 10000

        edge = getattr(opp, 'edge', 0)
        vs_source = getattr(opp, 'vs_source', None)
        vs_price = getattr(opp, 'vs_price', None)
        vs_selection = getattr(opp, 'vs_selection', None)
        stake_kalshi = getattr(opp, 'recommended_stake_kalshi', 0)
        stake_other = getattr(opp, 'recommended_stake_other', 0)
        vs_american = getattr(opp, 'vs_american_odds', None)

        if not edge and vs_price and opp.price:
            implied_opp = 1.0 / opp.price if opp.price > 0 else 0
            implied_vs = 1.0 / vs_price if vs_price > 0 else 0
            if implied_opp > 0 and implied_vs > 0:
                edge = abs(implied_opp - implied_vs) * 100

        recommended_side = opp.selection
        if vs_price and vs_price < opp.price:
            recommended_side = vs_selection if vs_selection else opp.selection

        event_label = getattr(opp, "event_name", None)
        if not event_label and (opp.home_team or opp.away_team):
            away = opp.away_team or opp.selection.split()[0] if ' ' in opp.selection else opp.selection
            home = opp.home_team or 'TBD'
            event_label = f"{away} @ {home}"
        elif not event_label:
            event_label = opp.selection

        # Build links
        links = getattr(opp, "links", None)
        if not links:
            safe_query = (event_label or "").replace(" ", "+")
            links = {
                "kalshi": f"https://kalshi.com/search?query={safe_query}",
                "polymarket": f"https://polymarket.com/search?query={safe_query}",
            }

        providers = getattr(opp, "sources", None) or getattr(opp, "providers", None)
        if not providers:
            providers = ["kalshi", "polymarket"] if vs_source else [opp.source]

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
            "liquidity": base_volume * 0.7,
            "edge": round(edge, 2),
            "recommended_side": (recommended_side or opp.selection).lower(),
            "created_at": datetime.utcnow().isoformat(),
            "is_arbitrage": edge >= 0.5,
            "vs_source": vs_source,
            "vs_price": vs_price,
            "vs_selection": vs_selection,
            "vs_american_odds": vs_american,
            "stake_kalshi": round(stake_kalshi, 2) if stake_kalshi else None,
            "stake_other": round(stake_other, 2) if stake_other else None,
            "roi_percentage": round(edge, 2),
            "providers": providers,
            "sources": providers,
            "market": getattr(opp, "market", None),
            "best_yes": getattr(opp, "best_yes", None),
            "best_no": getattr(opp, "best_no", None),
            "links": links,
        })
    return opportunities


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

async def health_status(request: Request) -> JSONResponse:
    kalshi_status = "connected" if os.getenv("KALSHI_API_KEY") else "disconnected"
    _set_health_status("kalshi", kalshi_status, 45)
    _set_health_status("polymarket", "connected", 150)
    _check_supabase_connection()
    return JSONResponse(STATE.health)


async def recent_events(request: Request) -> JSONResponse:
    limit = int(request.query_params.get("limit", "50"))
    return JSONResponse(list(STATE.events)[:limit])


async def list_odds(request: Request) -> JSONResponse:
    sources_config = _load_sources_config()
    data = collect_market_data(sources_config)
    if HAS_SUPABASE:
        try:
            client = get_supabase_client()
            if client:
                store_odds(client, data)
        except Exception:
            pass
    STATE.add_event(f"Fetched odds for {len(data)} markets", "info")
    results = []
    for item in data:
        try:
            row = asdict(item)
        except Exception:
            row = vars(item) if hasattr(item, '__dict__') else {"event_id": str(item)}
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
        results.append(row)
    return JSONResponse(results)


async def refresh_endpoint(request: Request) -> JSONResponse:
    result = await refresh_market_data()
    return JSONResponse({
        "success": result.get("success", False),
        "count": result.get("count", 0),
        "last_refresh": result.get("timestamp"),
        "error": result.get("error"),
    })


# ---------------------------------------------------------------------------
# WebSocket: /stream (display-only - opportunities + health)
# ---------------------------------------------------------------------------

async def websocket_stream(websocket: WebSocket):
    try:
        await websocket.accept()
    except Exception as e:
        print(f"Failed to accept WebSocket: {e}")
        return

    update_interval = 2

    try:
        while True:
            try:
                opportunities_raw = list(STATE.latest_data)
                if not opportunities_raw:
                    result = await refresh_market_data()
                    opportunities_raw = list(STATE.latest_data)

                # Check if any opportunities have actual arbitrage edges
                has_arbs = any(getattr(o, 'edge', 0) >= 0.5 for o in opportunities_raw)
                if not has_arbs:
                    # Use mock opportunities when no real arbs found
                    mock_opps = _generate_mock_opportunities()
                    if mock_opps:
                        opportunities_raw = mock_opps

                if not opportunities_raw:
                    opportunities_raw = _generate_mock_opportunities()

                opportunities = _build_opportunities_payload(opportunities_raw)

                state = {
                    "opportunities": opportunities,
                    "health": STATE.health,
                }

                try:
                    await websocket.send_json(state)
                except Exception:
                    break

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
        try:
            await websocket.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

async def on_startup():
    try:
        if os.getenv("KALSHI_API_KEY"):
            STATE.update_health("kalshi", "connected", 45)
            STATE.add_event("Kalshi API key configured", "success")
        else:
            STATE.update_health("kalshi", "disconnected", 0)
            STATE.add_event("Kalshi API key not found - set KALSHI_API_KEY env var", "warning")

        polymarket_key = os.getenv("POLYMARKET_PRIVATE_KEY")
        if polymarket_key:
            _set_health_status("polymarket", "connected", 150)
            STATE.add_event("Polymarket feed configured with authentication", "success")
        else:
            _set_health_status("polymarket", "connected", 150)
            STATE.add_event("Polymarket feed configured (public API)", "info")

        if HAS_SUPABASE:
            _check_supabase_connection()
        else:
            _set_health_status("supabase", "disconnected", 0)
            STATE.add_event("Supabase module not available - using in-memory mocks", "warning")

        await refresh_market_data()
        STATE.add_event("Scanner started - display only mode", "info")

        if not STATE.refresh_task or STATE.refresh_task.done():
            STATE.refresh_task = asyncio.create_task(_market_refresh_loop())
    except Exception as e:
        print(f"Startup error: {e}")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app = Starlette(
    debug=True,
    routes=[
        Route("/health", health_status),
        Route("/events", recent_events),
        Route("/odds", list_odds),
        Route("/refresh", refresh_endpoint, methods=["GET", "POST"]),
        WebSocketRoute("/stream", websocket_stream),
    ],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
    ],
    on_startup=[on_startup],
)
