"""Debug subject/predicate extraction from each provider."""

from datetime import datetime
from src.arbitragebot.normalization.layer_mappers import (
    ESPNLayerMapper,
    KalshiLayerMapper,
    PolymarketLayerMapper,
)

# Same test data as before
espn_game = {
    "id": "espn_sb59_jax_kc",
    "home_team": "Jacksonville Jaguars",
    "away_team": "Kansas City Chiefs",
    "league": "nfl",
    "start_time": "2025-02-09T23:30:00",
    "venue": "Allegiant Stadium",
    "home_moneyline": -110,
}

kalshi_market = {
    "id": "kalshi_jaguars_win_sb",
    "title": "Will Jacksonville Jaguars beat Kansas City Chiefs in Super Bowl?",
    "subtitle": "Resolves to YES if Jaguars win on Feb 9, 2025",
    "creator_username": "kalshi_market_maker",
    "strike_price": 0.55,
    "yes_bid": 0.54,
    "yes_ask": 0.56,
    "expiration_ts": int(datetime(2025, 2, 9, 23, 59).timestamp() * 1000),
}

polymarket_market = {
    "id": "poly_jaguars_sb59",
    "title": "Will Jacksonville Jaguars beat Kansas City Chiefs in Super Bowl LIX?",
    "description": "Resolves YES if Jaguars win Super Bowl LIX on Feb 9, 2025",
    "outcomes": ["Yes", "No"],
    "creationDate": "2024-11-01T00:00:00",
    "lastPrice": 0.52,
}

print("SUBJECT/PREDICATE EXTRACTION DEBUG")
print("="*80)

# ESPN
print("\nESPN:")
print(f"  home_team: {espn_game['home_team']}")
print(f"  away_team: {espn_game['away_team']}")
teams_sorted = sorted([espn_game['home_team'], espn_game['away_team']])
teams_canonical = "_vs_".join(t.lower().replace(" ", "_") for t in teams_sorted)
print(f"  teams_sorted: {teams_sorted}")
print(f"  teams_canonical: {teams_canonical}")
print(f"  predicate: moneyline_winner")

# Kalshi
print("\nKalshi:")
mapper_k = KalshiLayerMapper()
subject_k = mapper_k._extract_subject(kalshi_market['title'])
predicate_k = mapper_k._extract_predicate(kalshi_market['title'])
print(f"  title: {kalshi_market['title']}")
print(f"  extracted_subject: {subject_k}")
print(f"  extracted_predicate: {predicate_k}")

# Polymarket
print("\nPolymarket:")
mapper_p = PolymarketLayerMapper()
subject_p = mapper_p._extract_subject(polymarket_market['title'])
predicate_p = mapper_p._extract_predicate(polymarket_market['title'], polymarket_market['outcomes'])
print(f"  title: {polymarket_market['title']}")
print(f"  extracted_subject: {subject_p}")
print(f"  extracted_predicate: {predicate_p}")

print("\n" + "="*80)
print("COMPARISON:")
print(f"  ESPN subject:     {teams_canonical}")
print(f"  Kalshi subject:   {subject_k}")
print(f"  Polymarket subject: {subject_p}")

# Check if ESPN canonicalizes properly
import hashlib
def compute_id(domain, subject, predicate):
    key = f"{domain}|{subject}|{predicate}".encode()
    return hashlib.sha256(key).hexdigest()

print("\nINSTRUMENT IDs (computed with normalized inputs):")
esp_id = compute_id("sports", teams_canonical, "moneyline_winner")
kal_id = compute_id("sports", subject_k.replace("_", " ").title(), "moneyline_winner")
pol_id = compute_id("sports", subject_p.replace("_", " ").title(), "moneyline_winner")

print(f"  ESPN:      {esp_id[:16]}...")
print(f"  Kalshi:    {kal_id[:16]}...")
print(f"  Polymarket: {pol_id[:16]}...")
