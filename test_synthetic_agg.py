#!/usr/bin/env python3
"""
Test aggregation pipeline with synthetic cross-provider events.
This verifies that the aggregation works correctly.
"""

from datetime import datetime
from arbitragebot.normalization.schemas import (
    CanonicalEvent, CanonicalMarket, CanonicalOutcome,
    Sport, MarketType, OutcomeType
)
from arbitragebot.normalization.aggregator import (
    canonical_event_id, canonical_market_key, aggregate_events, validate_aggregation
)

print("\n" + "="*60)
print("SYNTHETIC CROSS-PROVIDER AGGREGATION TEST")
print("="*60)

# Create synthetic events that should match
now = datetime(2026, 1, 4, 19, 0)

# Provider 1: ESPN-like moneyline
espn_event = CanonicalEvent(
    event_id="",  # Placeholder
    sport=Sport.NBA,
    league="NBA",
    home_team="Cleveland Cavaliers",
    away_team="Detroit Pistons",
    start_time=now,
    provider_event_ids={"espn": "espn_123"}
)

espn_moneyline = CanonicalMarket(
    market_id="",
    market_type=MarketType.MONEYLINE,
    outcomes=[
        CanonicalOutcome(
            outcome_type=OutcomeType.HOME,
            title="Cavaliers",
            implied_probability=0.65,
            price=1.54,
            provider_outcome_id="home"
        ),
        CanonicalOutcome(
            outcome_type=OutcomeType.AWAY,
            title="Pistons",
            implied_probability=0.35,
            price=2.40,
            provider_outcome_id="away"
        )
    ]
)
espn_event.markets.append(espn_moneyline)

# Provider 2: Polymarket YES/NO (same event, different perspective)
poly_event = CanonicalEvent(
    event_id="",  # Placeholder
    sport=Sport.NBA,
    league="Polymarket",
    home_team="Cleveland Cavaliers",
    away_team="Detroit Pistons",
    start_time=now,
    provider_event_ids={"polymarket": "poly_456"}
)

poly_moneyline = CanonicalMarket(
    market_id="",
    market_type=MarketType.MONEYLINE,
    outcomes=[
        CanonicalOutcome(
            outcome_type=OutcomeType.HOME,
            title="Cavaliers Win",
            implied_probability=0.62,
            price=0.62,
            provider_outcome_id="yes"
        ),
        CanonicalOutcome(
            outcome_type=OutcomeType.AWAY,
            title="Pistons Win",
            implied_probability=0.38,
            price=0.38,
            provider_outcome_id="no"
        )
    ]
)
poly_event.markets.append(poly_moneyline)

# Aggregate
events_by_provider = {
    "espn": [espn_event],
    "polymarket": [poly_event]
}

print("\n[1] Input events:")
print(f"  ESPN: {espn_event.home_team} @ {espn_event.away_team}")
print(f"  Polymarket: {poly_event.home_team} @ {poly_event.away_team}")

print("\n[2] Computing canonical IDs...")
espn_id = canonical_event_id(
    espn_event.sport,
    [espn_event.home_team, espn_event.away_team],
    espn_event.start_time
)
poly_id = canonical_event_id(
    poly_event.sport,
    [poly_event.home_team, poly_event.away_team],
    poly_event.start_time
)

print(f"  ESPN canonical ID: {espn_id[:16]}...")
print(f"  Polymarket canonical ID: {poly_id[:16]}...")
print(f"  Match: {espn_id == poly_id}")

print("\n[3] Aggregating events...")
aggregated = aggregate_events(events_by_provider)

print(f"  Result: {len(aggregated)} aggregated events")

print("\n[4] Validating aggregation...")
stats = validate_aggregation(aggregated)

print(f"  Total events: {stats['total_events']}")
print(f"  Cross-provider: {stats['cross_provider_events']}")
print(f"  Single-provider: {stats['single_provider_events']}")

if stats['cross_provider_events'] > 0:
    print(f"\n✓ SUCCESS: Cross-provider event aggregation working!")
    
    # Show the aggregated event
    for event_id, event_data in aggregated.items():
        if len(event_data['providers']) > 1:
            print(f"\n[5] Aggregated Event Structure:")
            print(f"  Event ID: {event_id[:16]}...")
            print(f"  Providers: {event_data['providers']}")
            print(f"  Teams: {event_data['home_team']} @ {event_data['away_team']}")
            
            for market_key, market_data in event_data['markets'].items():
                print(f"\n  Market: {market_key}")
                for outcome, providers in market_data['outcomes'].items():
                    print(f"    {outcome}:")
                    for provider, info in providers.items():
                        print(f"      {provider}: {info['price']:.4f} (prob: {info['implied_probability']:.2%})")
            
            print(f"\n  This is what arbitrage detector would see!")
            print(f"  It can now compare prices across {event_data['providers']}")
else:
    print(f"\n✗ FAILED: Events did not aggregate together!")
    print(f"  Check that team names, sport, and time match")

print("\n" + "="*60)
