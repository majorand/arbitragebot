"""
Arbitrage detection for the 5-layer canonical model.
Works with AggregatedInstrumentView objects.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from .canonical_layers import AggregatedInstrumentView, CanonicalProviderListing

@dataclass
class LayerArbitrageOpportunity:
    """Arbitrage opportunity detected at the Instrument layer."""
    instrument_id: str
    subject: str
    predicate: str
    event_name: str
    domain: str
    start_time: Optional[datetime]

    # Best prices per outcome state
    # {state_id: (provider, listing)}
    best_prices: Dict[str, Tuple[str, CanonicalProviderListing]]

    # Metrics
    implied_probability_sum: float
    edge_pct: float
    roi_pct: float
    confidence_score: float
    providers: List[str]

    detected_at: datetime = field(default_factory=datetime.utcnow)

class LayerArbitrageDetector:
    """Detects arbitrage across AggregatedInstrumentViews."""

    def __init__(self, min_edge_pct: float = 0.5, fee_buffer: float = 0.005):
        self.min_edge_pct = min_edge_pct
        self.fee_buffer = fee_buffer

    def detect(self, views: List[AggregatedInstrumentView]) -> List[LayerArbitrageOpportunity]:
        """Detect opportunities in a list of aggregated views."""
        opportunities = []

        for view in views:
            opp = self._check_view(view)
            if opp:
                opportunities.append(opp)

        # Sort by ROI descending
        opportunities.sort(key=lambda x: x.roi_pct, reverse=True)
        return opportunities

    def _check_view(self, view: AggregatedInstrumentView) -> Optional[LayerArbitrageOpportunity]:
        """Check a single aggregated view for arbitrage."""
        # Need at least 2 providers
        if len(view.providers) < 2:
            return None

        # Need prices for at least 2 outcome states for binary/ternary
        if len(view.prices_by_state) < 2:
            return None

        # For each state, find the best (lowest implied prob) price
        best_prices = {}
        total_implied_prob = 0.0

        for state_id, provider_listings in view.prices_by_state.items():
            if not provider_listings:
                continue

            # Find provider with lowest implied probability for this state
            best_provider = min(provider_listings.items(), key=lambda x: x[1].implied_probability)
            best_prices[state_id] = (best_provider[0], best_provider[1])
            total_implied_prob += best_provider[1].implied_probability

        if not best_prices or len(best_prices) < 2:
            return None

        # Arbitrage check: total implied prob < 1.0
        # Account for fee buffer
        if total_implied_prob >= (1.0 - self.fee_buffer):
            return None

        edge = 1.0 - total_implied_prob
        edge_pct = edge * 100

        if edge_pct < self.min_edge_pct:
            return None

        # Calculate ROI: (1 / sum_prob) - 1
        roi = (1.0 / total_implied_prob) - 1.0
        roi_pct = roi * 100

        return LayerArbitrageOpportunity(
            instrument_id=view.instrument.instrument_id,
            subject=view.instrument.subject,
            predicate=view.instrument.predicate,
            event_name=view.context.event_name if view.context else view.instrument.description,
            domain=view.instrument.domain.value if hasattr(view.instrument.domain, 'value') else str(view.instrument.domain),
            start_time=view.context.event_date if view.context else None,
            best_prices=best_prices,
            implied_probability_sum=total_implied_prob,
            edge_pct=edge_pct,
            roi_pct=roi_pct,
            confidence_score=view.confidence_score,
            providers=view.providers
        )
