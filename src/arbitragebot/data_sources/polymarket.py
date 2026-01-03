from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List

from arbitragebot.schemas import NormalizedOdds
from arbitragebot.utils.http import build_session, request_json
from arbitragebot.utils.time import parse_iso_datetime

LOGGER = logging.getLogger(__name__)


class PolymarketDataSource:
    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = build_session()

    def fetch_markets(self) -> List[dict]:
        url = f"{self.base_url}/markets"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
        LOGGER.debug("Fetching Polymarket markets from %s", url)
        return request_json(self.session, "GET", url, headers=headers)

    def normalize_markets(self, raw_markets: Iterable[dict]) -> List[NormalizedOdds]:
        normalized: List[NormalizedOdds] = []
        now = datetime.utcnow()
        for market in raw_markets:
            start_time = market.get("start_time") or now.isoformat()
            for outcome in market.get("outcomes", []):
                price = float(outcome.get("price", 0))
                implied = max(min(price, 1.0), 0.0)
                normalized.append(
                    NormalizedOdds(
                        sport=market.get("sport", "unknown"),
                        league=market.get("league", "unknown"),
                        event_id=str(market.get("event_id", market.get("id"))),
                        start_time=parse_iso_datetime(start_time),
                        home_team=market.get("home_team", ""),
                        away_team=market.get("away_team", ""),
                        market_type="moneyline",
                        selection=outcome.get("name", "unknown"),
                        price=price,
                        implied_probability=implied,
                        source="polymarket",
                        last_updated=now,
                    )
                )
        return normalized