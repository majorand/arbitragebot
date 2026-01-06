"""Provider-specific normalizers that convert raw API responses to canonical schema."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from arbitragebot.normalization.schemas import (
    CanonicalEvent, CanonicalMarket, CanonicalOutcome,
    Sport, MarketType, OutcomeType,
    PROVIDER_KALSHI, PROVIDER_FANATICS, PROVIDER_ESPN
)
from arbitragebot.normalization.mappings import (
    KALSHI_MARKET_TYPE_MAP, ESPN_MARKET_TYPE_MAP,
    KALSHI_SPORT_MAP, ESPN_SPORT_MAP,
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
            # Kalshi/Fanatics: price is decimal odds or probability
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
                event_name=title or "",
                provider_event_ids={PROVIDER_KALSHI: event_id}
            )
            
            # Create YES/NO market from Kalshi's binary pricing
            # YES = market resolves true (event happens), NO = market resolves false
            # This binary structure enables direct arbitrage comparison with:
            #   - Fanatics moneyline (Home Win YES vs Away Win NO)
            #   - ESPN spread/total (favored YES vs underdog NO)
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


class FanaticsNormalizer(BaseNormalizer):
    """Normalize Fanatics API responses to canonical schema."""
    
    def normalize_market(self, event: Dict[str, Any]) -> Optional[CanonicalEvent]:
        """Convert raw Fanatics event to canonical event."""
        try:
            event_id = event.get("event_id") or event.get("id")
            if not event_id:
                return None
            
            name = event.get("name") or event.get("title") or ""
            sport_str = (event.get("sport") or "football").lower()
            league_str = (event.get("league") or "fanatics").lower()
            
            # Map sport
            if "football" in sport_str or "nfl" in league_str:
                sport = Sport.NFL
            elif "basketball" in sport_str or "nba" in league_str:
                sport = Sport.NBA
            elif "soccer" in sport_str or "football" in league_str:
                sport = Sport.SOCCER
            else:
                sport = Sport.OTHER
            
            # Parse participants
            home_team, away_team = self._parse_competitors(event)
            
            # Start time
            start_time_str = event.get("event_datetime") or event.get("start_time")
            start_time = (
                datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                if start_time_str
                else datetime.utcnow()
            )
            
            event_obj = CanonicalEvent(
                event_id="",
                sport=sport,
                league=league_str,
                home_team=home_team,
                away_team=away_team,
                start_time=start_time,
                event_name=name or "",
                provider_event_ids={PROVIDER_FANATICS: event_id}
            )
            
            # Extract moneyline market if available - Fanatics uses moneyline for sports betting
            markets = event.get("markets") or []
            moneyline_outcomes = {}  # Track outcomes by team/selection to build proper YES/NO binary market
            
            for market in markets:
                market_type = market.get("market_type") or ""
                if "moneyline" not in market_type.lower():
                    continue
                
                selections = market.get("selections") or []
                
                for selection in selections:
                    sel_name = selection.get("name") or ""
                    odds_val = selection.get("decimal_odds")
                    
                    if not sel_name or odds_val is None:
                        continue
                    
                    try:
                        odds_float = float(odds_val)
                        # Convert decimal odds to implied probability
                        prob = 1.0 / odds_float if odds_float > 0 else 0.5
                        prob = min(max(prob, 0.01), 0.99)
                    except (TypeError, ValueError):
                        continue
                    
                    moneyline_outcomes[sel_name.lower()] = {
                        "name": sel_name,
                        "prob": prob,
                        "odds": odds_float,
                        "outcome_id": selection.get("outcome_id") or sel_name
                    }
                
                # Once we have moneyline outcomes, build YES/NO binary market
                if moneyline_outcomes:
                    # Map selections to home/away
                    home_outcome = None
                    away_outcome = None
                    
                    for sel_lower, outcome_data in moneyline_outcomes.items():
                        if home_team and home_team.lower() in sel_lower:
                            home_outcome = outcome_data
                        elif away_team and away_team.lower() in sel_lower:
                            away_outcome = outcome_data
                    
                    # If we have both home and away, create YES/NO binary market
                    if home_outcome and away_outcome:
                        outcomes = [
                            CanonicalOutcome(
                                outcome_type=OutcomeType.YES,
                                title=f"{home_team} to win",
                                implied_probability=home_outcome["prob"],
                                price=home_outcome["prob"],
                                provider_outcome_id=home_outcome["outcome_id"]
                            ),
                            CanonicalOutcome(
                                outcome_type=OutcomeType.NO,
                                title=f"{away_team} to win",
                                implied_probability=away_outcome["prob"],
                                price=away_outcome["prob"],
                                provider_outcome_id=away_outcome["outcome_id"]
                            )
                        ]
                        
                        market_obj = CanonicalMarket(
                            market_id="",
                            market_type=MarketType.YES_NO,
                            outcomes=outcomes,
                            provider_market_ids={PROVIDER_FANATICS: event_id}
                        )
                        event_obj.markets.append(market_obj)
                    
                    break  # Only process first moneyline market
            
            return event_obj if event_obj.markets else None
        
        except Exception as e:
            LOGGER.warning(f"Failed to normalize Fanatics event: {e}")
            return None
    
    def _parse_competitors(self, event: dict) -> tuple[str, str]:
        """Extract home and away team names from Fanatics event."""
        competitors = event.get("competitors") or []
        if isinstance(competitors, list) and len(competitors) >= 2:
            home = (
                competitors[0].get("name")
                or competitors[0].get("team_name")
                or ""
            )
            away = (
                competitors[1].get("name")
                or competitors[1].get("team_name")
                or ""
            )
            return (home[:50], away[:50])
        
        # Fallback: parse from name
        name = event.get("name") or ""
        if " vs " in name.lower():
            parts = name.split(" vs ")
            return (parts[0].strip()[:50], parts[1].strip()[:50])
        
        return ("", "")


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
                event_name=f"{away_team} @ {home_team}",
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
