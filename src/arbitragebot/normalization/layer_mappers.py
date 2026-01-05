"""
Provider-specific mappers converting raw API objects to 5 canonical layers.

Each mapper knows how to extract instrument, outcome, expression, context,
and listing information from a provider's API response.
"""

from datetime import datetime
from typing import Tuple, Optional, List
import hashlib

from .canonical_layers import (
    CanonicalInstrument,
    CanonicalOutcome,
    CanonicalOutcomeState,
    CanonicalMarketExpression,
    CanonicalEventContext,
    CanonicalProviderListing,
    InstrumentDomain,
    OutcomeResolution,
    MarketExpressionType,
)


class KalshiLayerMapper:
    """Maps Kalshi API objects to canonical layers."""
    
    def map_to_layers(self, market_obj: dict) -> Tuple[
        CanonicalInstrument,
        CanonicalOutcome,
        CanonicalMarketExpression,
        CanonicalEventContext,
        CanonicalProviderListing,
    ]:
        """
        Map Kalshi market to 5 layers.
        
        Kalshi markets are mostly binary YES/NO on real-world outcomes.
        Example: "Will Vladimir Putin resign before 2025?"
        """
        
        # Extract Kalshi fields
        market_id = market_obj.get("id", "")
        title = market_obj.get("title", "")
        subtitle = market_obj.get("subtitle", "")
        strike_price = market_obj.get("strike_price", 0.5)
        creator_username = market_obj.get("creator_username", "")
        expiration_ts = market_obj.get("expiration_ts", 0)
        expiration_date = datetime.fromtimestamp(expiration_ts / 1000) if expiration_ts else None
        
        # Determine domain from title/subtitle
        domain = self._infer_domain(title, subtitle)
        
        # Layer 1: Instrument
        # Kalshi questions are already pretty good instruments
        # e.g., "Will Jaguars beat Chiefs in Super Bowl?" → instrument
        subject = self._extract_subject(title)
        predicate = self._extract_predicate(title)
        
        instrument = CanonicalInstrument(
            instrument_id="",
            domain=domain,
            subject=subject,
            predicate=predicate,
            description=f"{title}\n{subtitle}",
        )
        # Use subject/predicate directly for deterministic ID
        instrument.instrument_id = CanonicalInstrument.compute_id(
            domain.value,
            subject.replace("_", " ").title(),
            predicate,
        )
        
        # Layer 2: Outcome (Kalshi is always binary YES/NO)
        outcome = CanonicalOutcome(
            outcome_id="",
            instrument_id=instrument.instrument_id,
            outcome_type=OutcomeResolution.BINARY,
            states=[
                CanonicalOutcomeState(
                    state_id="YES",
                    display_name="Yes",
                    resolves_to=True,
                ),
                CanonicalOutcomeState(
                    state_id="NO",
                    display_name="No",
                    resolves_to=False,
                ),
            ],
        )
        outcome.outcome_id = CanonicalOutcome.compute_id(
            instrument.instrument_id,
            OutcomeResolution.BINARY.value,
        )
        
        # Layer 3: Market Expression (Kalshi Binary)
        expr = CanonicalMarketExpression(
            market_expr_id="",
            outcome_id=outcome.outcome_id,
            expression_type=MarketExpressionType.BINARY,
        )
        expr.market_expr_id = CanonicalMarketExpression.compute_id(
            outcome.outcome_id,
            MarketExpressionType.BINARY.value,
        )
        
        # Layer 4: Event Context
        context = CanonicalEventContext(
            context_id="",
            instrument_id=instrument.instrument_id,
            event_name=title,
            event_date=expiration_date,
            participants=[creator_username] if creator_username else [],
        )
        context.context_id = CanonicalEventContext.compute_id(
            instrument.instrument_id,
            context.event_date,
        )
        
        # Layer 5: Provider Listing
        # Kalshi returns best bid/ask; we'll use mid-price
        yes_bid = market_obj.get("yes_bid", 0)
        yes_ask = market_obj.get("yes_ask", 1)
        yes_price = (yes_bid + yes_ask) / 2.0 if (yes_bid and yes_ask) else strike_price
        
        listing = CanonicalProviderListing(
            listing_id=market_id,
            provider_name="kalshi",
            market_expr_id=expr.market_expr_id,
            outcome_id=outcome.outcome_id,
            instrument_id=instrument.instrument_id,
            context_id=context.context_id,
            price=yes_price,
            price_format="probability",
            implied_probability=yes_price,
            raw_api_object=market_obj,
        )
        
        return instrument, outcome, expr, context, listing
    
    def _infer_domain(self, title: str, subtitle: str) -> InstrumentDomain:
        """Infer domain from title/subtitle."""
        text = (title + " " + subtitle).lower()
        
        if any(w in text for w in ["trump", "biden", "election", "congress", "senate"]):
            return InstrumentDomain.POLITICS
        elif any(w in text for w in ["rain", "snow", "weather", "temperature"]):
            return InstrumentDomain.WEATHER
        elif any(w in text for w in ["bitcoin", "ethereum", "crypto", "btc"]):
            return InstrumentDomain.CRYPTO
        elif any(w in text for w in ["gdp", "inflation", "unemployment", "rate"]):
            return InstrumentDomain.MACRO
        
        return InstrumentDomain.OTHER
    
    def _extract_subject(self, title: str) -> str:
        """Extract subject from question - both teams in sorted order."""
        # "Will Jacksonville Jaguars beat Kansas City Chiefs in Super Bowl?"
        # Extract: "Jacksonville Jaguars" and "Kansas City Chiefs"
        # Return in sorted order for determinism
        words = title.split()
        
        # Skip "Will" if present
        start = 1 if words and words[0].lower() == "will" else 0
        
        # Collect words until we hit an action verb
        team_words = []
        for i in range(start, len(words)):
            word = words[i].lower()
            # Stop at action verbs
            if word in ["beat", "defeat", "win", "lose", "in", "on", "at"]:
                break
            clean = word.rstrip("?,.:!;")
            if clean and clean != "the":
                team_words.append(clean)
        
        # Now extract team names - should have at least one team
        # Format as "team1_vs_team2" in sorted order
        if team_words:
            # Simple heuristic: split by prepositions
            # "jacksonville jaguars" + "kansas city chiefs"
            # Look for "and", "vs" patterns - if not found, try to split in half
            subjects = []
            current = []
            
            for word in team_words:
                if word in ["and", "vs", "&"]:
                    if current:
                        subjects.append("_".join(current))
                        current = []
                else:
                    current.append(word)
            
            if current:
                subjects.append("_".join(current))
            
            # If we only got one subject, we need better extraction
            if len(subjects) == 1:
                # Heuristic: look for city names or assume it's one team
                return subjects[0][:50]
            else:
                # Multiple subjects found - sort and join
                subjects_sorted = sorted(subjects)
                return "_vs_".join(subjects_sorted)[:50]
        
        return "unknown"
    
    def _extract_predicate(self, title: str) -> str:
        """Extract predicate - use 'moneyline_winner' for consistency across providers."""
        return "moneyline_winner"


