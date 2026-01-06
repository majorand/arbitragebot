from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Iterable, List, Sequence

import requests

from arbitragebot.schemas import NormalizedOdds
from arbitragebot.utils.time import parse_iso_datetime

LOGGER = logging.getLogger(__name__)


class FanaticsDataSource:
    """Fanatics Sportsbook data source for live odds."""

    def __init__(
        self,
        base_url: str | None = None,
        min_interval_seconds: int = 120,
        limit: int = 500,
    ) -> None:
        self.base_url = base_url or os.getenv(
            "FANATICS_BASE_URL", "https://api.fanatics.com/api/v3"
        )
        self.min_interval_seconds = min_interval_seconds
        self.limit = limit
        self._last_fetch_ts: float = 0.0
        self._cached: List[NormalizedOdds] = []

    def _should_skip(self) -> bool:
        return (time.time() - self._last_fetch_ts) < self.min_interval_seconds

    def fetch_markets(self) -> List[NormalizedOdds]:
        """Fetch and normalize markets from Fanatics API."""
        if self._should_skip():
            LOGGER.debug("Fanatics: Using cached data (rate limit check)")
            return self._cached

        try:
            LOGGER.debug("Attempting Fanatics fetch from: %s/betting/featured", self.base_url)
            resp = requests.get(
                f"{self.base_url}/betting/featured",
                params={"limit": self.limit},
                timeout=10,
            )
            resp.raise_for_status()
            payload = resp.json()
            LOGGER.info("Fanatics fetch succeeded")
        except Exception as exc:
            LOGGER.warning("Fanatics fetch failed: %s", exc)
            LOGGER.info("Returning cached Fanatics data: %d markets", len(self._cached))
            return self._cached

        markets = payload.get("events") or payload.get("data") or []
        if not isinstance(markets, list):
            LOGGER.warning(f"Unexpected Fanatics response type: {type(markets)}")
            markets = []

        normalized = self._normalize_markets(markets)
        LOGGER.info("Fanatics normalized %d markets", len(normalized))
        self._cached = normalized
        self._last_fetch_ts = time.time()
        return normalized

    def fetch_raw_markets(self) -> List[dict]:
        """Fetch raw market data from Fanatics (not normalized)."""
        try:
            resp = requests.get(
                f"{self.base_url}/betting/featured",
                params={"limit": self.limit},
                timeout=10,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            LOGGER.warning("Fanatics raw fetch failed: %s", exc)
            return []

        markets = payload.get("events") or payload.get("data") or []
        if not isinstance(markets, list):
            LOGGER.warning(f"Unexpected Fanatics response type: {type(markets)}")
            return []

        return markets

    def _normalize_markets(self, markets: Iterable[dict]) -> List[NormalizedOdds]:
        """Convert Fanatics API events to NormalizedOdds.
        
        IMPORTANT: Fanatics moneyline markets (Home Win / Away Win) are the equivalent
        of Kalshi's binary YES/NO markets. Both represent the same outcome from different
        perspectives, enabling cross-provider arbitrage detection.
        
        Fanatics outcome: "Home Team to Win" (moneyline) ↔ Kalshi outcome: "Home Team YES"
        """
        normalized: List[NormalizedOdds] = []
        now = datetime.now(timezone.utc)

        markets_list = list(markets) if markets else []
        LOGGER.debug(f"_normalize_markets called with {len(markets_list)} markets")

        if not markets_list:
            LOGGER.warning("Fanatics markets list is empty")
            return normalized

        if markets_list:
            first_market = markets_list[0]
            LOGGER.info(f"First Fanatics market keys: {list(first_market.keys())[:10]}")

        for idx, event in enumerate(markets_list):
            try:
                event_id = str(event.get("event_id") or event.get("id") or "").strip()
                if not event_id:
                    continue

                # Extract event info
                name = event.get("name") or event.get("title") or ""
                sport = event.get("sport") or event.get("category") or "fanatics"
                league = event.get("league") or "fanatics"

                # Parse start time
                start_time_raw = (
                    event.get("event_datetime")
                    or event.get("start_time")
                    or event.get("started_at")
                )
                start_time = (
                    parse_iso_datetime(start_time_raw) if start_time_raw else now
                )

                # Parse teams from matchup
                home_team, away_team = self._parse_teams_from_matchup(event)

                # Get markets/selections
                markets = event.get("markets") or event.get("odds") or []
                if not markets:
                    continue

                # Process moneyline markets (most common for cross-provider overlap)
                # These are binary: Home Win vs Away Win = equivalent to Kalshi YES/NO
                moneyline_count = 0
                for market in markets:
                    market_type = market.get("market_type") or market.get("type") or ""
                    if "moneyline" not in market_type.lower():
                        continue

                    moneyline_count += 1
                    selections = market.get("selections") or market.get("outcomes") or []
                    
                    # Collect all selections for this moneyline market (should be 2: home and away)
                    selections_by_team = {}
                    for selection in selections:
                        try:
                            sel_name = selection.get("name") or selection.get("label") or ""
                            if not sel_name:
                                continue

                            # Extract decimal odds
                            odds_val = selection.get("decimal_odds") or selection.get(
                                "odds"
                            )
                            if odds_val is None:
                                continue

                            try:
                                odds_float = float(odds_val)
                                # Convert decimal odds to implied probability
                                if odds_float > 0:
                                    prob = 1.0 / odds_float
                                    prob = min(max(prob, 0.01), 0.99)
                                else:
                                    continue
                            except (TypeError, ValueError):
                                continue

                            selections_by_team[sel_name] = {
                                "prob": prob,
                                "odds": odds_float
                            }
                            
                            normalized.append(
                                NormalizedOdds(
                                    sport=str(sport)[:50],
                                    league=str(league)[:50],
                                    event_id=event_id[:100],
                                    event_name=str(name)[:200],
                                    start_time=start_time,
                                    home_team=str(home_team)[:100],
                                    away_team=str(away_team)[:100],
                                    market_type="moneyline",
                                    selection=str(sel_name).lower()[:50],
                                    price=float(prob),
                                    implied_probability=float(prob),
                                    source="fanatics",
                                    last_updated=now,
                                    american_odds=None,
                                )
                            )
                        except Exception as e:
                            if idx < 3:
                                LOGGER.debug(
                                    f"Error processing Fanatics selection in market {idx}: {e}"
                                )
                            continue
                    
                    # Log binary market capture for arbitrage detection
                    if len(selections_by_team) >= 2:
                        LOGGER.debug(
                            f"Fanatics binary moneyline captured for {name}: "
                            f"{', '.join(selections_by_team.keys())} "
                            f"(ready for Kalshi cross-provider arbitrage)"
                        )

            except Exception as exc:
                if idx < 3:
                    LOGGER.debug(
                        f"Error normalizing Fanatics event at index {idx}: {exc}"
                    )
                continue

        LOGGER.info(
            f"Fanatics _normalize_markets: input {len(markets_list)} markets, output {len(normalized)} normalized odds"
        )
        return normalized

    def _parse_teams_from_matchup(self, event: dict) -> tuple[str, str]:
        """Extract home and away teams from Fanatics event data.

        Fanatics typically provides teams in a competitors array or matchup field.
        """
        competitors = event.get("competitors") or []
        if isinstance(competitors, list) and len(competitors) >= 2:
            home = competitors[0].get("name") or competitors[0].get("team_name") or ""
            away = competitors[1].get("name") or competitors[1].get("team_name") or ""
            return (home[:30], away[:30])

        # Try to parse from name/title
        name = event.get("name") or event.get("title") or ""
        if " vs " in name.lower():
            parts = name.lower().split(" vs ")
            return (parts[0].strip()[:30], parts[1].strip()[:30])

        if " @ " in name.lower():
            parts = name.lower().split(" @ ")
            return (parts[1].strip()[:30], parts[0].strip()[:30])

        return ("", "")
