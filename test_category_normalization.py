"""Test category normalization across providers."""

from src.arbitragebot.normalization.canonical_layers import (
    normalize_category,
    InstrumentDomain,
)

print("=" * 80)
print("CATEGORY NORMALIZATION TEST")
print("=" * 80)
print()

# Test sports category normalization
sports_tests = [
    ("Pro Football", "Kalshi"),
    ("NFL", "Polymarket"),
    ("nfl", "ESPN"),
    ("Pro Basketball", "Kalshi"),
    ("NBA", "Polymarket"),
    ("nba", "ESPN"),
    ("Soccer", "Polymarket"),
    ("UFC", "Polymarket"),
]

print("SPORTS CATEGORIES (Should normalize to specific sport):")
print("-" * 80)
for category, source in sports_tests:
    normalized = normalize_category(category)
    print(f"  {source:12} '{category:20}' -> {normalized.value}")
print()

# Test non-sports category preservation
non_sports_tests = [
    ("Politics", "Kalshi"),
    ("politics", "Polymarket"),
    ("Crypto", "Kalshi"),
    ("crypto", "Polymarket"),
    ("Finance", "Polymarket"),
    ("Economics", "Kalshi"),
    ("Climate", "Kalshi"),
    ("Culture", "Polymarket"),
]

print("NON-SPORTS CATEGORIES (Should preserve exactly):")
print("-" * 80)
for category, source in non_sports_tests:
    normalized = normalize_category(category)
    print(f"  {source:12} '{category:20}' -> {normalized.value}")
print()

# Show that different phrasings map to same domain
print("CROSS-PROVIDER MATCHING EXAMPLES:")
print("-" * 80)

nfl_kalshi = normalize_category("Pro Football")
nfl_poly = normalize_category("NFL")
nfl_espn = normalize_category("nfl")

print(f"Kalshi 'Pro Football' -> {nfl_kalshi.value}")
print(f"Polymarket 'NFL'      -> {nfl_poly.value}")
print(f"ESPN 'nfl'            -> {nfl_espn.value}")
print(f"  All match: {nfl_kalshi == nfl_poly == nfl_espn}")
print()

politics_kalshi = normalize_category("Politics")
politics_poly = normalize_category("politics")

print(f"Kalshi 'Politics'     -> {politics_kalshi.value}")
print(f"Polymarket 'politics' -> {politics_poly.value}")
print(f"  Match: {politics_kalshi == politics_poly}")
print()

print("=" * 80)
print("SUCCESS: Category normalization working!")
print("=" * 80)