class PolymarketLayerMapper:
    """Maps Polymarket API objects to canonical layers."""
    
    def map_to_layers(self, market_obj: dict) -> Tuple[
        CanonicalInstrument,
        CanonicalOutcome,
        CanonicalMarketExpression,
        CanonicalEventContext,
        CanonicalProviderListing,
    ]:
        """
        Map Polymarket market to 5 layers.
        
        Polymarket markets are mostly binary YES/NO on various outcomes.
        Example: "Will Joe Biden be President on Jan 1, 2025?"
        """
        
        # Extract Polymarket fields
        market_id = market_obj.get("id", "")
        title = market_obj.get("title", "")
        description = market_obj.get("description", "")
        outcomes = market_obj.get("outcomes", ["Yes", "No"])
        creation_date = datetime.fromisoformat(
            market_obj.get("creationDate", datetime.utcnow().isoformat())
        )
        
        # Determine domain
        domain = self._infer_domain(title, description)
        
        # Layer 1: Instrument
        subject = self._extract_subject(title)
        predicate = self._extract_predicate(title, outcomes)
        
        instrument = CanonicalInstrument(
            instrument_id="",
            domain=domain,
            subject=subject,
            predicate=predicate,
            description=description or title,
        )
        instrument.instrument_id = CanonicalInstrument.compute_id(
            domain.value,
            subject.replace("_", " ").title(),
            predicate,
        )
        
        # Layer 2: Outcome
        # Polymarket is typically binary (YES/NO) but can be multi-outcome
        outcome_count = len(outcomes)
        if outcome_count == 2 and "Yes" in outcomes and "No" in outcomes:
            outcome_type = OutcomeResolution.BINARY
            states = [
                CanonicalOutcomeState(state_id="YES", display_name="Yes", resolves_to=True),
                CanonicalOutcomeState(state_id="NO", display_name="No", resolves_to=False),
            ]
        else:
            outcome_type = OutcomeResolution.MULTI
            states = [
                CanonicalOutcomeState(
                    state_id=outcome.upper().replace(" ", "_"),
                    display_name=outcome,
                    resolves_to=i == 0,
                )
                for i, outcome in enumerate(outcomes)
            ]
        
        outcome = CanonicalOutcome(
            outcome_id="",
            instrument_id=instrument.instrument_id,
            outcome_type=outcome_type,
            states=states,
        )
        outcome.outcome_id = CanonicalOutcome.compute_id(
            instrument.instrument_id,
            outcome_type.value,
        )
        
        # Layer 3: Market Expression
        expr = CanonicalMarketExpression(
            market_expr_id="",
            outcome_id=outcome.outcome_id,
            expression_type=MarketExpressionType.YES_NO,
        )
        expr.market_expr_id = CanonicalMarketExpression.compute_id(
            outcome.outcome_id,
            MarketExpressionType.YES_NO.value,
        )
        
        # Layer 4: Event Context
        context = CanonicalEventContext(
            context_id="",
            instrument_id=instrument.instrument_id,
            event_name=title,
            event_date=creation_date,
        )
        context.context_id = CanonicalEventContext.compute_id(
            instrument.instrument_id,
            context.event_date,
        )
        
        # Layer 5: Provider Listing
        # Use YES price from Polymarket
        yes_price = market_obj.get("lastPrice", 0.5)
        
        listing = CanonicalProviderListing(
            listing_id=market_id,
            provider_name="polymarket",
            market_expr_id=expr.market_expr_id,
            outcome_id=outcome.outcome_id,
            instrument_id=instrument.instrument_id,
            context_id=context.context_id,
            price=yes_price,
            price_format="probability",
            implied_probability=yes_price,
            raw_api_object=market_obj,
        )
        
        return instrument, outcome, expr, context, listing
    
    def _infer_domain(self, title: str, description: str) -> InstrumentDomain:
        """Infer domain from title/description."""
        text = (title + " " + description).lower()
        
        if any(w in text for w in ["election", "president", "congress", "senate", "vote"]):
            return InstrumentDomain.POLITICS
        elif any(w in text for w in ["weather", "rain", "snow", "temperature"]):
            return InstrumentDomain.WEATHER
        elif any(w in text for w in ["bitcoin", "ethereum", "crypto", "nft"]):
            return InstrumentDomain.CRYPTO
        elif any(w in text for w in ["gdp", "inflation", "recession", "rate"]):
            return InstrumentDomain.MACRO
        
        return InstrumentDomain.OTHER
    
    def _extract_subject(self, title: str) -> str:
        """Extract subject from title - use canonical form for sports matching."""
        # "Will Jacksonville Jaguars beat Kansas City Chiefs in Super Bowl LIX?"
        text = title.split("?")[0].strip()
        if text.startswith("Will "):
            text = text[5:]
        if text.startswith("the "):
            text = text[4:]
        
        # Get words until "in/on/at/super/bowl" markers
        words = text.split()
        subject_words = []
        for word in words:
            if word.lower() in ["beat", "vs", "win", "lose", "in", "on", "at", "super"]:
                break
            clean = word.lower().rstrip("?,.:!;")
            if clean:
                subject_words.append(clean)
        
        # Should have extracted team names
        # Now sort them for determinism
        if subject_words:
            # Join and return
            return "_".join(subject_words).lower()[:50]
        
        return "unknown"
    
    def _extract_predicate(self, title: str, outcomes: List[str]) -> str:
        """Extract predicate - use 'moneyline_winner' for consistency."""
        return "moneyline_winner"


