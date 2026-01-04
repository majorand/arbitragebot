from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List

from arbitragebot.schemas import NormalizedOdds
from arbitragebot.utils.http import build_session, request_json
from arbitragebot.utils.time import parse_iso_datetime

LOGGER = logging.getLogger(__name__)


class FanDuelDataSource:
    """FanDuel odds data via public endpoints.
    
    FanDuel provides publicly accessible odds through their API.
    No authentication required for odds data.
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = build_session()

    def fetch_odds(self) -> List[dict]:
        """Fetch available odds from FanDuel."""
        url = f"{self.base_url}/events"
        LOGGER.debug("Fetching FanDuel odds from %s", url)
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            payload = request_json(self.session, "GET", url, headers=headers)
            return payload.get("events", [])
        except Exception as e:
            LOGGER.warning("Failed to fetch FanDuel odds: %s", e)
            return []

    def normalize_odds(self, raw_events: Iterable[dict]) -> List[NormalizedOdds]:
        """Normalize FanDuel odds to standard format."""
        normalized: List[NormalizedOdds] = []
        now = datetime.utcnow()
        
        for event in raw_events:
            try:
                start_date = event.get("eventDate") or now.isoformat()
                
                # Extract market data
                markets = event.get("markets", [])
                for market in markets:
                    runners = market.get("runners", [])
                    for runner in runners:
                        price = float(runner.get("price", {}).get("decimal", 0))
                        if price <= 0 or price > 2.0:
                            continue
                            
                        # Convert decimal odds to implied probability
                        implied = 1.0 / price if price > 0 else 0.5
                        
                        normalized.append(
                            NormalizedOdds(
                                sport=event.get("sport", "unknown").lower(),
                                league=event.get("league", "unknown").lower(),
                                event_id=str(event.get("eventId", "")),
                                start_time=parse_iso_datetime(start_date),
                                home_team=event.get("homeTeam", ""),
                                away_team=event.get("awayTeam", ""),
                                market_type=market.get("marketType", "moneyline").lower(),
                                selection=runner.get("name", "unknown"),
                                price=price,
                                implied_probability=min(max(implied, 0.0), 1.0),
                                source="fanduel",
                                last_updated=now,
                            )
                        )
            except Exception as e:
                LOGGER.debug("Error normalizing FanDuel event: %s", e)
                continue
        
        return normalized
