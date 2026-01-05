#!/usr/bin/env python3
"""Debug aggregation issues by testing team name normalization."""

import os
import logging
from dotenv import load_dotenv
from arbitragebot.data_sources.kalshi import KalshiDataSource
from arbitragebot.data_sources.polymarket import PolymarketDataSource
from arbitragebot.data_sources.espn import ESPNDataSource
from arbitragebot.normalization import (
    KalshiNormalizer, PolymarketNormalizer, ESPNNormalizer
)
from arbitragebot.normalization.schemas import Sport
from arbitragebot.normalization.aggregator import canonical_event_id

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

load_dotenv()

# Fetch raw data from each provider
print("\n" + "="*60)
print("TESTING TEAM NAME EXTRACTION")
print("="*60)

# Kalshi
kalshi = KalshiDataSource(api_key=os.getenv("KALSHI_API_KEY"))
kalshi_raw = kalshi.fetch_markets()
kalshi_norm = KalshiNormalizer()

print(f"\nKALSHI: {len(kalshi_raw)} markets")
if kalshi_raw:
    for i, market in enumerate(kalshi_raw[:3]):
        title = market.get("title", "")
        event = kalshi_norm.normalize_market(market)
        if event:
            print(f"  [{i}] Title: {title}")
            print(f"      > Home: '{event.home_team}' Away: '{event.away_team}'")
            print(f"      > Sport: {event.sport}, Start: {event.start_time}")
        else:
            print(f"  [{i}] FAILED to normalize: {title}")

# ESPN
espn = ESPNDataSource()
espn_raw = espn.fetch_scoreboard("basketball", "nba")
espn_norm = ESPNNormalizer()

print(f"\nESPN: {len(espn_raw)} events")
if espn_raw:
    for i, event in enumerate(espn_raw[:3]):
        for comp in event.get("competitions", [])[:1]:
            canon_event = espn_norm.normalize_competition(comp, Sport.NBA)
            if canon_event:
                print(f"  [{i}] Home: '{canon_event.home_team}' Away: '{canon_event.away_team}'")
                print(f"      > Sport: {canon_event.sport}, Start: {canon_event.start_time}")

# Polymarket
polymarket = PolymarketDataSource(private_key=os.getenv("POLYMARKET_PRIVATE_KEY"))
pm_raw = polymarket.fetch_raw_markets()
pm_norm = PolymarketNormalizer()

print(f"\nPOLYMARKET: {len(pm_raw)} markets")
if pm_raw:
    count = 0
    for market in pm_raw:
        event = pm_norm.normalize_market(market)
        if event and ("vs" in event.away_team.lower() or "@" in event.away_team.lower()):
            print(f"  [{count}] Question: {market.get('question', '')}")
            print(f"      → Home: '{event.home_team}' Away: '{event.away_team}'")
            count += 1
            if count >= 3:
                break

print("\n" + "="*60)
print("TESTING CANONICAL EVENT IDs")
print("="*60)

from datetime import datetime

# Test identical events from different sources
test_cases = [
    ("nfl", ["Kansas City Chiefs", "Buffalo Bills"], datetime(2026, 1, 10, 14, 0)),
    ("nfl", ["Buffalo Bills", "Kansas City Chiefs"], datetime(2026, 1, 10, 14, 0)),
    ("nba", ["Los Angeles Lakers", "Boston Celtics"], datetime(2026, 1, 15, 19, 0)),
]

for sport, teams, start_time in test_cases:
    canonical_id = canonical_event_id(sport, teams, start_time)
    print(f"{sport.upper()} {teams[0]} @ {teams[1]} -> {canonical_id[:16]}...")
