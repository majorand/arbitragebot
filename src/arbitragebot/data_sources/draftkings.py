from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List

from arbitragebot.schemas import NormalizedOdds
from arbitragebot.utils.http import build_session, request_json
from arbitragebot.utils.time import parse_iso_datetime

LOGGER = logging.getLogger(__name__)


class DraftKingsDataSource:
    """DraftKings odds data via public endpoints.

    Note: only use endpoints and request patterns that comply with DraftKings terms of service.
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = build_session()

    def fetch_odds(self, league: str) -> List[dict]:
        url = f"{self.base_url}/eventgroups/{league}"
        LOGGER.debug("Fetching DraftKings odds from %s", url)
        headers = {"User-Agent": "Mozilla/5.0"}
        payload = request_json(self.session, "GET", url, headers=headers)
        return payload.get("events", [])

    def normalize_odds(self, raw_events: Iterable[dict]) -> List[NormalizedOdds]:
        normalized: List[NormalizedOdds] = []
        now = datetime.utcnow()
        for event in raw_events:
            start_date = event.get("startDate") or now.isoformat()
            normalized.append(
                NormalizedOdds(
                    sport=event.get("sport", "unknown"),
                    league=event.get("league", "unknown"),
                    event_id=str(event.get("eventId", event.get("id"))),
                    start_time=parse_iso_datetime(start_date),
                    home_team=event.get("homeTeam", ""),
                    away_team=event.get("awayTeam", ""),
                    market_type="moneyline",
                    selection="",
                    price=0.0,
                    implied_probability=0.0,
                    source="draftkings",
                    last_updated=now,
                )
            )
        return normalized