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

logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)

load_dotenv()

# Fetch raw data from each provider
print("\n" + "="*60)
print("TESTING SPORTS DISTRIBUTION")
print("="*60)

# Kalshi
print("\nFetching from Kalshi...")
kalshi = KalshiDataSource(api_key=os.getenv("KALSHI_API_KEY"))
kalshi_raw = kalshi.fetch_markets()
kalshi_norm = KalshiNormalizer()

sports = {}
for market in kalshi_raw[:50]:  # Sample
    event = kalshi_norm.normalize_market(market)
    if event:
        sport_name = event.sport.value if hasattr(event.sport, 'value') else str(event.sport)
        sports[sport_name] = sports.get(sport_name, 0) + 1

print(f"KALSHI sports (sample of 50):")
for sport, count in sorted(sports.items(), key=lambda x: -x[1]):
    print(f"  {sport}: {count}")

# ESPN
print("\nFetching from ESPN...")
espn = ESPNDataSource()
espn_raw = espn.fetch_scoreboard("basketball", "nba")
espn_norm = ESPNNormalizer()

sports = {}
for event in espn_raw[:50]:
    for comp in event.get("competitions", []):
        canon_event = espn_norm.normalize_competition(comp, Sport.NBA)
        if canon_event:
            sport_name = canon_event.sport.value if hasattr(canon_event.sport, 'value') else str(canon_event.sport)
            sports[sport_name] = sports.get(sport_name, 0) + 1

print(f"ESPN sports:")
for sport, count in sorted(sports.items(), key=lambda x: -x[1]):
    print(f"  {sport}: {count}")

# Polymarket
print("\nFetching from Polymarket...")
polymarket = PolymarketDataSource(private_key=os.getenv("POLYMARKET_PRIVATE_KEY"))
pm_raw = polymarket.fetch_raw_markets()
pm_norm = PolymarketNormalizer()

sports = {}
for market in pm_raw[:100]:  # Sample
    event = pm_norm.normalize_market(market)
    if event:
        sport_name = event.sport.value if hasattr(event.sport, 'value') else str(event.sport)
        sports[sport_name] = sports.get(sport_name, 0) + 1

print(f"POLYMARKET sports (sample of 100):")
for sport, count in sorted(sports.items(), key=lambda x: -x[1]):
    print(f"  {sport}: {count}")

print("\n" + "="*60)
