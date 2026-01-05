# 5-Layer Canonical Model - Implementation Guide

## Overview

The 5-layer canonical model solves cross-provider arbitrage detection by explicitly separating concerns:

1. **Instrument** (What is being resolved)
2. **Outcome** (Possible result states)
3. **Market Expression** (How providers package outcomes)
4. **Event Context** (When/where - optional metadata)
5. **Provider Listing** (Raw API objects)

Matching happens at Layer 1+2 only. Layers 3-5 are supporting.

##Key Principle

> **Different providers with different market formats resolve to the same Instrument+Outcome**

Example:
- ESPN: Moneyline (2.1 odds on home team)
- Kalshi: Binary contract (0.48 YES price)
- Polymarket: Probability market (0.52 YES)

All three price the SAME outcome ("Jaguars win") via different market expressions.

## Implementation Status

✓ Schema definitions complete (canonical_layers.py)
✓ Aggregator engine complete (layer_aggregator.py)
✓ Provider mappers created (layer_mappers.py):
  - ESPN mapper: Converts odds to canonical layers
  - Kalshi mapper: Converts binary contracts to canonical layers
  - Polymarket mapper: Converts prob markets to canonical layers
✓ Demo test created (test_5_layer_simple.py)

## Next Steps

### 1. Normalize Subject Extraction (CURRENT)

All providers must extract the same "subject" from their market data.

**Current Challenge**: 
- ESPN has structured data: home_team="Jacksonville Jaguars", away_team="Kansas City Chiefs"
- Kalshi/Polymarket have unstructured titles: "Will Jacksonville Jaguars beat Kansas City Chiefs?"
- Extraction logic must normalize both to canonical form

**Solution Approaches**:

**Option A: Home Team Only**
- All extract just the home/primary team: "jacksonville_jaguars"
- Use Event Context (date/opponent) for confidence scoring
- ✓ Simple, deterministic
- ✗ Less granular - misses some potential arbitrage

**Option B: Both Teams, Sorted** 
- ESPN: sort [home, away] → "jacksonville_jaguars_vs_kansas_city_chiefs"
- Kalshi/Polymarket: extract both from title → "jacksonville_jaguars_vs_kansas_city_chiefs"
- ✓ More granular matching
- ✗ Requires robust team extraction from unstructured titles

**Option C: Entity Extraction (Recommended for Production)**
- Use spaCy NER or sports-specific entity recognizer
- Extract team names from any text
- Normalize league codes ("JAX" → "Jacksonville Jaguars")
- ✓ Robust across formats
- ✗ Adds dependency

### 2. Test with Real Data

Once subject normalization works, run against actual provider APIs:
```python
from layer_aggregator import aggregate_multi_provider_events

provider_data = {
    "espn": espn_api.get_games(),
    "kalshi": kalshi_api.get_markets(),
    "polymarket": poly_api.get_markets(),
}

views = aggregate_multi_provider_events(provider_data)

# This should show 10+ events where 2+ providers have prices
for view in views.filter_by_confidence(min_confidence=0.7):
    print(f"{view.instrument.subject}: {view.providers}")
```

### 3. Integration Points

**ArbitrageDetector**: Update to work with `AggregatedInstrumentView`:
```python
detector = ArbitrageDetector(min_confidence=0.7)
opportunities = detector.find_opportunities(aggregated_views)
```

**UI/Dashboard**: Render one row per Instrument, not per Event:
```json
{
  "instrument": "Jacksonville Jaguars win",
  "providers": ["espn", "kalshi", "polymarket"],
  "outcomes": {
    "YES": { "best_price": 0.52, "provider": "polymarket" },
    "NO": { "best_price": 0.48, "provider": "kalshi" }
  },
  "arbitrage_roi": 0.04  // 4% profit margin
}
```

### 4. Production Refinements

**Confidence Scoring**: Currently uses provider count. Enhance with:
- Event context matching (same date/venue)
- Outcome state alignment (binary YES/NO vs moneyline HOME/AWAY)
- Team name edit distance (for typo tolerance)

**Canonicalization**: Add explicit mappings:
```python
TEAM_ALIASES = {
    "jaguars": "jacksonville_jaguars",
    "jax": "jacksonville_jaguars",
    "chiefs": "kansas_city_chiefs",
    "kc": "kansas_city_chiefs",
}
```

## Architecture Diagram

```
┌─────────────────────┐
│  Provider APIs      │
│  (ESPN, Kalshi...)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Provider Mappers   │ ◄──── Converts API → 5 Layers
│  (ESPN, Kalshi...)  │
└──────────┬──────────┘
           │
      ┌────┴────┐
      ▼         ▼
    L1-L2    L3-L5
 (Matching)  (Support)
      │         │
      └────┬────┘
           ▼
   ┌──────────────────┐
   │ Layer Aggregator │ ◄──── Groups by Instrument+Outcome
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────────┐
   │ AggregatedViews      │ ◄──── One row per (Instrument, Outcome)
   │ (with confidence)    │       Contains all provider prices
   └────────┬─────────────┘
            │
            ▼
   ┌──────────────────────┐
   │ Arbitrage Detector   │ ◄──── Find profitable opportunities
   └────────┬─────────────┘
            │
            ▼
   ┌──────────────────────┐
   │ Opportunities        │ ◄──── Display & execute trades
   └──────────────────────┘
```

## Key Files

- **canonical_layers.py**: Schema definitions for all 5 layers
- **layer_aggregator.py**: Aggregation engine (grouping by Instrument+Outcome)
- **layer_mappers.py**: Provider-specific mappers (ESPN, Kalshi, Polymarket)
- **test_5_layer_simple.py**: Demo showing all 3 providers pricing same instrument
- **debug_extraction.py**: Debug tool for subject extraction

## Testing Checklist

- [ ] Subject extraction normalizes all providers to same value
- [ ] Instrument IDs match across providers (same game/market)
- [ ] Outcome IDs match (YES/NO, HOME/AWAY, etc.)
- [ ] Aggregation groups correctly (1 view per instrument, not per provider)
- [ ] Confidence scores > 0.7 when 2+ providers present
- [ ] UI renders instrument rows, not event rows
- [ ] Arbitrage detection finds profitable opportunities
- [ ] Confidence threshold correctly filters low-quality matches

## Known Limitations

1. **Subject Extraction**: Currently simple string parsing. Production should use NER.
2. **Outcome Mapping**: Currently assumes binary outcomes. Need multi-outcome support.
3. **Event Context Matching**: Not yet using date/venue for confidence scoring.
4. **Team Aliases**: No normalization of team name variations.
5. **Historical Data**: System designed for real-time; no backtest support yet.

## Next Session Action Items

1. Choose subject extraction approach (Option A/B/C)
2. Implement chosen approach
3. Test against actual API data
4. Integrate with ArbitrageDetector
5. Update UI to render AggregatedInstrumentView
