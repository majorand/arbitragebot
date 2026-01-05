"""Example usage of the normalization and arbitrage detection pipeline.

This demonstrates the complete workflow:
1. Normalize raw API responses from each provider
2. Match events across providers
3. Match markets within events
4. Detect arbitrage opportunities
"""

from datetime import datetime, timedelta
from typing import Dict, List

from arbitragebot.normalization import (
    KalshiNormalizer, PolymarketNormalizer, ESPNNormalizer,
    EventMatcher, MarketMatcher, ArbitrageDetector,
    CanonicalEvent, DetectedArbitrage
)


def normalize_all_providers(
    kalshi_markets: List[Dict],
    polymarket_markets: List[Dict],
    espn_competitions: List[Dict],
    espn_sport: str = "nfl"
) -> Dict[str, List[CanonicalEvent]]:
    """Normalize raw API responses from all providers.
    
    Args:
        kalshi_markets: Raw markets from Kalshi API
        polymarket_markets: Raw markets from Polymarket API
        espn_competitions: Raw competitions from ESPN API
        espn_sport: Sport type for ESPN data
        
    Returns:
        Dict mapping provider name → normalized CanonicalEvent objects
    """
    events_by_provider = {}
    
    # Normalize Kalshi
    kalshi_normalizer = KalshiNormalizer()
    kalshi_events = [
        kalshi_normalizer.normalize_market(m)
        for m in kalshi_markets
    ]
    events_by_provider["kalshi"] = [e for e in kalshi_events if e is not None]
    
    # Normalize Polymarket
    polymarket_normalizer = PolymarketNormalizer()
    polymarket_events = [
        polymarket_normalizer.normalize_market(m)
        for m in polymarket_markets
    ]
    events_by_provider["polymarket"] = [e for e in polymarket_events if e is not None]
    
    # Normalize ESPN
    espn_normalizer = ESPNNormalizer()
    from arbitragebot.normalization import Sport
    sport_enum = Sport[espn_sport.upper()] if espn_sport.upper() in Sport.__members__ else Sport.OTHER
    
    espn_events = [
        espn_normalizer.normalize_competition(c, sport_enum)
        for c in espn_competitions
    ]
    events_by_provider["espn"] = [e for e in espn_events if e is not None]
    
    return events_by_provider


def find_arbitrage_opportunities(
    events_by_provider: Dict[str, List[CanonicalEvent]],
    min_edge_pct: float = 0.5,
    fee_bps: int = 25
) -> List[DetectedArbitrage]:
    """Complete pipeline: match events, match markets, detect arbitrage.
    
    Args:
        events_by_provider: Output from normalize_all_providers()
        min_edge_pct: Minimum edge % to report (default 0.5%)
        fee_bps: Exchange fee in basis points (default 25 bps)
        
    Returns:
        List of DetectedArbitrage opportunities
    """
    
    # Step 1: Match events across providers
    matcher = EventMatcher()
    matched_event_groups = matcher.match_events(events_by_provider)
    
    all_arbitrage = []
    
    # Step 2-4: For each matched event, find markets and detect arbitrage
    for event_group in matched_event_groups:
        from arbitragebot.normalization import MatchedEventSet
        matched_set = MatchedEventSet(event_group)
        
        # Find matching markets within this event
        market_matcher = MarketMatcher()
        matched_markets = market_matcher.find_matching_markets(matched_set)
        
        if not matched_markets:
            continue
        
        # Detect arbitrage in these markets
        detector = ArbitrageDetector()
        opportunities = detector.detect_arbitrage(
            matched_markets,
            matched_set,
            min_edge_pct=min_edge_pct,
            fee_bps=fee_bps
        )
        
        all_arbitrage.extend(opportunities)
    
    # Sort by ROI descending
    all_arbitrage.sort(key=lambda x: x.roi_percentage, reverse=True)
    
    return all_arbitrage


def print_arbitrage_report(opportunities: List[DetectedArbitrage]):
    """Print formatted arbitrage report."""
    if not opportunities:
        print("No arbitrage opportunities detected.")
        return
    
    print(f"\n{'='*80}")
    print(f"ARBITRAGE OPPORTUNITIES DETECTED: {len(opportunities)}")
    print(f"{'='*80}\n")
    
    for i, arb in enumerate(opportunities, 1):
        print(f"{i}. {arb.event_name}")
        print(f"   Sport: {arb.sport.value}")
        print(f"   Market: {arb.market_type.value}")
        print(f"   Edge: {arb.roi_percentage:.2f}%")
        print(f"   Expected Profit: ${arb.expected_profit:.4f} per $1 stake")
        print(f"   Risk: {arb.execution_risk}")
        print()
        
        print("   Bets:")
        for leg in arb.legs:
            print(f"     - {leg.provider.upper()}: {leg.outcome.title}")
            print(f"       Stake: ${leg.stake:.4f}")
            print(f"       Probability: {leg.outcome.implied_probability:.1%}")
        print()


if __name__ == "__main__":
    # Example: Mock data (in real usage, fetch from APIs)
    kalshi_mock = [
        {
            "id": "kxnflgame_26jan04detchi",
            "ticker": "KXNFLGAME-26JAN04DETCHI",
            "title": "Will Detroit beat Chicago?",
            "yes_bid": 62,  # 62 cents = 62%
            "no_bid": 38,
            "category": "sports",
            "expiration_time": datetime.now().isoformat(),
        }
    ]
    
    polymarket_mock = [
        {
            "question_id": "0x12345",
            "question": "DET @ CHI: Will Detroit win?",
            "tokens": [
                {"outcome": "YES", "price": 0.61, "id": "token1"},
                {"outcome": "NO", "price": 0.39, "id": "token2"},
            ],
            "end_date_iso": datetime.now().isoformat() + "Z",
            "tags": ["nfl"],
        }
    ]
    
    espn_mock = [
        {
            "id": "espn_det_chi_123",
            "competitors": [
                {"team": {"name": "Detroit Lions", "abbreviation": "DET"}},
                {"team": {"name": "Chicago Bears", "abbreviation": "CHI"}},
            ],
            "startDate": datetime.now().isoformat() + "Z",
            "odds": [
                {
                    "homeTeamOdds": {"value": 1.61},  # Decimal: 61% implied
                    "awayTeamOdds": {"value": 2.44},  # Decimal: 41% implied
                }
            ]
        }
    ]
    
    # Run pipeline
    print("Normalizing provider data...")
    events = normalize_all_providers(kalshi_mock, polymarket_mock, espn_mock, "nfl")
    
    print(f"  Kalshi: {len(events['kalshi'])} events")
    print(f"  Polymarket: {len(events['polymarket'])} events")
    print(f"  ESPN: {len(events['espn'])} events")
    
    print("\nFinding arbitrage opportunities...")
    opportunities = find_arbitrage_opportunities(events, min_edge_pct=0.1)
    
    print_arbitrage_report(opportunities)
