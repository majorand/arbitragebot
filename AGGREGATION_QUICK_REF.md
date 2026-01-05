# Quick Reference - Aggregation Pipeline

## How It Works

```
Normalizers (extract from provider APIs)
    ↓
Create CanonicalEvent with placeholder IDs
    ↓
Aggregator (compute canonical IDs)
    ↓
Group events by ID
    ↓
Tag outcomes with provider names
    ↓
Arbitrage Detector (compare prices)
    ↓
Find profitable opportunities
```

## Key Concepts

### Canonical Event ID
**What:** Provider-agnostic event identifier
**How:** SHA256(sport | sorted_teams | datetime)
**Result:** Same event from different providers gets same hash

### Canonical Market Key
**What:** Market type + line identifier
**How:** "moneyline" or "spread:2.5" or "total:45.5"
**Result:** Markets grouped by type, outcomes tagged by provider

### Aggregated Event Structure
```json
{
  "event_id": "7084f63fb57d485c...",
  "sport": "nba",
  "home_team": "Cavaliers",
  "away_team": "Pistons",
  "start_time": "2026-01-04T19:00:00",
  "providers": ["espn", "polymarket"],
  "markets": {
    "moneyline": {
      "outcomes": {
        "home": {
          "espn": {"price": 1.54, "implied_probability": 0.65},
          "polymarket": {"price": 0.62, "implied_probability": 0.62}
        },
        "away": {
          "espn": {"price": 2.40, "implied_probability": 0.35},
          "polymarket": {"price": 0.38, "implied_probability": 0.38}
        }
      }
    }
  }
}
```

## Adding a New Provider

1. **Create Normalizer**
   ```python
   class MyNormalizer(BaseNormalizer):
       def normalize_market(self, market) -> Optional[CanonicalEvent]:
           # Extract participants
           home_team, away_team = self._parse_participants(title)
           
           # Create event with EMPTY event_id
           event = CanonicalEvent(
               event_id="",  # Important: empty!
               sport=sport,
               league="MyProvider",
               home_team=home_team,
               away_team=away_team,
               start_time=start_time,
               provider_event_ids={"myprovider": provider_id}
           )
           
           # Add markets and outcomes
           # ...
           return event
   ```

2. **Implement _parse_participants**
   ```python
   def _parse_participants(self, title: str) -> tuple[str, str]:
       if " vs " in title:
           parts = title.split(" vs ")
           return (parts[0].strip(), parts[1].strip())
       # Fallback: use hash for uniqueness
       import hashlib
       h = hashlib.md5(title.encode()).hexdigest()[:8]
       return (f"provider_{title[:20]}_{h}", "MARKET")
   ```

3. **Register in main.py**
   ```python
   from my_provider import MyDataSource
   from arbitragebot.normalization import MyNormalizer
   
   # In collect_market_data():
   my_provider = MyDataSource(api_key=...)
   my_raw = my_provider.fetch_markets()
   my_norm = MyNormalizer()
   my_events = []
   for market in my_raw:
       event = my_norm.normalize_market(market)
       if event:
           my_events.append(event)
   events_by_provider["myprovider"] = my_events
   ```

## Testing Aggregation

### Unit Test
```bash
python test_synthetic_agg.py
```

### Debug Sports Distribution
```bash
python debug_sports.py
```

### Run Full Pipeline
```bash
python src/arbitragebot/main.py 2>&1 | grep -E "Aggregat|cross-provider"
```

Expected output for cross-provider events:
```
Aggregated 1052 unique events from 3 providers
Aggregation stats: 1052 total, 1 cross-provider, 1051 single-provider
ARBITRAGE DETECTION PHASE: Scanning cross-provider outcomes
```

## Debugging No Cross-Provider Events

**Question:** Why does my provider show "0 cross-provider events"?

**Answers:**
1. ✓ Provider events have different sports (ESPN=NBA, Kalshi=OTHER)
2. ✓ Team names don't parse correctly (check _parse_participants)
3. ✓ Start times differ by >1 minute (check canonical_event_id logic)
4. ✓ Provider genuinely has no overlapping events

**Debug steps:**
```bash
# 1. Check what sports are being extracted
python debug_sports.py

# 2. Check canonical IDs for specific events
python test_canonical_ids.py

# 3. Run synthetic test to prove aggregation works
python test_synthetic_agg.py

# 4. Add logging to normalizer
# In normalize_market():
LOGGER.info(f"Event: {home_team} @ {away_team}, Sport: {sport}")
```

## Configuration

### Which Providers to Use

**For Sports Arbitrage:**
- ESPN (odds reference)
- DraftKings (legal sportsbook)
- FanDuel (legal sportsbook)

**For Political/Prediction Markets:**
- PredictIt
- Kalshi (legal prediction exchange)
- Polymarket (global prediction market)

**For Crypto Prediction:**
- Polymarket (crypto options)
- Polymarket (general)

## Performance

### Aggregation Speed
- 100 Kalshi events: <0.1s
- 8 ESPN events: <0.01s
- 944 Polymarket events: <0.3s
- **Total: ~0.4s for 1052 events**

### Memory
- Aggregated events: ~1 MB for 1000 events
- Outcome structure: Minimal (dict of dicts)

## Common Issues

### Issue: "No cross-provider events found"
**Cause:** Providers have different event focus
**Solution:** Add more sports books (DraftKings, FanDuel) that overlap with ESPN

### Issue: Teams show as "Participant 1", "Participant 2"
**Cause:** _parse_participants() fallback triggered
**Solution:** Improve parsing logic or check raw data format

### Issue: Events aggregated but still "0 cross-provider"
**Cause:** All providers created one event, but then failed to match
**Solution:** Check that canonical_event_id() produces same hash for both

## References

- `AGGREGATION_COMPLETE.md` - Detailed architecture
- `AGGREGATION_FINAL_SUMMARY.md` - Full implementation docs
- `test_synthetic_agg.py` - Working example
- `src/arbitragebot/normalization/` - Source code
