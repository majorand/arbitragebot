"""
Multi-layer aggregator: Groups events by Instrument+Outcome across providers.

This aggregator works backwards from provider APIs:

Provider API Objects
    ↓ (Normalize into 5 layers)
Provider Listings (Layer 5)
    ↓ (Map through)
Market Expressions (Layer 3) → Outcomes (Layer 2) → Instruments (Layer 1)
    ↓ (Aggregate by Layer 1+2)
AggregatedInstrumentViews
    ↓ (Score confidence using Layer 4)
Ready for arbitrage detection
"""

import hashlib
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .canonical_layers import (
    CanonicalInstrument,
    CanonicalOutcome,
    CanonicalOutcomeState,
    CanonicalMarketExpression,
    CanonicalEventContext,
    CanonicalProviderListing,
    AggregatedInstrumentView,
)


class LayerAggregator:
    """Aggregates across all 5 layers with provider-agnostic matching."""
    
    def __init__(self):
        """Initialize aggregation state."""
        self.instruments: Dict[str, CanonicalInstrument] = {}
        self.outcomes: Dict[str, CanonicalOutcome] = {}
        self.market_expressions: Dict[str, CanonicalMarketExpression] = {}
        self.contexts: Dict[str, CanonicalEventContext] = {}
        self.listings: List[CanonicalProviderListing] = []
        
        # Aggregation index: instrument_id → outcome_id → AggregatedInstrumentView
        self.aggregated: Dict[str, Dict[str, AggregatedInstrumentView]] = defaultdict(dict)
    
    def register_instrument(self, instrument: CanonicalInstrument):
        """Register Layer 1."""
        self.instruments[instrument.instrument_id] = instrument
    
    def register_outcome(self, outcome: CanonicalOutcome):
        """Register Layer 2."""
        self.outcomes[outcome.outcome_id] = outcome
    
    def register_market_expression(self, expr: CanonicalMarketExpression):
        """Register Layer 3."""
        self.market_expressions[expr.market_expr_id] = expr
    
    def register_context(self, context: CanonicalEventContext):
        """Register Layer 4."""
        self.contexts[context.context_id] = context
    
    def register_listing(self, listing: CanonicalProviderListing):
        """Register Layer 5 and trigger aggregation."""
        self.listings.append(listing)
        self._aggregate_listing(listing)
    
    def _aggregate_listing(self, listing: CanonicalProviderListing):
        """
        Aggregate a single provider listing into the view.
        
        This is where the magic happens: listing knows which
        Instrument (Layer 1) and Outcome (Layer 2) it represents,
        so we group by those — ignoring Event (Layer 4) differences.
        """
        instrument_id = listing.instrument_id
        outcome_id = listing.outcome_id
        
        # Get or create aggregated view for this Instrument+Outcome pair
        if outcome_id not in self.aggregated[instrument_id]:
            instrument = self.instruments.get(instrument_id)
            outcome = self.outcomes.get(outcome_id)
            context = self.contexts.get(listing.context_id) if listing.context_id else None
            
            self.aggregated[instrument_id][outcome_id] = AggregatedInstrumentView(
                instrument=instrument,
                outcome=outcome,
                context=context,
            )
        
        view = self.aggregated[instrument_id][outcome_id]
        
        # Extract outcome state from the market expression
        # (In real impl, this comes from the mapping layer)
        # For now, we infer it from the listing structure
        state_id = self._infer_state_id(listing)
        
        # Group prices by outcome state and provider
        if state_id not in view.prices_by_state:
            view.prices_by_state[state_id] = {}
        
        view.prices_by_state[state_id][listing.provider_name] = listing
        
        # Track providers
        if listing.provider_name not in view.providers:
            view.providers.append(listing.provider_name)
    
    def _infer_state_id(self, listing: CanonicalProviderListing) -> str:
        """
        Extract the outcome state from a listing.
        
        In a full implementation, this would use the market expression mapping.
        For now, we use the outcome object.
        """
        outcome = self.outcomes.get(listing.outcome_id)
        if outcome and outcome.states:
            # Take first state as example
            return outcome.states[0].state_id
        return "unknown"
    
    def finalize(self) -> Dict[str, AggregatedInstrumentView]:
        """
        Finalize aggregation and compute confidence scores.
        
        Returns dict of {instrument_outcome_key: AggregatedInstrumentView}
        """
        result = {}
        
        for instrument_id, outcome_views in self.aggregated.items():
            for outcome_id, view in outcome_views.items():
                # Compute confidence score (0-1)
                # Based on: provider count, outcome state count, event context match
                view.confidence_score = self._compute_confidence(view)
                view.outcome_count = len(view.prices_by_state)
                view.max_providers = len(self.instruments[instrument_id].description.split(","))
                
                # Create unique key
                key = f"{instrument_id}:{outcome_id}"
                result[key] = view
        
        return result
    
    def _compute_confidence(self, view: AggregatedInstrumentView) -> float:
        """
        Compute confidence that all listings truly resolve to same instrument+outcome.
        
        Factors:
        - Provider count (more = higher)
        - Outcome state match (how many states have 2+ providers)
        - Event context match (date/time/location consistency)
        """
        provider_weight = min(len(view.providers) / 3.0, 1.0)  # Up to 3 providers
        outcome_weight = view.outcome_count / 2.0  # Up to 2 states
        
        # Context weight: check if all contexts are similar
        context_weight = 1.0
        if view.context and len(view.providers) > 1:
            # Would do date/time consistency check here
            # For now, assume consistent if context is present
            context_weight = 0.9
        
        confidence = (provider_weight * 0.5) + (outcome_weight * 0.3) + (context_weight * 0.2)
        return min(confidence, 1.0)
    
    def get_by_instrument(self, instrument_id: str) -> Dict[str, AggregatedInstrumentView]:
        """Get all outcome views for a specific instrument."""
        return self.aggregated.get(instrument_id, {})
    
    def filter_by_confidence(self, min_confidence: float = 0.7) -> Dict[str, AggregatedInstrumentView]:
        """Return only views meeting confidence threshold."""
        result = {}
        for instrument_id, outcome_views in self.aggregated.items():
            for outcome_id, view in outcome_views.items():
                if view.confidence_score >= min_confidence:
                    key = f"{instrument_id}:{outcome_id}"
                    result[key] = view
        return result
    
    def find_arbitrage_candidates(self, min_confidence: float = 0.7) -> List[AggregatedInstrumentView]:
        """
        Find instruments with sufficient price overlap for arbitrage.
        
        Criteria:
        - Confidence >= min_confidence
        - At least 2 outcome states have prices
        - At least 2 different providers
        """
        candidates = []
        
        for instrument_id, outcome_views in self.aggregated.items():
            for outcome_id, view in outcome_views.items():
                if view.confidence_score < min_confidence:
                    continue
                
                if len(view.prices_by_state) < 2:
                    continue
                
                if len(view.providers) < 2:
                    continue
                
                candidates.append(view)
        
        return candidates


