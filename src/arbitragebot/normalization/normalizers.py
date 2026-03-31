"""Provider-specific normalizers that convert raw API responses to canonical schema."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from arbitragebot.normalization.schemas import (
    CanonicalEvent, CanonicalMarket, CanonicalOutcome,
    Sport, MarketType, OutcomeType,
    PROVIDER_KALSHI, PROVIDER_POLYMARKET
)
from arbitragebot.normalization.mappings import (
    KALSHI_MARKET_TYPE_MAP,
    KALSHI_SPORT_MAP,
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


class PolymarketNormalizer(BaseNormalizer):
    """Normalize Polymarket API responses to canonical schema."""
    
    def normalize_market(self, market: Dict[str, Any]) -> Optional[CanonicalEvent]:
        """Convert raw Polymarket market to canonical event.
        
        Expected Polymarket market structure:
        {
            "question_id": "...",
            "question": "Will ...",
            "tokens": [
                {"ticker": "YES", "price": 0.52},
                {"ticker": "NO", "price": 0.48}
            ],
            "end_date_iso": "2026-01-10T...",
            "tags": ["sports", "nba"],
            ...
        }
        """
        try:
            event_id = market.get("question_id") or market.get("condition_id") or market.get("id")
            if not event_id:
                return None
            
            title = market.get("question") or market.get("title") or ""
            
            # Extract tags to determine sport
            tags = market.get("tags") or []
            sport = self._map_sport_from_tags(tags)
            
            # Parse participants from title
            home_team, away_team = self._parse_participants(title)
            
            # Start time
            start_time_str = market.get("end_date_iso")
            start_time = datetime.fromisoformat(start_time_str) if start_time_str else datetime.utcnow()
            
            event = CanonicalEvent(
                event_id="",  # PLACEHOLDER - aggregator will compute canonical_event_id()
                sport=sport,
                league="Polymarket",
                home_team=home_team,
                away_team=away_team,
                start_time=start_time,
                event_name=title,
                provider_event_ids={PROVIDER_POLYMARKET: str(event_id)}
            )
            
            # Parse tokens to create YES/NO market
            tokens = market.get("tokens") or []
            if len(tokens) >= 2:
                outcomes = []
                for token in tokens:
                    token_ticker = token.get("ticker", "").upper()
                    token_price = float(token.get("price", 0.5))
                    
                    # Map ticker to outcome type
                    if "YES" in token_ticker:
                        outcome_type = OutcomeType.YES
                    elif "NO" in token_ticker:
                        outcome_type = OutcomeType.NO
                    else:
                        continue
                    
                    outcomes.append(
                        CanonicalOutcome(
                            outcome_type=outcome_type,
                            title=token_ticker,
                            implied_probability=token_price,
                            price=token_price,
                            provider_outcome_id=token.get("token_id") or token_ticker
                        )
                    )
                
                if outcomes:
                    market_obj = CanonicalMarket(
                        market_id="",
                        market_type=MarketType.YES_NO,
                        outcomes=outcomes,
                        provider_market_ids={PROVIDER_POLYMARKET: str(event_id)}
                    )
                    event.markets.append(market_obj)
            
            return event if event.markets else None
        
        except Exception as e:
            LOGGER.warning(f"Failed to normalize Polymarket market: {e}")
            return None
    
    def _map_sport_from_tags(self, tags: List[str]) -> Sport:
        """Map Polymarket tags to Sport enum."""
        tags_lower = [t.lower() for t in tags]
        
        if "nfl" in tags_lower or "football" in tags_lower:
            return Sport.NFL
        elif "nba" in tags_lower or "basketball" in tags_lower:
            return Sport.NBA
        elif "mlb" in tags_lower or "baseball" in tags_lower:
            return Sport.MLB
        elif "nhl" in tags_lower or "hockey" in tags_lower:
            return Sport.NHL
        elif "soccer" in tags_lower or "epl" in tags_lower:
            return Sport.SOCCER
        elif "politics" in tags_lower:
            return Sport.POLITICS
        elif "crypto" in tags_lower:
            return Sport.CRYPTO
        else:
            return Sport.OTHER
    
    def _parse_participants(self, title: str) -> tuple[str, str]:
        """Extract participants from Polymarket title."""
        import re
        
        # Try "X vs Y" or "X v Y" pattern
        vs_match = re.search(r"(.+?)\s+vs?\.?\s+(.+)", title, re.IGNORECASE)
        if vs_match:
            return (vs_match.group(1).strip(), vs_match.group(2).strip())
        
        # Try "Will X beat Y" pattern
        beat_match = re.search(r"Will\s+(.+?)\s+beat\s+(.+?)\??\s*$", title, re.IGNORECASE)
        if beat_match:
            return (beat_match.group(1).strip(), beat_match.group(2).strip())
        
        # Try "X to win" pattern
        win_match = re.search(r"(.+?)\s+to\s+win", title, re.IGNORECASE)
        if win_match:
            return (win_match.group(1).strip(), "")
        
        return ("", "")
