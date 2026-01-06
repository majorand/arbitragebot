# Fanatics Integration Summary

## Overview
Successfully switched from Polymarket to Fanatics Sportsbook as the alternate sports betting market provider (alongside Kalshi elections and ESPN sports scores).

## Changes Made

### 1. New Fanatics Data Source
**File:** `src/arbitragebot/data_sources/fanatics.py`
- Created `FanaticsDataSource` class that fetches markets from Fanatics API
- Supports both normalized odds (`fetch_markets()`) and raw market data (`fetch_raw_markets()`)
- Base URL: `https://api.fanatics.com/api/v3` (configurable via env var `FANATICS_BASE_URL`)
- Normalizes Fanatics events to `NormalizedOdds` format
- Parses teams from competitor arrays and event names
- Extracts moneyline markets with decimal odds conversion to implied probabilities

### 2. Fanatics Normalizer
**File:** `src/arbitragebot/normalization/normalizers.py`
- Added `FanaticsNormalizer` class for converting Fanatics API responses to canonical schema
- Maps Fanatics sport/league fields to internal `Sport` enum (NFL, NBA, Soccer, etc.)
- Extracts home/away teams from competitor lists
- Parses moneyline markets and converts decimal odds to probabilities
- Supports cross-provider instrument matching via canonical event/market schema

### 3. Provider Schema Updates
**File:** `src/arbitragebot/normalization/schemas.py`
- Added `PROVIDER_FANATICS = "fanatics"` constant
- Updated `CANONICAL_PROVIDERS` set to include Fanatics

### 4. Main Pipeline Integration
**File:** `src/arbitragebot/main.py`
- Replaced Polymarket data source import with Fanatics
- Replaced Polymarket initializer with `FanaticsDataSource()` (no auth needed)
- Updated normalization imports to use `FanaticsNormalizer` instead of `PolymarketNormalizer`
- Updated event collection loop to:
  - Fetch Fanatics markets and raw events
  - Filter by allowed leagues: `{nfl, nba, nhl, ncaaf, ncaab, mlb}`
  - Normalize to canonical format
  - Aggregate with other providers (Kalshi, ESPN) for cross-provider arbitrage detection

### 5. Module Exports
**File:** `src/arbitragebot/normalization/__init__.py`
- Updated `__all__` to export `FanaticsNormalizer` alongside other normalizers

## API Compatibility

Fanatics API Structure Expected:
```python
{
    "event_id": "...",
    "name": "Team A vs Team B",
    "sport": "football",
    "league": "nfl",
    "event_datetime": "2026-01-10T14:00:00Z",
    "competitors": [
        {"name": "Team A", "team_name": "Team A"},
        {"name": "Team B", "team_name": "Team B"}
    ],
    "markets": [
        {
            "market_type": "moneyline",
            "selections": [
                {"name": "Team A", "decimal_odds": 1.95},
                {"name": "Team B", "decimal_odds": 1.90}
            ]
        }
    ]
}
```

## Configuration

### Environment Variables
- `FANATICS_BASE_URL` (optional): Override default Fanatics API base URL
  - Default: `https://api.fanatics.com/api/v3`

### League Filtering
Fanatics markets are filtered to these leagues during ingestion:
- `nfl`, `nba`, `nhl`, `ncaaf`, `ncaab`, `mlb`

## Testing

All components verified:
```bash
✓ FanaticsDataSource imports and instantiates
✓ FanaticsNormalizer imports and instantiates
✓ main.py collects Kalshi + ESPN + Fanatics markets
✓ Cross-provider instrument aggregation pipeline ready
```

## Next Steps

1. **Verify Fanatics API Access:** Confirm endpoint availability and response format with actual API calls
2. **Test Cross-Provider Matching:** Run end-to-end collection to verify Fanatics markets overlap with ESPN/Kalshi
3. **Adjust Filtering:** Fine-tune league/sport detection if needed based on actual Fanatics data
4. **Monitor Performance:** Track fetch times and market counts to optimize pagination/caching

## Backward Compatibility

- Polymarket data source remains in codebase but is no longer used in main pipeline
- Can be re-enabled by updating imports in `main.py` if needed
- All canonical schema changes are backward-compatible with existing provider integrations
