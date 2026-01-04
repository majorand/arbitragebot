from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Iterable, List

from arbitragebot.schemas import NormalizedOdds
from arbitragebot.utils.http import build_session, request_json
from arbitragebot.utils.time import parse_iso_datetime
from arbitragebot.utils.odds import american_to_decimal, decimal_to_probability

LOGGER = logging.getLogger(__name__)


class FanDuelDataSource:
    """FanDuel odds data via public endpoints.
    
    FanDuel provides publicly accessible odds through their API.
    No authentication required for odds data.
    
    Rate limiting: 30 requests per minute recommended.
    """

    def __init__(self, base_url: str, rate_limit_per_minute: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = build_session()
        self.rate_limit = rate_limit_per_minute
        self.last_request_time = 0.0
        self._request_count = 0
        self._window_start = time.time()

    def _check_rate_limit(self) -> None:
        """Enforce rate limiting."""
        now = time.time()
        
        # Reset counter if minute window passed
        if now - self._window_start >= 60:
            self._request_count = 0
            self._window_start = now
        
        # Check if at limit
        if self._request_count >= self.rate_limit:
            sleep_time = 60 - (now - self._window_start)
            if sleep_time > 0:
                LOGGER.info(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
                self._request_count = 0
                self._window_start = time.time()
        
        self._request_count += 1

    def fetch_odds(self, sport: str = "football") -> List[dict]:
        """Fetch available odds from FanDuel.
        
        Args:
            sport: Sport to fetch (e.g., "football", "basketball")
        """
        self._check_rate_limit()
        
        url = f"{self.base_url}/events"
        LOGGER.debug("Fetching FanDuel odds from %s", url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
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
                        # FanDuel uses American odds
                        american_odds = runner.get("price", {}).get("american", 0)
                        if american_odds == 0:
                            continue
                        
                        # Convert to decimal and probability
                        decimal_odds = american_to_decimal(american_odds)
                        implied_prob = decimal_to_probability(decimal_odds)
                        
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
                                price=decimal_odds,
                                implied_probability=implied_prob,
                                source="fanduel",
                                last_updated=now,
                            )
                        )
            except Exception as e:
                LOGGER.debug("Error normalizing FanDuel event: %s", e)
                continue
        
        return normalized
