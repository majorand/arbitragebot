"""
Event aggregator - builds canonical events with cross-provider aggregation.

This module MUST run AFTER normalization but BEFORE arbitrage detection.
It enforces proper hierarchies:

CanonicalEvent
  ├── provider_events {provider: ProviderEvent}
  ├── canonical_markets {market_key: CanonicalMarket}
  │   └── outcomes {outcome_type: {provider: price}}
  └── metadata (sport, participants, start_time)
"""

import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from arbitragebot.normalization.schemas import (
    CanonicalEvent, CanonicalMarket, CanonicalOutcome, OutcomeType
)
import logging

LOGGER = logging.getLogger(__name__)


def canonical_event_id(sport: str, participants: List[str], start_time: datetime) -> str:
    """
    Generate provider-agnostic event ID from sport + sorted participants + time.
    
    This is the SOURCE OF TRUTH for event identity.
    Same event from different providers will produce identical hash.
    
    Args:
        sport: Sport enum value or string (e.g., "nfl", "nba")
        participants: [home_team, away_team] or similar
        start_time: Event start datetime
    
    Returns:
        Deterministic hex hash (64 chars)
    """
    # Normalize sport to string
    sport_str = sport.value if hasattr(sport, 'value') else str(sport).lower()
    
    # Sort participants to ensure consistent ordering
    sorted_participants = sorted([str(p).lower() for p in participants if p])
    
    # Use ISO format truncated to minute for time matching
    time_str = start_time.isoformat()[:16] if start_time else "unknown"
    
    # Build key: "nfl|away_team|home_team|2026-01-04T14:00"
    key = f"{sport_str}|{'|'.join(sorted_participants)}|{time_str}"
    
    # Return SHA256 hash (deterministic, provider-agnostic)
    event_hash = hashlib.sha256(key.encode()).hexdigest()
    LOGGER.debug(f"Canonical ID for {key} = {event_hash}")
    return event_hash


def canonical_market_key(market_type: str, line: Optional[float] = None) -> str:
    """
    Generate canonical market key for grouping across providers.
    
    Same market type+line from different providers uses same key.
    
    Examples:
        moneyline:  → "moneyline"
        spread:2.5  → "spread:2.5"
        total:45.5  → "total:45.5"
        yes_no:     → "yes_no"
    """
    market_str = market_type.value if hasattr(market_type, 'value') else str(market_type).lower()
    
    if line is not None:
        return f"{market_str}:{line}"
    return market_str


def aggregate_events(events_by_provider: Dict[str, List[CanonicalEvent]]) -> Dict[str, object]:
    """
    Aggregate events from multiple providers into shared canonical events.
    
    Core algorithm:
    1. For each provider's events
    2. Calculate canonical_event_id()
    3. Group by ID → events[id] = {provider: event}
    4. Build outcomes with provider tags
    
    Args:
        events_by_provider: {"kalshi": [...], "polymarket": [...], "espn": [...]}
    
    Returns:
        {canonical_event_id: AggregatedEvent}
        
    Example output:
        {
            "abc123hash": {
                "event_id": "abc123hash",
                "sport": "nfl",
                "home_team": "Kansas City Chiefs",
                "away_team": "Buffalo Bills",
                "start_time": datetime(...),
                "providers": ["kalshi", "polymarket"],
                "provider_events": {
                    "kalshi": CanonicalEvent(...),
                    "polymarket": CanonicalEvent(...)
                },
                "markets": {
                    "yes_no": {
                        "outcomes": {
                            "YES": {"kalshi": 0.62, "polymarket": 0.59},
                            "NO": {"kalshi": 0.41, "polymarket": 0.44}
                        }
                    },
                    "moneyline": {
                        "outcomes": {
                            "HOME": {"espn": 0.54, ...},
                            "AWAY": {...}
                        }
                    }
                }
            }
        }
    """
    aggregated = {}
    
    # Iterate through all providers
    for provider_name, provider_events in events_by_provider.items():
        if not provider_events:
            LOGGER.debug(f"No events from {provider_name}")
            continue
        
        LOGGER.info(f"Aggregating {len(provider_events)} events from {provider_name}")
        
        for provider_event in provider_events:
            # Calculate canonical ID using only event metadata
            event_id = canonical_event_id(
                provider_event.sport,
                [provider_event.home_team, provider_event.away_team],
                provider_event.start_time
            )
            
            # Update provider_event to use canonical ID (was placeholder before)
            provider_event.event_id = event_id
            
            # Create aggregated event if first time seeing this ID
            if event_id not in aggregated:
                aggregated[event_id] = {
                    "event_id": event_id,
                    "sport": provider_event.sport,
                    "home_team": provider_event.home_team,
                    "away_team": provider_event.away_team,
                    "start_time": provider_event.start_time,
                    "providers": [],
                    "provider_events": {},
                    "markets": {}
                }
            
            # Add this provider to the list if not already there
            if provider_name not in aggregated[event_id]["providers"]:
                aggregated[event_id]["providers"].append(provider_name)
            
            # Store the original provider event
            aggregated[event_id]["provider_events"][provider_name] = provider_event
            
            # Aggregate markets with provider tags
            for market in provider_event.markets:
                market_key = canonical_market_key(market.market_type, market.line)
                
                # Update market to use canonical ID (was placeholder before)
                market.market_id = f"{event_id}_{market_key}"
                
                # Create market container if first time
                if market_key not in aggregated[event_id]["markets"]:
                    aggregated[event_id]["markets"][market_key] = {
                        "market_type": market.market_type,
                        "line": market.line,
                        "outcomes": {}
                    }
                
                # Add outcomes with provider tag
                for outcome in market.outcomes:
                    outcome_key = outcome.outcome_type.value if hasattr(outcome.outcome_type, 'value') else str(outcome.outcome_type)
                    
                    if outcome_key not in aggregated[event_id]["markets"][market_key]["outcomes"]:
                        aggregated[event_id]["markets"][market_key]["outcomes"][outcome_key] = {}
                    
                    # Tag with provider
                    aggregated[event_id]["markets"][market_key]["outcomes"][outcome_key][provider_name] = {
                        "price": outcome.price,
                        "implied_probability": outcome.implied_probability,
                        "provider": provider_name
                    }
    
    LOGGER.info(f"Aggregated {len(aggregated)} unique events from {len(events_by_provider)} providers")
    
    # Validation
    for event_id, event_data in aggregated.items():
        if len(event_data["providers"]) > 1:
            LOGGER.info(f"✓ Event {event_id[:8]}... shared by {event_data['providers']}")
        else:
            LOGGER.debug(f"Event {event_id[:8]}... only from {event_data['providers']}")
    
    return aggregated


