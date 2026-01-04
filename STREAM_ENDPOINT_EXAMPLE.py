"""
Example WebSocket /stream endpoint implementation for web/backend/app.py

This replaces or extends the existing /ws endpoint to provide real-time data
that the frontend dashboard consumes.
"""

import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect
from pathlib import Path
import os

# Assuming these are already imported in app.py
# from arbitragebot.main import collect_market_data
# from arbitragebot.storage.supabase import (
#     fetch_positions, fetch_trades, count_trades, get_supabase_client
# )


async def stream_bot_state(websocket: WebSocket) -> None:
    """
    Streams current bot state to frontend via WebSocket.
    Called from @app.websocket("/stream")
    
    Expected message format sent to frontend matches frontend store schema:
    {
        "opportunities": [
            {
                "market_id": str,
                "sport": str,
                "league": str,
                "home_team": str,
                "away_team": str,
                "selection": str,
                "edge": float,  # arbitrage edge %
                "recommended_side": str,
                "venue": str,
                "price": float,
                "implied_probability": float
            }
        ],
        "positions": [...],
        "trades": [...],
        "metrics": {...},
        "health": {...},
        "mode": "paper" | "live"
    }
    """
    
    await websocket.accept()
    update_interval = 2  # Send update every 2 seconds
    
    try:
        while True:
            try:
                # Collect current state
                state = await build_current_state()
                
                # Send to frontend
                await websocket.send_json(state)
                
                # Wait before next update
                await asyncio.sleep(update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error building state: {e}")
                await asyncio.sleep(1)
                
    except WebSocketDisconnect:
        print("Frontend disconnected from /stream")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()


async def build_current_state() -> dict:
    """
    Builds the complete bot state for frontend consumption.
    This is called every 2 seconds by the stream endpoint.
    """
    
    try:
        # 1. FETCH LIVE MARKET DATA
        # These functions are from arbitragebot/main.py
        sources_config = _load_sources_config()
        opportunities_raw = collect_market_data(sources_config)  # List[NormalizedOdds]
        
        # 2. FETCH POSITIONS & TRADES FROM DATABASE
        client = get_supabase_client()
        positions_dict = fetch_positions(client)  # Dict[str, float]
        trades_list = fetch_trades(client)  # List[dict]
        total_trades_count = count_trades(client)  # int
        
        # 3. FORMAT OPPORTUNITIES FOR FRONTEND
        opportunities = [
            {
                "market_id": opp.event_id,
                "sport": opp.sport.upper(),
                "league": opp.league.upper(),
                "home_team": opp.home_team,
                "away_team": opp.away_team,
                "selection": opp.selection,
                "price": opp.price,
                "implied_probability": opp.implied_probability,
                "venue": opp.source,  # "kalshi", "draftkings", "espn", etc
                "edge": calculate_edge(opp),  # You implement edge calculation
                "recommended_side": get_recommended_side(opp),  # yes/no/over/under
            }
            for opp in opportunities_raw
        ]
        
        # 4. FORMAT POSITIONS FOR FRONTEND
        positions = [
            {
                "position_id": pos_id,
                "market_id": pos_id,
                "quantity": qty,
                "unrealized_pnl": calculate_position_pnl(pos_id, qty),
            }
            for pos_id, qty in positions_dict.items()
            if qty != 0  # Only open positions
        ]
        
        # 5. FORMAT TRADES FOR FRONTEND (last 50)
        trades = [
            {
                "trade_id": trade["trade_id"],
                "market_id": trade["event_id"],
                "timestamp": trade["timestamp"],
                "side": "buy",  # or "sell" - extract from trade if available
                "stake": trade["stake"],
                "price": trade["price"],
                "status": trade["status"],
                "pnl": calculate_trade_pnl(trade),
            }
            for trade in trades_list[-50:]  # Last 50 trades
        ]
        
        # 6. CALCULATE METRICS
        cash_balance = STATE.paper_engine.cash_balance  # From your STATE object
        total_position_value = sum(
            calculate_position_value(pos_id, qty)
            for pos_id, qty in positions_dict.items()
        )
        
        metrics = {
            "total_trades": total_trades_count,
            "cash_balance": cash_balance,
            "portfolio_value": cash_balance + total_position_value,
            "total_pnl": calculate_total_pnl(trades_list),
            "win_rate": calculate_win_rate(trades_list),
            "sharpe_ratio": calculate_sharpe_ratio(trades_list),
            "max_drawdown": calculate_max_drawdown(trades_list),
            "open_positions": len([q for q in positions_dict.values() if q != 0]),
        }
        
        # 7. CHECK DATA SOURCE HEALTH
        health = await check_source_health(sources_config)
        
        # 8. GET CURRENT MODE (paper/live)
        current_mode = STATE.mode.mode
        
        # 9. BUILD COMPLETE STATE
        state = {
            "opportunities": opportunities,
            "positions": positions,
            "trades": trades,
            "metrics": metrics,
            "health": health,
            "mode": current_mode,
        }
        
        return state
        
    except Exception as e:
        print(f"Error in build_current_state: {e}")
        # Return safe default state on error
        return get_default_state()


def get_default_state() -> dict:
    """Returns safe default state when data collection fails"""
    return {
        "opportunities": [],
        "positions": [],
        "trades": [],
        "metrics": {
            "total_trades": 0,
            "cash_balance": 0,
            "portfolio_value": 0,
            "total_pnl": 0,
            "win_rate": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "open_positions": 0,
        },
        "health": {
            "kalshi": {"status": "unknown"},
            "draftkings": {"status": "unknown"},
            "espn": {"status": "unknown"},
            "supabase": {"status": "unknown"},
        },
        "mode": "paper",
    }


async def check_source_health(sources_config: dict) -> dict:
    """
    Check health/latency of each data source.
    Returns status for dashboard health monitor.
    """
    health = {}
    
    # Check Kalshi
    try:
        start = datetime.now()
        kalshi = KalshiDataSource(
            base_url=sources_config.get("kalshi", {}).get("base_url", "https://api.kalshi.com"),
            api_key=os.getenv("KALSHI_API_KEY"),
        )
        kalshi.fetch_markets()  # Quick ping
        latency = (datetime.now() - start).total_seconds() * 1000
        health["kalshi"] = {
            "status": "connected",
            "latency": int(latency),
            "last_check": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        health["kalshi"] = {
            "status": "disconnected",
            "latency": None,
            "error": str(e),
        }
    
    # Check DraftKings
    try:
        start = datetime.now()
        dk = DraftKingsDataSource(
            base_url=sources_config.get("draftkings", {}).get("base_url", 
                    "https://sportsbook.draftkings.com/sites/US-SB/api/v5")
        )
        dk.fetch_odds("42648")  # Quick ping
        latency = (datetime.now() - start).total_seconds() * 1000
        health["draftkings"] = {
            "status": "connected",
            "latency": int(latency),
            "last_check": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        health["draftkings"] = {
            "status": "disconnected",
            "latency": None,
            "error": str(e),
        }
    
    # Check ESPN
    try:
        start = datetime.now()
        espn = ESPNDataSource()
        espn.fetch_events("basketball", "nba")  # Quick ping
        latency = (datetime.now() - start).total_seconds() * 1000
        health["espn"] = {
            "status": "connected",
            "latency": int(latency),
            "last_check": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        health["espn"] = {
            "status": "disconnected",
            "latency": None,
            "error": str(e),
        }
    
    # Check Supabase
    try:
        start = datetime.now()
        client = get_supabase_client()
        client.table("trades").select("COUNT(*)").execute()
        latency = (datetime.now() - start).total_seconds() * 1000
        health["supabase"] = {
            "status": "connected",
            "latency": int(latency),
            "last_check": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        health["supabase"] = {
            "status": "disconnected",
            "latency": None,
            "error": str(e),
        }
    
    return health


# ============================================================================
# HELPER FUNCTIONS - Implement these based on your bot logic
# ============================================================================

def calculate_edge(opportunity) -> float:
    """
    Calculate arbitrage edge for an opportunity.
    This depends on your specific strategy.
    
    Example: If you have two markets with different odds,
    edge = (payout1 - stake) - (stake to break even on market2)
    """
    # TODO: Implement based on your strategy
    return 0.05  # Example: 5% edge


def get_recommended_side(opportunity) -> str:
    """
    Determine which side to bet on for maximum edge.
    Returns: "yes", "no", "over", "under"
    """
    # TODO: Implement based on your strategy
    return "yes"


def calculate_position_pnl(position_id: str, quantity: float) -> float:
    """Calculate unrealized P&L for an open position"""
    # TODO: Get current price and calculate
    return quantity * 0.01


def calculate_position_value(position_id: str, quantity: float) -> float:
    """Get current value of a position"""
    # TODO: Get current market price
    return quantity * 0.5


def calculate_trade_pnl(trade: dict) -> float:
    """Calculate P&L for a specific trade"""
    # TODO: If trade is closed, calculate realized P&L
    return 0.0


def calculate_total_pnl(trades: List[dict]) -> float:
    """Sum P&L across all trades"""
    return sum(trade.get("pnl", 0) for trade in trades)


def calculate_win_rate(trades: List[dict]) -> float:
    """
    Calculate win rate from trade history.
    win_rate = winning_trades / total_trades
    """
    if not trades:
        return 0.0
    winning = len([t for t in trades if t.get("pnl", 0) > 0])
    return winning / len(trades)


def calculate_sharpe_ratio(trades: List[dict]) -> float:
    """Calculate Sharpe ratio from returns"""
    # TODO: Implement Sharpe calculation
    return 0.0


def calculate_max_drawdown(trades: List[dict]) -> float:
    """Calculate maximum drawdown from equity curve"""
    # TODO: Implement max drawdown calculation
    return 0.0


def _load_sources_config() -> dict:
    """Load sources configuration from yaml"""
    sources_path = Path(os.getenv("SOURCES_CONFIG", "config/example_sources.yaml"))
    return load_yaml(sources_path).get("sources", {})


# ============================================================================
# UPDATE web/backend/app.py
# ============================================================================

# Replace the existing @app.websocket("/ws") with:
#
# @app.websocket("/stream")
# async def websocket_stream(websocket: WebSocket) -> None:
#     """
#     Real-time data stream to frontend dashboard.
#     Frontend connects to ws://localhost:8000/stream
#     """
#     await stream_bot_state(websocket)
