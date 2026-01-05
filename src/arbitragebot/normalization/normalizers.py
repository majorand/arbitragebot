"""Provider-specific normalizers that convert raw API responses to canonical schema."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from arbitragebot.normalization.schemas import (
    CanonicalEvent, CanonicalMarket, CanonicalOutcome,
    Sport, MarketType, OutcomeType,
    PROVIDER_KALSHI, PROVIDER_POLYMARKET, PROVIDER_ESPN
)
from arbitragebot.normalization.mappings import (
    KALSHI_MARKET_TYPE_MAP, POLYMARKET_MARKET_TYPE_MAP, ESPN_MARKET_TYPE_MAP,
    KALSHI_SPORT_MAP, POLYMARKET_SPORT_MAP, ESPN_SPORT_MAP,
    map_outcome_type, normalize_team_name
)

LOGGER = logging.getLogger(__name__)


class BaseNormalizer:
    """Base normalizer with common utilities."""
    
    @staticmethod
    def price_to_implied_probability(price: float, price_format: str) -> float:
        """Convert price in any format to implied probability (0-1).
        
        Args:
            price: The price value
            price_format: "decimal", "american", or "cents"
            
        Returns:
            Implied probability (0-1)
        """
        if price_format == "decimal":
            # Decimal odds: 2.0 = 50%, 3.0 = 33.3%
            if price <= 0:
                return 0.5
            return 1.0 / price
        
        elif price_format == "american":
            # American odds: +100 = 50%, -110 = 52.38%
            if price > 0:
                return 100.0 / (price + 100.0)
            else:
                return abs(price) / (abs(price) + 100.0)
        
        elif price_format == "cents":
            # Kalshi/Polymarket cents: 50 = $0.50 = 50%
            return price / 100.0
        
        else:
            raise ValueError(f"Unknown price format: {price_format}")


class KalshiNormalizer(BaseNormalizer):
    """Normalize Kalshi API responses to canonical schema."""
    
    def normalize_market(self, market: Dict[str, Any]) -> Optional[CanonicalEvent]:
        """Convert raw Kalshi market to canonical event.
        
        Expected Kalshi market structure:
        {
            "id": "...",
            "ticker": "...",
            "title": "Will ...",
            "yes_bid": 45,  # cents
            "no_bid": 55,
            "category": "sports",
            "expiration_time": "2026-01-10T...",
            ...
        }
        """
        try:
            event_id = market.get("id") or market.get("ticker")
            if not event_id:
                return None
            
            title = market.get("title", "")
            category = market.get("category", "sports")
            
            # Map sport
            sport = KALSHI_SPORT_MAP.get(category, Sport.OTHER)
            
            # Parse participants from title
            home_team, away_team = self._parse_participants(title)
            
            # Start time
            start_time_str = market.get("expiration_time")
            start_time = datetime.fromisoformat(start_time_str) if start_time_str else datetime.utcnow()
            
            # Create event - use placeholder ID, aggregator will compute canonical_event_id
            # This allows proper cross-provider matching
            event = CanonicalEvent(
                event_id="",  # PLACEHOLDER - aggregator will compute canonical_event_id()
                sport=sport,
                league="Kalshi",
                home_team=home_team,
                away_team=away_team,
                start_time=start_time,
                provider_event_ids={PROVIDER_KALSHI: event_id}
            )
            
            # Create YES/NO market
            yes_bid = market.get("yes_bid", 0)
            no_bid = market.get("no_bid", 0)
            
            yes_prob = self.price_to_implied_probability(yes_bid, "cents")
            no_prob = self.price_to_implied_probability(no_bid, "cents")
            
            # Use provider's market ID as placeholder - aggregator will compute canonical key
            market_obj = CanonicalMarket(
                market_id="",  # PLACEHOLDER - aggregator will compute canonical_market_key()
                market_type=MarketType.YES_NO,
                outcomes=[
                    CanonicalOutcome(
                        outcome_type=OutcomeType.YES,
                        title="YES",
                        implied_probability=yes_prob,
                        price=yes_bid,
                        provider_outcome_id="yes"
                    ),
                    CanonicalOutcome(
                        outcome_type=OutcomeType.NO,
                        title="NO",
                        implied_probability=no_prob,
                        price=no_bid,
                        provider_outcome_id="no"
                    )
                ],
                provider_market_ids={PROVIDER_KALSHI: event_id}
            )
            
            event.markets.append(market_obj)
            return event
        
        except Exception as e:
            LOGGER.warning(f"Failed to normalize Kalshi market: {e}")
            return None
    
    def _parse_participants(self, title: str) -> tuple[str, str]:
        """Parse participants from Kalshi title.
        
        Since Kalshi markets are mostly props/predictions (not team sports),
        we use a combined hash of the title as a pseudo-team identifier.
        This ensures each market gets its own canonical event ID.
        """
        # For non-sports markets, use title hash as identifier to ensure uniqueness
        import hashlib
        title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
        
        # Try to extract real teams if it looks like a matchup
        if " vs " in title.lower():
            parts = title.lower().split(" vs ")
            return (parts[0].strip()[:30], parts[1].strip()[:30])
        
        if " @ " in title.lower():
            parts = title.lower().split(" @ ")
            return (parts[1].strip()[:30], parts[0].strip()[:30])  # @ means away @ home
        
        # Default: use title hash to ensure uniqueness
        # "Kalshi" + first 30 chars of title + hash
        title_prefix = title[:20].replace(" ", "_")
        return (f"kalshi_{title_prefix}_{title_hash}", "MARKET")


class PolymarketNormalizer(BaseNormalizer):
    """Normalize Polymarket API responses to canonical schema."""
    
    def normalize_market(self, market: Dict[str, Any]) -> Optional[CanonicalEvent]:
        """Convert raw Polymarket market to canonical event.
        
        Expected Polymarket market structure:
        {
            "id": "...",
            "question_id": "...",
            "question": "Will X happen?",
            "tokens": [
                {"outcome": "YES", "price": 0.65, ...},
                {"outcome": "NO", "price": 0.35, ...}
            ],
            "end_date_iso": "2026-01-10T...",
            "tags": ["nfl", ...],
            ...
        }
        """
        try:
            event_id = market.get("question_id") or market.get("id")
            if not event_id:
                return None
            
            question = market.get("question", "")
            
            # Map sport from tags
            tags = market.get("tags", [])
            sport_tag = tags[0].lower() if tags else ""
            sport = POLYMARKET_SPORT_MAP.get(sport_tag, Sport.OTHER)
            
            # Parse participants
            home_team, away_team = self._parse_participants(question)
            
            # Start time
            start_time_str = market.get("end_date_iso")
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00")) if start_time_str else datetime.utcnow()
            
            # Create event - use placeholder ID, aggregator will compute canonical_event_id
            # This allows proper cross-provider matching
            event = CanonicalEvent(
                event_id="",  # PLACEHOLDER - aggregator will compute canonical_event_id()
                sport=sport,
                league="Polymarket",
                home_team=home_team,
                away_team=away_team,
                start_time=start_time,
                provider_event_ids={PROVIDER_POLYMARKET: event_id}
            )
            
            # Create YES/NO market from tokens
            tokens = market.get("tokens", [])
            outcomes = []
            
            for token in tokens:
                outcome_str = token.get("outcome", "")
                price = float(token.get("price", 0.5))
                
                outcome_type = OutcomeType.YES if "yes" in outcome_str.lower() else OutcomeType.NO
                
                outcomes.append(CanonicalOutcome(
                    outcome_type=outcome_type,
                    title=outcome_str,
                    implied_probability=price,  # Polymarket prices are already probabilities
                    price=price,
                    provider_outcome_id=token.get("id", outcome_str)
                ))
            
            # Use provider's market ID as placeholder - aggregator will compute canonical key
            market_obj = CanonicalMarket(
                market_id="",  # PLACEHOLDER - aggregator will compute canonical_market_key()
                market_type=MarketType.YES_NO,
                outcomes=outcomes,
                provider_market_ids={PROVIDER_POLYMARKET: event_id}
            )
            
            event.markets.append(market_obj)
            return event
        
        except Exception as e:
            LOGGER.warning(f"Failed to normalize Polymarket market: {e}")
            return None
    
    def _parse_participants(self, question: str) -> tuple[str, str]:
        """Parse participants from Polymarket question.
        
        Since Polymarket markets are often predictions (not team sports),
        we use a combined hash of the question as a pseudo-team identifier.
        This ensures each market gets its own canonical event ID.
        """
        # For non-sports markets, use question hash as identifier to ensure uniqueness
        import hashlib
        q_hash = hashlib.md5(question.encode()).hexdigest()[:8]
        
        # Try to extract real teams if it looks like a matchup
        if " @ " in question:
            parts = question.split(" @ ")
            team1 = parts[0].strip()[:30]
            team2 = parts[1].strip()[:30]
            return (team1, team2)
        
        if " vs " in question.lower():
            parts = question.split(" vs ")
            team1 = parts[0].strip()[:30]
            team2 = parts[1].strip()[:30]
            return (team1, team2)
        
        # Default: use question hash to ensure uniqueness
        q_prefix = question[:20].replace(" ", "_")
        return (f"polymarket_{q_prefix}_{q_hash}", "MARKET")


class ESPNNormalizer(BaseNormalizer):
    """Normalize ESPN API responses to canonical schema."""
    
    def normalize_competition(self, competition: Dict[str, Any], sport: Sport) -> Optional[CanonicalEvent]:
        """Convert ESPN competition to canonical event.
        
        Expected ESPN structure (from /odds endpoint):
        {
            "id": "...",
            "competitors": [
                {"id": "...", "team": {"abbreviation": "DET", ...}},
                {"id": "...", "team": {"abbreviation": "CHI", ...}}
            ],
            "startDate": "2026-01-04T...",
            "odds": [
                {"homeTeamOdds": {"value": 1.91}, "awayTeamOdds": {"value": 1.91}, ...}
            ]
        }
        """
        try:
            comp_id = competition.get("id")
            if not comp_id:
                return None
            
            # Extract teams
            competitors = competition.get("competitors", [])
            if len(competitors) < 2:
                return None
            
            home_team = self._extract_team_name(competitors[0])
            away_team = self._extract_team_name(competitors[1])
            
            # Start time
            start_date = competition.get("startDate")
            start_time = datetime.fromisoformat(start_date.replace("Z", "+00:00")) if start_date else datetime.utcnow()
            
            # Create event - use placeholder ID, aggregator will compute canonical_event_id
            # This allows proper cross-provider matching
            event = CanonicalEvent(
                event_id="",  # PLACEHOLDER - aggregator will compute canonical_event_id()
                sport=sport,
                league="ESPN",
                home_team=home_team,
                away_team=away_team,
                start_time=start_time,
                provider_event_ids={PROVIDER_ESPN: comp_id}
            )
            
            # Extract markets from odds
            odds_list = competition.get("odds", [])
            for odds in odds_list:
                market = self._parse_odds_to_market(odds, comp_id)
                if market:
                    event.markets.append(market)
            
            return event
        
        except Exception as e:
            LOGGER.warning(f"Failed to normalize ESPN competition: {e}")
            return None
    
    def _extract_team_name(self, competitor: Dict[str, Any]) -> str:
        """Extract team name from competitor dict."""
        team = competitor.get("team", {})
        return normalize_team_name(team.get("name") or team.get("abbreviation") or "TBD")
    
    def _parse_odds_to_market(self, odds: Dict[str, Any], event_id: str) -> Optional[CanonicalMarket]:
        """Parse ESPN odds object to market."""
        try:
            # Determine market type
            market_type = MarketType.MONEYLINE  # Default
            
            # Moneyline odds
            home_odds = odds.get("homeTeamOdds", {})
            away_odds = odds.get("awayTeamOdds", {})
            
            home_value = float(home_odds.get("value", 0))
            away_value = float(away_odds.get("value", 0))
            
            if home_value <= 0 or away_value <= 0:
                return None
            
            home_prob = self.price_to_implied_probability(home_value, "decimal")
            away_prob = self.price_to_implied_probability(away_value, "decimal")
            
            # Use provider's market ID as placeholder - aggregator will compute canonical key
            market = CanonicalMarket(
                market_id="",  # PLACEHOLDER - aggregator will compute canonical_market_key()
                market_type=market_type,
                outcomes=[
                    CanonicalOutcome(
                        outcome_type=OutcomeType.HOME,
                        title="HOME",
                        implied_probability=home_prob,
                        price=home_value,
                        provider_outcome_id="home"
                    ),
                    CanonicalOutcome(
                        outcome_type=OutcomeType.AWAY,
                        title="AWAY",
                        implied_probability=away_prob,
                        price=away_value,
                        provider_outcome_id="away"
                    )
                ],
                provider_market_ids={PROVIDER_ESPN: event_id}
            )
            
            return market
        
        except Exception as e:
            LOGGER.warning(f"Failed to parse ESPN odds: {e}")
            return None
