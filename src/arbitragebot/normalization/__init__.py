"""Normalization and arbitrage detection layer.

This module provides a complete pipeline for:
1. Normalizing odds from different providers (Kalshi, Polymarket)
2. Matching equivalent events across providers
3. Matching equivalent markets within events
4. Detecting arbitrage opportunities with precise math
"""

try:
    from arbitragebot.normalization.schemas import (
        Sport, MarketType, OutcomeType,
        CanonicalEvent, CanonicalMarket, CanonicalOutcome,
        DetectedArbitrage, ArbitrageOpportunitySingle
    )
    from arbitragebot.normalization.normalizers import (
        KalshiNormalizer, PolymarketNormalizer
    )
    from arbitragebot.normalization.event_matching import (
        EventMatcher, MatchedEventSet
    )
    from arbitragebot.normalization.arbitrage_detector import (
        MarketMatcher, ArbitrageDetector
    )
    from arbitragebot.normalization.canonical_layers import (
        CanonicalInstrument, CanonicalOutcome, CanonicalMarketExpression,
        CanonicalEventContext, CanonicalProviderListing, AggregatedInstrumentView,
        InstrumentDomain, OutcomeResolution, MarketExpressionType, normalize_category
    )
    from arbitragebot.normalization.layer_aggregator import LayerAggregator
    from arbitragebot.normalization.providers import ProviderRegistry, aggregate_all_providers
    from arbitragebot.normalization.layer_arbitrage import LayerArbitrageDetector, LayerArbitrageOpportunity
except ImportError:
    # Allow imports to fail for 5-layer system files
    pass

__all__ = [
    # Schemas
    "Sport", "MarketType", "OutcomeType",
    "CanonicalEvent", "CanonicalMarket", "CanonicalOutcome",
    "DetectedArbitrage", "ArbitrageOpportunitySingle",
    
    # 5-Layer Schemas
    "CanonicalInstrument", "CanonicalOutcome", "CanonicalMarketExpression",
    "CanonicalEventContext", "CanonicalProviderListing", "AggregatedInstrumentView",
    "InstrumentDomain", "OutcomeResolution", "MarketExpressionType",

    # Normalizers
    "KalshiNormalizer", "PolymarketNormalizer",
    "normalize_category",
    
    # Matching & Detection
    "EventMatcher", "MatchedEventSet",
    "MarketMatcher", "ArbitrageDetector",

    # 5-Layer Aggregation
    "LayerAggregator", "ProviderRegistry", "aggregate_all_providers",
    "LayerArbitrageDetector", "LayerArbitrageOpportunity",
]
