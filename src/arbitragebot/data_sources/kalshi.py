from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Iterable, List, Optional
import re

from arbitragebot.schemas import NormalizedOdds
from arbitragebot.utils.http import build_session, request_json
from arbitragebot.utils.time import parse_iso_datetime

LOGGER = logging.getLogger(__name__)


class KalshiDataSource:
    """Kalshi prediction market data source.
    
    Kalshi trades on political, economic, and event outcomes.
    The API uses yes/no binary contracts with decimal odds (0-1 for implied probability).
    """
    
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        # Use the elections API endpoint as it resolves more reliably
        self.base_url = base_url or os.getenv("KALSHI_API", "https://api.elections.kalshi.com/trade-api/v2")
        self.api_key = api_key
        self.session = build_session()
        LOGGER.info("Initialized Kalshi data source with base_url: %s", self.base_url)

    def fetch_markets(self, limit: int = 100) -> List[dict]:
        """Fetch available markets from Kalshi.
        
        Args:
            limit: Maximum number of markets to fetch (default 100)
            
        Returns:
            List of market dictionaries
        """
        url = f"{self.base_url}/markets?limit={limit}"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
        
        LOGGER.debug("Fetching Kalshi markets from %s", url)
        try:
            response = request_json(self.session, "GET", url, headers=headers)
            markets = response.get("markets", []) if isinstance(response, dict) else response
            LOGGER.info("Fetched %d markets from Kalshi", len(markets))
            return markets
        except Exception as e:
            LOGGER.error("Error fetching Kalshi markets: %s", e)
            return []

    def normalize_markets(self, raw_markets: Iterable[dict]) -> List[NormalizedOdds]:
        """Normalize Kalshi markets to standard odds format.
        
        Kalshi uses binary yes/no contracts with decimal prices (0-100, representing cents).
        Each market has yes_bid/yes_ask and no_bid/no_ask prices.
        Price of 25 = 0.25 decimal odds = 75% implied probability for "no" outcome.
        
        Args:
            raw_markets: Raw market data from Kalshi API
            
        Returns:
            List of normalized odds
        """
        normalized: List[NormalizedOdds] = []
        now = datetime.utcnow()
        
        for market in raw_markets:
            try:
                event_id = market.get("id", "")
                ticker = market.get("ticker", "")
                title = market.get("title", "")
                status = market.get("status", "")
                
                # Skip inactive markets
                if status != "active":
                    continue
                
                # Use Kalshi title verbatim for UI, but still parse teams for matching
                event_name = title or ticker or event_id
                # Parse title to extract teams/candidates
                # Kalshi titles are like: "Will x win?" or "x vs y - winner?"
                home_team, away_team = self._parse_title(title)
                
                # Extract category as league (politics, sports, economy, etc.)
                category = market.get("category", "markets")
                
                # Get expiration time
                start_time = market.get("expiration_time") or now.isoformat()
                
                # Kalshi prices are in cents (0-100), convert to decimal (0-1)
                # Price of 25 = $0.25 = 0.25 decimal odds
                yes_price_cents = market.get("yes_bid", 0)
                no_price_cents = market.get("no_bid", 0)
                
                # Convert cents to decimal
                yes_price = float(yes_price_cents) / 100.0 if yes_price_cents else 0
                no_price = float(no_price_cents) / 100.0 if no_price_cents else 0
                
                # Yes and no probabilities should sum to 1 (or close to it for mid prices)
                # If yes_bid=25 (0.25), no_bid should be ~75 (0.75)
                # The spread represents the bookmaker's margin
                
                # Create yes contract entry
                if yes_price > 0 and yes_price <= 1:
                    normalized.append(
                        NormalizedOdds(
                            sport=category,
                            league="kalshi",
                            event_id=event_id,
                            event_name=event_name,
                            start_time=parse_iso_datetime(start_time),
                            home_team=home_team or "Yes",
                            away_team=away_team or "Outcome",
                            market_type="binary",
                            selection="yes",
                            price=yes_price,  # Decimal odds (0-1)
                            implied_probability=yes_price,
                            source="kalshi",
                            last_updated=now,
                        )
                    )
                
                # Create no contract entry
                if no_price > 0 and no_price <= 1:
                    normalized.append(
                        NormalizedOdds(
                            sport=category,
                            league="kalshi",
                            event_id=event_id,
                            event_name=event_name,
                            start_time=parse_iso_datetime(start_time),
                            home_team=home_team or "No",
                            away_team=away_team or "Outcome",
                            market_type="binary",
                            selection="no",
                            price=no_price,
                            implied_probability=no_price,
                            source="kalshi",
                            last_updated=now,
                        )
                    )
                    
            except Exception as e:
                LOGGER.warning("Error normalizing market %s: %s", market.get("id"), e)
                continue
        
        LOGGER.info("Normalized %d markets from Kalshi", len(normalized))
        return normalized

    def _parse_title(self, title: str) -> tuple[str, str]:
        """Parse market title to extract teams/candidates.
        
        Examples:
            "Will Cleveland win?" -> ("Cleveland", "")
            "x vs y - winner?" -> ("x", "y")
            "yes Detroit wins..." -> ("Detroit", "")
        
        Args:
            title: Market title string
            
        Returns:
            Tuple of (home_team, away_team)
        """
        if not title:
            return ("", "")
        
        # Try "x vs y" pattern
        vs_match = re.search(r"(\w+)\s+vs\.?\s+(\w+)", title, re.IGNORECASE)
        if vs_match:
            return (vs_match.group(1), vs_match.group(2))
        
        # Try "Will x" or similar pattern
        will_match = re.search(r"(?:Will|Will\s+)(\w+)", title, re.IGNORECASE)
        if will_match:
            return (will_match.group(1), "")
        
        # Fallback: use first capitalized word
        words = title.split()
        for word in words:
            if word and word[0].isupper():
                return (word.rstrip("?"), "")
        
        return ("", "")