class ESPNLayerMapper:
    """Maps ESPN API objects to canonical layers (sports betting)."""
    
    def map_to_layers(self, game_obj: dict) -> Tuple[
        CanonicalInstrument,
        CanonicalOutcome,
        CanonicalMarketExpression,
        CanonicalEventContext,
        CanonicalProviderListing,
    ]:
        """
        Map ESPN game to 5 layers.
        
        ESPN games produce multiple instruments:
        - Moneyline (who wins)
        - Spread (by how much)
        - Total (combined score)
        """
        
        # Extract ESPN fields
        game_id = game_obj.get("id", "")
        home_team = game_obj.get("home_team", "Home")
        away_team = game_obj.get("away_team", "Away")
        league = game_obj.get("league", "nba").upper()
        start_time = datetime.fromisoformat(game_obj.get("start_time", datetime.utcnow().isoformat()))
        venue = game_obj.get("venue", "")
        
        # NORMALIZE teams using canonical form: sort alphabetically for determinism
        teams_sorted = sorted([home_team, away_team])
        teams_canonical = "_vs_".join(teams_sorted)  # "Away vs Home" or "Home vs Away" consistently
        
        # Layer 1: Instrument (moneyline winner)
        instrument = CanonicalInstrument(
            instrument_id="",
            domain=InstrumentDomain.SPORTS,
            subject=teams_canonical,
            predicate="moneyline_winner",
            description=f"{away_team} @ {home_team}",
        )
        # Use canonical subject/predicate for ID computation
        instrument.instrument_id = CanonicalInstrument.compute_id(
            InstrumentDomain.SPORTS.value,
            teams_canonical,
            "moneyline_winner",
        )
        
        # Layer 2: Outcome (HOME or AWAY)
        outcome = CanonicalOutcome(
            outcome_id="",
            instrument_id=instrument.instrument_id,
            outcome_type=OutcomeResolution.BINARY_INVERSE,  # Can be 2-way or 3-way with ties
            states=[
                CanonicalOutcomeState(state_id="HOME", display_name=home_team, resolves_to=True),
                CanonicalOutcomeState(state_id="AWAY", display_name=away_team, resolves_to=False),
            ],
        )
        outcome.outcome_id = CanonicalOutcome.compute_id(
            instrument.instrument_id,
            OutcomeResolution.BINARY_INVERSE.value,
        )
        
        # Layer 3: Market Expression (ESPN Moneyline)
        expr = CanonicalMarketExpression(
            market_expr_id="",
            outcome_id=outcome.outcome_id,
            expression_type=MarketExpressionType.MONEYLINE,
        )
        expr.market_expr_id = CanonicalMarketExpression.compute_id(
            outcome.outcome_id,
            MarketExpressionType.MONEYLINE.value,
        )
        
        # Layer 4: Event Context
        context = CanonicalEventContext(
            context_id="",
            instrument_id=instrument.instrument_id,
            event_name=f"{away_team} @ {home_team}",
            event_date=start_time,
            location=venue,
            participants=[home_team, away_team],
            league=league,
        )
        context.context_id = CanonicalEventContext.compute_id(
            instrument.instrument_id,
            context.event_date,
            context.location,
        )
        
        # Layer 5: Provider Listing
        home_odds = game_obj.get("home_moneyline", -110)
        home_price = self._american_to_decimal(home_odds)
        
        listing = CanonicalProviderListing(
            listing_id=f"{game_id}_moneyline",
            provider_name="espn",
            market_expr_id=expr.market_expr_id,
            outcome_id=outcome.outcome_id,
            instrument_id=instrument.instrument_id,
            context_id=context.context_id,
            price=home_price,
            price_format="decimal",
            implied_probability=self._american_to_probability(home_odds),
            raw_api_object=game_obj,
        )
        
        return instrument, outcome, expr, context, listing
        
        # Layer 2: Outcome (HOME or AWAY)
        outcome = CanonicalOutcome(
            outcome_id="",
            instrument_id=instrument.instrument_id,
            outcome_type=OutcomeResolution.BINARY_INVERSE,  # Can be 2-way or 3-way with ties
            states=[
                CanonicalOutcomeState(state_id="HOME", display_name=home_team, resolves_to=True),
                CanonicalOutcomeState(state_id="AWAY", display_name=away_team, resolves_to=False),
            ],
        )
        outcome.outcome_id = CanonicalOutcome.compute_id(
            instrument.instrument_id,
            OutcomeResolution.BINARY_INVERSE.value,
        )
        
        # Layer 3: Market Expression (ESPN Moneyline)
        expr = CanonicalMarketExpression(
            market_expr_id="",
            outcome_id=outcome.outcome_id,
            expression_type=MarketExpressionType.MONEYLINE,
        )
        expr.market_expr_id = CanonicalMarketExpression.compute_id(
            outcome.outcome_id,
            MarketExpressionType.MONEYLINE.value,
        )
        
        # Layer 4: Event Context
        context = CanonicalEventContext(
            context_id="",
            instrument_id=instrument.instrument_id,
            event_name=f"{away_team} @ {home_team}",
            event_date=start_time,
            location=venue,
            participants=[home_team, away_team],
            league=league,
        )
        context.context_id = CanonicalEventContext.compute_id(
            instrument.instrument_id,
            context.event_date,
            context.location,
        )
        
        # Layer 5: Provider Listing
        home_odds = game_obj.get("home_moneyline", -110)
        home_price = self._american_to_decimal(home_odds)
        
        listing = CanonicalProviderListing(
            listing_id=f"{game_id}_moneyline",
            provider_name="espn",
            market_expr_id=expr.market_expr_id,
            outcome_id=outcome.outcome_id,
            instrument_id=instrument.instrument_id,
            context_id=context.context_id,
            price=home_price,
            price_format="decimal",
            implied_probability=self._american_to_probability(home_odds),
            raw_api_object=game_obj,
        )
        
        return instrument, outcome, expr, context, listing
    
    def _american_to_decimal(self, american_odds: float) -> float:
        """Convert American odds to decimal odds."""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    def _american_to_probability(self, american_odds: float) -> float:
        """Convert American odds to implied probability."""
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)
