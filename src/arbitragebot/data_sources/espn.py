from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Iterable, List, Optional

from arbitragebot.schemas import NormalizedOdds
from arbitragebot.utils.http import build_session, request_json
from arbitragebot.utils.odds import american_to_decimal
from arbitragebot.utils.time import parse_iso_datetime

LOGGER = logging.getLogger(__name__)

# Rate limiting: respect ESPN's undocumented API with reasonable delays
RATE_LIMIT_DELAY = 0.5  # 500ms between requests


class ESPNDataSource:
    """ESPN public API data source. Uses undocumented but publicly accessible endpoints.
    
    Base URLs:
    - site.api.espn.com: Scores, teams, standings
    - sports.core.api.espn.com: Odds, detailed stats
    - cdn.espn.com: Live/fast data
    """
    
    def __init__(self) -> None:
        self.site_api = "https://site.api.espn.com/apis/site/v2"
        self.core_api = "https://sports.core.api.espn.com/v2"
        self.session = build_session()
        self._last_request_time = 0.0

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting to be respectful to ESPN's API."""
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def fetch_scoreboard(self, sport: str, league: str) -> List[dict]:
        """Fetch events/games from ESPN scoreboard.
        
        Args:
            sport: Sport type (football, basketball, baseball, hockey, etc.)
            league: League code (nfl, nba, mlb, nhl, college-football, etc.)
        
        Returns:
            List of events/games
        """
        self._enforce_rate_limit()
        url = f"{self.site_api}/sports/{sport}/{league}/scoreboard"
        LOGGER.debug("Fetching ESPN scoreboard from %s", url)
        try:
            payload = request_json(self.session, "GET", url, timeout=10)
            return payload.get("events", [])
        except Exception as e:
            LOGGER.error("Failed to fetch ESPN scoreboard: %s", e)
            return []

    def fetch_event_odds(self, sport: str, league: str, event_id: str) -> Optional[dict]:
        """Fetch odds for a specific event from core API.
        
        Args:
            sport: Sport type
            league: League code
            event_id: Event ID from scoreboard
        
        Returns:
            Odds data if available
        """
        self._enforce_rate_limit()
        url = f"{self.core_api}/sports/{sport}/leagues/{league}/events/{event_id}/competitions/{event_id}/odds"
        LOGGER.debug("Fetching ESPN odds from %s", url)
        try:
            payload = request_json(self.session, "GET", url, timeout=10)
            if payload and payload.get("items"):
                return payload
            return None
        except Exception as e:
            LOGGER.debug("Odds not available for event %s: %s", event_id, e)
            return None

    def normalize_events(
        self, raw_events: Iterable[dict], sport: str = "", league: str = ""
    ) -> List[NormalizedOdds]:
        """Convert ESPN scoreboard events to normalized odds format.
        
        Each competition is normalized into moneyline (home/away) odds.
        Fetches real odds from core API when available.
        """
        normalized: List[NormalizedOdds] = []
        now = datetime.utcnow()

        for event in raw_events:
            competitions = event.get("competitions", [])
            if not competitions:
                continue

            competition = competitions[0]
            competitors = competition.get("competitors", [])
            if len(competitors) < 2:
                continue

            # Identify home and away teams
            home_team = next(
                (t for t in competitors if t.get("homeAway") == "home"),
                competitors[0],
            )
            away_team = next(
                (t for t in competitors if t.get("homeAway") == "away"),
                competitors[1],
            )

            home_name = home_team.get("team", {}).get("displayName", "")
            away_name = away_team.get("team", {}).get("displayName", "")
            event_id = str(event.get("id", ""))
            event_date = event.get("date", now.isoformat())

            # Fetch odds for this event
            odds_data = self.fetch_event_odds(sport, league, event_id) if event_id else None
            home_ml_american = 0.0
            away_ml_american = 0.0

            if odds_data:
                # Parse moneyline odds from the first odds provider
                items = odds_data.get("items", [])
                if items:
                    first_odds = items[0]
                    home_odds = first_odds.get("homeTeamOdds", {})
                    away_odds = first_odds.get("awayTeamOdds", {})
                    
                    # Get moneyline from current odds, fallback to close, then open
                    home_ml_american = (
                        home_odds.get("moneyLine") or
                        home_odds.get("close", {}).get("moneyLine", {}).get("value") or
                        home_odds.get("open", {}).get("moneyLine", {}).get("value") or
                        0.0
                    )
                    away_ml_american = (
                        away_odds.get("moneyLine") or
                        away_odds.get("close", {}).get("moneyLine", {}).get("value") or
                        away_odds.get("open", {}).get("moneyLine", {}).get("value") or
                        0.0
                    )

            # Create home team odds
            if home_ml_american:
                home_decimal = american_to_decimal(home_ml_american)
                home_prob = 1.0 / home_decimal if home_decimal > 1.0 else 0.0
            else:
                home_decimal = 0.0
                home_prob = 0.0

            normalized.append(
                NormalizedOdds(
                    sport=event.get("sport", {}).get("name", sport or "unknown"),
                    league=event.get("league", {}).get("name", league or "unknown"),
                    event_id=event_id,
                    event_name=event.get("name") or f"{away_name} at {home_name}",
                    start_time=parse_iso_datetime(event_date),
                    home_team=home_name,
                    away_team=away_name,
                    market_type="moneyline",
                    selection="home",
                    price=home_decimal,
                    american_odds=home_ml_american,
                    implied_probability=home_prob,
                    source="espn",
                    last_updated=now,
                )
            )

            # Create away team odds
            if away_ml_american:
                away_decimal = american_to_decimal(away_ml_american)
                away_prob = 1.0 / away_decimal if away_decimal > 1.0 else 0.0
            else:
                away_decimal = 0.0
                away_prob = 0.0

            normalized.append(
                NormalizedOdds(
                    sport=event.get("sport", {}).get("name", sport or "unknown"),
                    league=event.get("league", {}).get("name", league or "unknown"),
                    event_id=event_id,
                    event_name=event.get("name") or f"{away_name} at {home_name}",
                    start_time=parse_iso_datetime(event_date),
                    home_team=home_name,
                    away_team=away_name,
                    market_type="moneyline",
                    selection="away",
                    price=away_decimal,
                    american_odds=away_ml_american,
                    implied_probability=away_prob,
                    source="espn",
                    last_updated=now,
                )
            )

        return normalized

    def get_upcoming_games(
        self, sport: str = "football", league: str = "nfl"
    ) -> List[NormalizedOdds]:
        """Convenience method to fetch and normalize upcoming games.
        
        Args:
            sport: Sport type (default: football)
            league: League code (default: nfl)
        
        Returns:
            List of normalized odds for upcoming games
        """
        raw_events = self.fetch_scoreboard(sport, league)
        return self.normalize_events(raw_events, sport=sport, league=league)