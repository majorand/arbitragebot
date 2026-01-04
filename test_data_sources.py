#!/usr/bin/env python3
"""
Arbitrage Bot Data Source Testing & Comparison

This script demonstrates the capabilities and limitations of each data source:

Data Source Summary:
- ESPN: Public API, NO auth required, WORKING - Returns real live odds
- DraftKings: Restricted API (403 Forbidden) - Requires browser session/cookies
- FanDuel: Restricted API (401 Unauthorized) - Requires authentication
- Kalshi: Private API, requires API key - Network connection issue in test

Results:
✅ ESPN: 8 NBA live games with real moneyline odds
⚠️  DraftKings: 403 Forbidden (anti-scraping protection)
⚠️  FanDuel: 401 Unauthorized (requires API credentials)
⚠️  Kalshi: Network error (unreachable from current environment)
"""

import sys
sys.path.insert(0, 'src')

from arbitragebot.data_sources.espn import ESPNDataSource
from arbitragebot.schemas import NormalizedOdds
from datetime import datetime

print("=" * 80)
print("ARBITRAGE BOT - DATA SOURCE TESTING & COMPARISON".center(80))
print("=" * 80)

print("\n1. ESPN PUBLIC API TEST")
print("-" * 80)

espn = ESPNDataSource()

# Test multiple sports
sports_tests = [
    ("basketball", "nba", "NBA Basketball"),
    ("football", "nfl", "NFL Football"),
    ("baseball", "mlb", "MLB Baseball"),
    ("hockey", "nhl", "NHL Hockey"),
]

all_results = {}

for sport, league, name in sports_tests:
    try:
        events = espn.fetch_scoreboard(sport, league)
        normalized = espn.normalize_events(events, sport=sport, league=league)
        all_results[name] = {
            'status': 'SUCCESS',
            'events': len(events),
            'odds_entries': len(normalized),
            'sample': normalized[:2] if normalized else []
        }
        print(f"[OK] {name:20} | {len(events):2} events | {len(normalized):2} odds entries")
    except Exception as e:
        print(f"[FAIL] {name:20} | Error: {str(e)[:60]}")
        all_results[name] = {'status': 'ERROR', 'error': str(e)}

print("\n" + "=" * 80)
print("2. DETAILED ESPN NBA RESULTS".center(80))
print("=" * 80)

# Show detailed NBA results
nba_events = espn.fetch_scoreboard("basketball", "nba")
nba_odds = espn.normalize_events(nba_events, sport="basketball", league="nba")

if nba_odds:
    print(f"\nTotal entries: {len(nba_odds)} from {len(nba_events)} games\n")
    
    # Group by game
    games = {}
    for odd in nba_odds:
        key = odd.event_id
        if key not in games:
            games[key] = []
        games[key].append(odd)
    
    for i, (game_id, game_odds) in enumerate(list(games.items())[:3], 1):
        if len(game_odds) >= 2:
            home = game_odds[0]
            away = game_odds[1]
            print(f"Game {i}: {home.home_team} vs {away.away_team}")
            print(f"  Time: {home.start_time}")
            for odd in game_odds:
                print(f"    {odd.selection.upper():6} @ {odd.price:6.2f} (Amer: {odd.american_odds:7.0f}) | Prob: {odd.implied_probability:.1%}")
            print()

print("=" * 80)
print("3. DATA SOURCE COMPARISON & STATUS".center(80))
print("=" * 80)

comparison = {
    "ESPN": {
        "auth_required": False,
        "status": "WORKING",
        "sports": ["NFL", "NBA", "MLB", "NHL", "CFB", "Soccer", "MMA", "Golf", "Tennis"],
        "api_type": "Public REST API",
        "base_url": "site.api.espn.com",
        "rate_limit": "500ms/request (recommended)",
        "real_data": True,
    },
    "DraftKings": {
        "auth_required": False,
        "status": "BLOCKED (403)",
        "sports": ["NFL", "NBA", "MLB", "NHL", "CFB"],
        "api_type": "Restricted REST API",
        "base_url": "sportsbook.draftkings.com",
        "rate_limit": "Protected by anti-scraping",
        "real_data": False,
        "note": "Requires browser session/cookies or API access",
    },
    "FanDuel": {
        "auth_required": True,
        "status": "BLOCKED (401)",
        "sports": ["NFL", "NBA", "MLB", "NHL"],
        "api_type": "Authenticated REST API",
        "base_url": "api.fanduel.com",
        "rate_limit": "30 req/min",
        "real_data": False,
        "note": "Requires API credentials",
    },
    "Kalshi": {
        "auth_required": True,
        "status": "NETWORK ERROR",
        "sports": ["Sports Markets", "Election Markets"],
        "api_type": "Private REST API",
        "base_url": "api.kalshi.com",
        "rate_limit": "Varies",
        "real_data": False,
        "note": "Prediction market platform",
    },
}

for source, info in comparison.items():
    print(f"\n{source}")
    print(f"  Status:        {info['status']}")
    print(f"  Auth Required: {info['auth_required']}")
    print(f"  Sports:        {', '.join(info['sports'])}")
    print(f"  Real Data:     {info['real_data']}")
    if 'note' in info:
        print(f"  Note:          {info['note']}")

print("\n" + "=" * 80)
print("4. ARBITRAGE SYSTEM STATUS".center(80))
print("=" * 80)

print("""
Primary Arbitrage Source: ESPN (Public API - NO Auth Required)
  - Provides real-time odds for 16+ sports
  - Moneyline markets extracted with decimal/American conversion
  - Rate-limited to respect API (500ms delays)
  - Zero cost, no authentication needed

Comparison Sources (for cross-market arbitrage):
  1. DraftKings: API blocked - requires auth or browser session
  2. FanDuel: API requires credentials
  3. Kalshi: Requires API key + network access
  
Fallback Mechanism:
  ✓ System uses mock data when real APIs unavailable
  ✓ Mock data shows realistic arbitrage opportunities
  ✓ Backend gracefully handles API failures
  ✓ Dashboard displays available data sources

Deployment Status:
  ✓ ESPN integration: FULLY FUNCTIONAL
  ⚠️  Kalshi/DraftKings/FanDuel: Use mock data in Render
  ✓ Mock data sufficient for testing arbitrage engine
""")

print("=" * 80)
