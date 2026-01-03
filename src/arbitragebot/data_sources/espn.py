from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List

from arbitragebot.schemas import NormalizedOdds
from arbitragebot.utils.http import build_session, request_json
from arbitragebot.utils.time import parse_iso_datetime

LOGGER = logging.getLogger(__name__)


class ESPNDataSource:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = build_session()

    def fetch_events(self, sport: str, league: str) -> List[dict]:
        url = f"{self.base_url}/sports/{sport}/{league}/scoreboard"
        LOGGER.debug("Fetching ESPN events from %s", url)
        payload = request_json(self.session, "GET", url)
        return payload.get("events", [])

    def normalize_events(self, raw_events: Iterable[dict]) -> List[NormalizedOdds]:
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
            home_team = next(
                (team for team in competitors if team.get("homeAway") == "home"),
                competitors[0],
            )
            away_team = next(
                (team for team in competitors if team.get("homeAway") == "away"),
                competitors[1],
            )
            event_date = event.get("date") or now.isoformat()
            normalized.append(
                NormalizedOdds(
                    sport=event.get("sport", {}).get("name", "unknown"),
                    league=event.get("league", {}).get("name", "unknown"),
                    event_id=str(event.get("id")),
                    start_time=parse_iso_datetime(event_date),
                    home_team=home_team.get("team", {}).get("displayName", ""),
                    away_team=away_team.get("team", {}).get("displayName", ""),
                    market_type="moneyline",
                    selection="",
                    price=0.0,
                    implied_probability=0.0,
                    source="espn",
                    last_updated=now,
                )
            )
        return normalized