def find_cross_provider_markets(aggregated_event: Dict) -> List[Dict]:
    """
    Find markets that exist in 2+ providers within an event.
    
    This is the filter for arbitrage detection:
    - If market only exists in 1 provider → no arbitrage possible
    - If market exists in 2+ providers → eligible for arbitrage
    
    Args:
        aggregated_event: Single event from aggregate_events() output
    
    Returns:
        List of markets that have 2+ provider quotes
    """
    cross_provider_markets = []
    
    for market_key, market_data in aggregated_event.get("markets", {}).items():
        for outcome_key, provider_quotes in market_data["outcomes"].items():
            provider_count = len(provider_quotes)
            
            if provider_count >= 2:
                cross_provider_markets.append({
                    "market_key": market_key,
                    "market_type": market_data["market_type"],
                    "line": market_data["line"],
                    "outcome": outcome_key,
                    "provider_quotes": provider_quotes,
                    "provider_count": provider_count
                })
                LOGGER.debug(
                    f"Cross-provider market found: {outcome_key} in {market_key} "
                    f"({provider_count} providers)"
                )
    
    return cross_provider_markets


def validate_aggregation(aggregated_events: Dict[str, Dict]) -> Dict[str, any]:
    """
    Validate aggregation quality and return statistics.
    
    Returns:
        {
            "total_events": int,
            "cross_provider_events": int,
            "single_provider_events": int,
            "avg_providers_per_event": float,
            "max_providers_in_event": int,
        }
    """
    stats = {
        "total_events": len(aggregated_events),
        "cross_provider_events": 0,
        "single_provider_events": 0,
        "provider_counts": [],
        "avg_providers_per_event": 0.0,
        "max_providers_in_event": 0,
    }
    
    for event_id, event_data in aggregated_events.items():
        provider_count = len(event_data["providers"])
        stats["provider_counts"].append(provider_count)
        
        if provider_count >= 2:
            stats["cross_provider_events"] += 1
        else:
            stats["single_provider_events"] += 1
        
        stats["max_providers_in_event"] = max(stats["max_providers_in_event"], provider_count)
    
    if stats["total_events"] > 0:
        stats["avg_providers_per_event"] = sum(stats["provider_counts"]) / stats["total_events"]
    
    LOGGER.info(
        f"Aggregation stats: {stats['total_events']} total, "
        f"{stats['cross_provider_events']} cross-provider, "
        f"{stats['single_provider_events']} single-provider, "
        f"avg {stats['avg_providers_per_event']:.1f} providers/event"
    )
    
    return stats
