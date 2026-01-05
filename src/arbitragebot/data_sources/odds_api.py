from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Iterable, List

import requests

from arbitragebot.schemas import NormalizedOdds
from arbitragebot.utils.odds import american_to_decimal
from arbitragebot.utils.time import parse_iso_datetime

LOGGER = logging.getLogger(__name__)

# The Odds API docs: https://the-odds-api.com/
# We keep a simple client with local rate limiting to avoid burning credits.
# Default sport is NBA; adjust via env ODDS_API_SPORT (e.g., basketball_nba, baseball_mlb).


class OddsAPIDataSource:
    """Thin client for The Odds API with caching to limit credit usage."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.the-odds-api.com/v4",
        min_interval_seconds: int = 120,
        default_sport: str = "basketball_nba",
        default_market: str = "h2h",
        regions: str = "us",
        odds_format: str = "american",
        date_format: str = "iso",
    ) -> None:
        self.api_key = api_key or os.getenv("ODDS_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.min_interval_seconds = min_interval_seconds
        self.default_sport = os.getenv("ODDS_API_SPORT", default_sport)
        self.default_market = os.getenv("ODDS_API_MARKET", default_market)
        self.regions = regions
        self.odds_format = odds_format
        self.date_format = date_format

        self._last_fetch_ts: float = 0.0
        self._cached: List[NormalizedOdds] = []

    def _should_skip(self) -> bool:
        return (time.time() - self._last_fetch_ts) < self.min_interval_seconds

    def fetch_odds(self, sport: str | None = None) -> List[NormalizedOdds]:
        """Fetch odds for a single sport/market; caches for min_interval_seconds."""
        if not self.api_key:
            LOGGER.info("Odds API key not set; skipping Odds API fetch")
            return []

        if self._should_skip():
            return self._cached

        target_sport = sport or self.default_sport
        url = f"{self.base_url}/sports/{target_sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": self.regions,
            "markets": self.default_market,
            "oddsFormat": self.odds_format,
            "dateFormat": self.date_format,
        }

        try:
            resp = requests.get(url, params=params, timeout=8)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            LOGGER.warning("Odds API fetch failed: %s", exc)
            return self._cached

        normalized = self._normalize_events(payload, sport=target_sport)
        self._cached = normalized
        self._last_fetch_ts = time.time()
        return normalized

    def _normalize_events(self, events: Iterable[dict], sport: str) -> List[NormalizedOdds]:
        normalized: List[NormalizedOdds] = []
        now = datetime.utcnow()

        for event in events or []:
            try:
                event_id = str(event.get("id", ""))
                commence_time = event.get("commence_time") or now.isoformat()
                home_team = event.get("home_team", "")
                away_team = event.get("away_team", "")
                event_name = event.get("sport_title") or f"{away_team} @ {home_team}" or event_id

                bookmakers = event.get("bookmakers", [])
                if not bookmakers:
                    continue

                # Choose the first bookmaker to minimize parsing (reduces data and credits)
                market = None
                for bm in bookmakers:
                    mkts = bm.get("markets") or []
                    market = next((m for m in mkts if m.get("key") == self.default_market), None)
                    if market:
                        break
                if not market:
                    continue

                outcomes = market.get("outcomes") or []
                for outcome in outcomes:
                    name = outcome.get("name", "")
                    american = outcome.get("price") or 0
                    if not american:
                        continue

                    decimal_price = american_to_decimal(american)
                    implied_prob = 1.0 / decimal_price if decimal_price > 1 else 0.0

                    normalized.append(
                        NormalizedOdds(
                            sport=sport,
                            league=event.get("sport_key", "odds_api"),
                            event_id=event_id,
                            event_name=event_name,
                            start_time=parse_iso_datetime(commence_time),
                            home_team=home_team,
                            away_team=away_team,
                            market_type="moneyline",
                            selection=name.lower(),
                            price=decimal_price,
                            implied_probability=implied_prob,
                            source="odds_api",
                            last_updated=now,
                            american_odds=float(american),
                        )
                    )
            except Exception as exc:
                LOGGER.debug("Error normalizing Odds API event: %s", exc)
                continue

        return normalized