# ============================================================================
# Mapping Layer: Provider → 5 Canonical Layers
# ============================================================================

class ProviderToLayersMapper:
    """
    Abstract base: converts provider API objects into all 5 layers.
    
    Subclasses implement per-provider mapping logic.
    """
    
    def map_to_layers(self, provider_obj: dict) -> Tuple[
        CanonicalInstrument,
        CanonicalOutcome,
        CanonicalMarketExpression,
        CanonicalEventContext,
        CanonicalProviderListing,
    ]:
        """
        Map a single provider object through all 5 layers.
        
        Returns: (instrument, outcome, expr, context, listing)
        """
        raise NotImplementedError("Subclasses must implement")


# ============================================================================
# Example: ESPN Mapper
# ============================================================================

class ESPNLayerMapper(ProviderToLayersMapper):
    """Maps ESPN API objects to canonical layers."""
    
    def map_to_layers(self, provider_obj: dict) -> Tuple[
        CanonicalInstrument,
        CanonicalOutcome,
        CanonicalMarketExpression,
        CanonicalEventContext,
        CanonicalProviderListing,
    ]:
        # Extract ESPN fields
        league = provider_obj.get("league", "nba")
        sport_map = {"nfl": "sports", "nba": "sports", "mlb": "sports"}
        domain = sport_map.get(league, "sports")
        
        # Layer 1: Instrument (who wins this game)
        home = provider_obj.get("home_team", "Unknown")
        away = provider_obj.get("away_team", "Unknown")
        instrument = CanonicalInstrument(
            instrument_id="",  # Will be computed
            domain="sports",
            subject=home,
            predicate=f"win_vs_{away}",
        )
        instrument.instrument_id = CanonicalInstrument.compute_id(
            "sports", home, f"win_vs_{away}"
        )
        
        # Layer 2: Outcome (HOME wins or AWAY wins)
        outcome = CanonicalOutcome(
            outcome_id="",
            instrument_id=instrument.instrument_id,
            outcome_type="moneyline",
        )
        outcome.outcome_id = CanonicalOutcome.compute_id(
            instrument.instrument_id, "moneyline"
        )
        outcome.states = [
            CanonicalOutcomeState(state_id="HOME", display_name=home, resolves_to=True),
            CanonicalOutcomeState(state_id="AWAY", display_name=away, resolves_to=False),
        ]
        
        # Layer 3: Market Expression (ESPN Moneyline)
        expr = CanonicalMarketExpression(
            market_expr_id="",
            outcome_id=outcome.outcome_id,
            expression_type="moneyline",
        )
        expr.market_expr_id = CanonicalMarketExpression.compute_id(
            outcome.outcome_id, "moneyline"
        )
        
        # Layer 4: Event Context
        context = CanonicalEventContext(
            context_id="",
            instrument_id=instrument.instrument_id,
            event_name=f"{away} @ {home}",
            event_date=datetime.fromisoformat(provider_obj.get("start_time", "")),
            location=provider_obj.get("venue", ""),
            participants=[home, away],
            league=league,
        )
        context.context_id = CanonicalEventContext.compute_id(
            instrument.instrument_id,
            context.event_date,
            context.location,
        )
        
        # Layer 5: Provider Listing (ESPN's odds)
        listing = CanonicalProviderListing(
            listing_id=provider_obj.get("id", ""),
            provider_name="espn",
            market_expr_id=expr.market_expr_id,
            outcome_id=outcome.outcome_id,
            instrument_id=instrument.instrument_id,
            context_id=context.context_id,
            price=provider_obj.get("moneyline", 0.0),
            price_format="american",
            implied_probability=provider_obj.get("implied_prob", 0.5),
            raw_api_object=provider_obj,
        )
        
        return instrument, outcome, expr, context, listing


# ============================================================================
# Example aggregation flow
# ============================================================================

def aggregate_multi_provider_events(
    provider_data: Dict[str, List[dict]]
) -> Dict[str, AggregatedInstrumentView]:
    """
    Main aggregation function.
    
    Input: {provider_name: [api_objects]}
    Output: {instrument_outcome_key: AggregatedInstrumentView}
    """
    aggregator = LayerAggregator()
    
    # Mappers per provider
    mappers = {
        "espn": ESPNLayerMapper(),
        # "kalshi": KalshiLayerMapper(),
        # "polymarket": PolymarketLayerMapper(),
    }
    
    # Process each provider's data
    for provider_name, api_objects in provider_data.items():
        if provider_name not in mappers:
            continue
        
        mapper = mappers[provider_name]
        
        for api_obj in api_objects:
            # Map through 5 layers
            instrument, outcome, expr, context, listing = mapper.map_to_layers(api_obj)
            
            # Register in aggregator
            aggregator.register_instrument(instrument)
            aggregator.register_outcome(outcome)
            aggregator.register_market_expression(expr)
            aggregator.register_context(context)
            aggregator.register_listing(listing)
    
    # Finalize and return
    return aggregator.finalize()
