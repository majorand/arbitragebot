from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


MarketType = Literal["moneyline", "spread", "total", "binary"]


@dataclass
class NormalizedOdds:
    sport: str
    league: str
    event_id: str
    start_time: datetime
    event_name: Optional[str]
    home_team: str
    away_team: str
    market_type: MarketType
    selection: str
    price: float
    implied_probability: float
    source: str
    last_updated: datetime
    american_odds: Optional[float] = None


@dataclass
class OrderRequest:
    market_id: str
    side: Literal["buy", "sell"]
    price: float
    size: float
    order_type: Literal["limit", "market"]
    time_in_force: Optional[str] = None


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str]
    status: str
    message: Optional[str] = None