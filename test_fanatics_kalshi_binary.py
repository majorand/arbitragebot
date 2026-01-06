#!/usr/bin/env python3
"""
Test script to verify Fanatics binary moneyline markets are being properly
captured and can be compared with Kalshi YES/NO markets for arbitrage.

This demonstrates the binary data flow:
  Fanatics (Home Win 1.85 / Away Win 2.05)
       ↓
  FanaticsNormalizer
       ↓
  Canonical YES/NO format (YES=0.54 / NO=0.49)
       ↓
  Cross-provider arbitrage matching
       ↓
  Kalshi binary market (Kalshi YES 0.52 / NO 0.51)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from arbitragebot.normalization.normalizers import FanaticsNormalizer, KalshiNormalizer
from arbitragebot.normalization.schemas import MarketType, OutcomeType

# Mock Fanatics raw market data (moneyline - binary)
fanatics_market = {
    "event_id": "nfl_game_123",
    "id": "nfl_game_123",
    "name": "Buffalo Bills vs Kansas City Chiefs",
    "title": "Buffalo Bills vs Kansas City Chiefs",
    "sport": "football",
    "league": "nfl",
    "event_datetime": "2026-01-10T20:00:00Z",
    "start_time": "2026-01-10T20:00:00Z",
    "competitors": [
        {"name": "Buffalo Bills", "team_name": "Buffalo Bills"},
        {"name": "Kansas City Chiefs", "team_name": "Kansas City Chiefs"}
    ],
    "markets": [
        {
            "market_type": "moneyline",
            "type": "moneyline",
            "selections": [
                {
                    "name": "Buffalo Bills",
                    "label": "Buffalo Bills",
                    "outcome_id": "buf_ml",
                    "decimal_odds": 1.85,
                    "odds": 1.85
                },
                {
                    "name": "Kansas City Chiefs",
                    "label": "Kansas City Chiefs",
                    "outcome_id": "kc_ml",
                    "decimal_odds": 2.05,
                    "odds": 2.05
                }
            ],
            "outcomes": [
                {
                    "name": "Buffalo Bills",
                    "label": "Buffalo Bills",
                    "outcome_id": "buf_ml",
                    "decimal_odds": 1.85,
                    "odds": 1.85
                },
                {
                    "name": "Kansas City Chiefs",
                    "label": "Kansas City Chiefs",
                    "outcome_id": "kc_ml",
                    "decimal_odds": 2.05,
                    "odds": 2.05
                }
            ]
        }
    ],
    "odds": [
        {
            "market_type": "moneyline",
            "type": "moneyline",
            "selections": [
                {
                    "name": "Buffalo Bills",
                    "label": "Buffalo Bills",
                    "outcome_id": "buf_ml",
                    "decimal_odds": 1.85,
                    "odds": 1.85
                },
                {
                    "name": "Kansas City Chiefs",
                    "label": "Kansas City Chiefs",
                    "outcome_id": "kc_ml",
                    "decimal_odds": 2.05,
                    "odds": 2.05
                }
            ]
        }
    ]
}

# Mock Kalshi binary market (YES/NO)
kalshi_market = {
    "id": "will_bills_beat_chiefs",
    "ticker": "will_bills_beat_chiefs",
    "title": "Will Buffalo Bills beat Kansas City Chiefs?",
    "category": "sports",
    "expiration_time": "2026-01-10T20:00:00",
    "yes_bid": 52,  # 52 cents = 52% implied probability
    "no_bid": 51,   # 51 cents = 49% implied probability (should sum to ~100%)
}

def test_fanatics_normalization():
    """Test that Fanatics moneyline markets are normalized to binary YES/NO."""
    print("=" * 70)
    print("FANATICS BINARY NORMALIZATION TEST")
    print("=" * 70)
    
    normalizer = FanaticsNormalizer()
    canonical_event = normalizer.normalize_market(fanatics_market)
    
    if not canonical_event:
        print("❌ FAILED: FanaticsNormalizer returned None")
        return False
    
    print(f"✅ FanaticsNormalizer successfully created canonical event")
    print(f"   Event ID (placeholder): '{canonical_event.event_id}'")
    print(f"   Sport: {canonical_event.sport}")
    print(f"   League: {canonical_event.league}")
    print(f"   Home Team: {canonical_event.home_team}")
    print(f"   Away Team: {canonical_event.away_team}")
    print(f"   Event Name: {canonical_event.event_name}")
    print(f"   Provider Event IDs: {canonical_event.provider_event_ids}")
    
    # Check markets
    if not canonical_event.markets:
        print("❌ FAILED: No markets in canonical event")
        return False
    
    print(f"\n✅ Markets captured: {len(canonical_event.markets)}")
    
    for i, market in enumerate(canonical_event.markets):
        print(f"\n   Market {i}:")
        print(f"   - Type: {market.market_type}")
        print(f"   - Outcomes: {len(market.outcomes)}")
        
        if market.market_type != MarketType.YES_NO:
            print(f"   ❌ FAILED: Expected MarketType.YES_NO, got {market.market_type}")
            return False
        
        for outcome in market.outcomes:
            print(f"     - {outcome.outcome_type}: {outcome.title}")
            print(f"       Probability: {outcome.implied_probability:.2%}")
            print(f"       Price: {outcome.price:.4f}")
            print(f"       Provider ID: {outcome.provider_outcome_id}")
        
        # Verify we have both YES and NO
        outcome_types = {o.outcome_type for o in market.outcomes}
        if OutcomeType.YES not in outcome_types or OutcomeType.NO not in outcome_types:
            print(f"   ❌ FAILED: Missing YES or NO outcome")
            return False
    
    print("\n✅ Fanatics binary market properly normalized to YES/NO")
    return True


def test_kalshi_normalization():
    """Test that Kalshi markets maintain binary YES/NO structure."""
    print("\n" + "=" * 70)
    print("KALSHI BINARY NORMALIZATION TEST")
    print("=" * 70)
    
    normalizer = KalshiNormalizer()
    canonical_event = normalizer.normalize_market(kalshi_market)
    
    if not canonical_event:
        print("❌ FAILED: KalshiNormalizer returned None")
        return False
    
    print(f"✅ KalshiNormalizer successfully created canonical event")
    print(f"   Event ID (placeholder): '{canonical_event.event_id}'")
    print(f"   Sport: {canonical_event.sport}")
    print(f"   League: {canonical_event.league}")
    print(f"   Event Name: {canonical_event.event_name}")
    print(f"   Provider Event IDs: {canonical_event.provider_event_ids}")
    
    # Check markets
    if not canonical_event.markets:
        print("❌ FAILED: No markets in canonical event")
        return False
    
    print(f"\n✅ Markets captured: {len(canonical_event.markets)}")
    
    for i, market in enumerate(canonical_event.markets):
        print(f"\n   Market {i}:")
        print(f"   - Type: {market.market_type}")
        print(f"   - Outcomes: {len(market.outcomes)}")
        
        if market.market_type != MarketType.YES_NO:
            print(f"   ❌ FAILED: Expected MarketType.YES_NO, got {market.market_type}")
            return False
        
        for outcome in market.outcomes:
            print(f"     - {outcome.outcome_type}: {outcome.title}")
            print(f"       Probability: {outcome.implied_probability:.2%}")
            print(f"       Price: {outcome.price}")
            print(f"       Provider ID: {outcome.provider_outcome_id}")
        
        # Verify we have both YES and NO
        outcome_types = {o.outcome_type for o in market.outcomes}
        if OutcomeType.YES not in outcome_types or OutcomeType.NO not in outcome_types:
            print(f"   ❌ FAILED: Missing YES or NO outcome")
            return False
    
    print("\n✅ Kalshi binary market properly maintains YES/NO")
    return True


def test_cross_provider_comparison():
    """Test that Fanatics and Kalshi markets can be compared for arbitrage."""
    print("\n" + "=" * 70)
    print("CROSS-PROVIDER BINARY COMPARISON TEST")
    print("=" * 70)
    
    # Normalize both
    fanatics_norm = FanaticsNormalizer()
    kalshi_norm = KalshiNormalizer()
    
    fanatics_event = fanatics_norm.normalize_market(fanatics_market)
    kalshi_event = kalshi_norm.normalize_market(kalshi_market)
    
    if not fanatics_event or not fanatics_event.markets:
        print("❌ FAILED: Could not normalize Fanatics market")
        return False
    
    if not kalshi_event or not kalshi_event.markets:
        print("❌ FAILED: Could not normalize Kalshi market")
        return False
    
    print(f"✅ Both events normalized successfully")
    
    # Get market outcomes
    fanatics_mkt = fanatics_event.markets[0]
    kalshi_mkt = kalshi_event.markets[0]
    
    print(f"\nFanatics outcomes:")
    for outcome in fanatics_mkt.outcomes:
        print(f"  {outcome.outcome_type}: {outcome.implied_probability:.2%}")
    
    print(f"\nKalshi outcomes:")
    for outcome in kalshi_mkt.outcomes:
        print(f"  {outcome.outcome_type}: {outcome.implied_probability:.2%}")
    
    # Calculate if arbitrage exists
    fanatics_yes = next((o for o in fanatics_mkt.outcomes if o.outcome_type == OutcomeType.YES), None)
    fanatics_no = next((o for o in fanatics_mkt.outcomes if o.outcome_type == OutcomeType.NO), None)
    kalshi_yes = next((o for o in kalshi_mkt.outcomes if o.outcome_type == OutcomeType.YES), None)
    kalshi_no = next((o for o in kalshi_mkt.outcomes if o.outcome_type == OutcomeType.NO), None)
    
    if not (fanatics_yes and fanatics_no and kalshi_yes and kalshi_no):
        print("❌ FAILED: Missing outcomes for arbitrage comparison")
        return False
    
    # Simple arbitrage check: YES at best price + NO at best price < 1.0
    best_yes_price = min(fanatics_yes.implied_probability, kalshi_yes.implied_probability)
    best_no_price = min(fanatics_no.implied_probability, kalshi_no.implied_probability)
    arbitrage_margin = 1.0 - (best_yes_price + best_no_price)
    
    print(f"\n📊 Arbitrage Analysis:")
    print(f"   Best YES price (min of both providers): {best_yes_price:.2%}")
    print(f"   Best NO price (min of both providers): {best_no_price:.2%}")
    print(f"   Implied margin: {(best_yes_price + best_no_price):.2%}")
    print(f"   Arbitrage opportunity: {arbitrage_margin:.2%}")
    
    if arbitrage_margin > 0.01:
        print(f"   ✅ ARBITRAGE DETECTED: {arbitrage_margin:.2%} margin available!")
    else:
        print(f"   ℹ️  No arbitrage (tight pricing or negative margin)")
    
    print(f"\n✅ Cross-provider binary comparison successful")
    return True


if __name__ == "__main__":
    print("\n" + "🔍 FANATICS-KALSHI BINARY ARBITRAGE TEST SUITE".center(70) + "\n")
    
    results = []
    results.append(("Fanatics Normalization", test_fanatics_normalization()))
    results.append(("Kalshi Normalization", test_kalshi_normalization()))
    results.append(("Cross-Provider Comparison", test_cross_provider_comparison()))
    
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(p for _, p in results)
    print("=" * 70)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED - Binary data flowing correctly for arbitrage!")
        sys.exit(0)
    else:
        print("\n⚠️  SOME TESTS FAILED - Review output above")
        sys.exit(1)
