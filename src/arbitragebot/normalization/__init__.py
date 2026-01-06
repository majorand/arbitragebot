"""Normalization and arbitrage detection layer.

This module provides a complete pipeline for:
1. Normalizing odds from different providers (Kalshi, Polymarket, ESPN)
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
        KalshiNormalizer, PolymarketNormalizer, FanaticsNormalizer, ESPNNormalizer
    )
    from arbitragebot.normalization.event_matching import (
        EventMatcher, MatchedEventSet
    )
    from arbitragebot.normalization.arbitrage_detector import (
        MarketMatcher, ArbitrageDetector
    )
except ImportError:
    # Allow imports to fail for 5-layer system files
    pass

__all__ = [
    # Schemas
    "Sport", "MarketType", "OutcomeType",
    "CanonicalEvent", "CanonicalMarket", "CanonicalOutcome",
    "DetectedArbitrage", "ArbitrageOpportunitySingle",
    
    # Normalizers
    "KalshiNormalizer", "PolymarketNormalizer", "FanaticsNormalizer", "ESPNNormalizer",
    
    # Matching & Detection
    "EventMatcher", "MatchedEventSet",
    "MarketMatcher", "ArbitrageDetector",
]
