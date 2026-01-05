# 5-Layer System - Integration Guide

## System Architecture

```
                    ARBITRAGE BOT ARCHITECTURE
                    
    ┌─────────────────────────────────────────────────────┐
    │  DATA COLLECTION LAYER (Providers)                  │
    │  • ESPN API (sports odds)                           │
    │  • Kalshi API (binary contracts)                    │
    │  • Polymarket API (prediction markets)              │
    │  • [Future: DraftKings, FanDuel, PredictIt]        │
    └──────────────────┬──────────────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────────────┐
    │  NORMALIZATION LAYER ← NEW 5-LAYER SYSTEM HERE     │
    │  • canonical_layers.py (5 layer schemas)            │
    │  • layer_mappers.py (provider converters)           │
    │  • layer_aggregator.py (grouping engine)            │
    │                                                      │
    │  Input: Raw API responses                           │
    │  Output: AggregatedInstrumentView (per Layer 1+2)   │
    └──────────────────┬──────────────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────────────┐
    │  ARBITRAGE DETECTION LAYER                          │
    │  • ArbitrageDetector (find opportunities)           │
    │  • Confidence filtering (min 0.7)                   │
    │  • ROI calculation (implied prob sum)               │
    │  • Risk assessment                                  │
    └──────────────────┬──────────────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────────────┐
    │  EXECUTION LAYER                                    │
    │  • Order routing (ESPN/Kalshi/Polymarket APIs)      │
    │  • Position tracking                                │
    │  • Risk limits & stops                              │
    └──────────────────┬──────────────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────────────┐
    │  PRESENTATION LAYER                                 │
    │  • Dashboard (React frontend)                       │
    │  • WebSocket updates (real-time)                    │
    │  • Trade history                                    │
    └─────────────────────────────────────────────────────┘
```

## Integration Points

### 1. Data Collection → Normalization

**Current**: `src/arbitragebot/main.py` orchestrates collection
**Future**: Use 5-layer mappers in the collection phase

```python
# BEFORE (current code)
from data_sources.espn import ESPNProvider
from data_sources.kalshi import KalshiProvider

providers = [ESPNProvider(), KalshiProvider()]
events = providers.fetch()

# AFTER (with 5-layer system)
from normalization.layer_mappers import ESPNLayerMapper, KalshiLayerMapper
from normalization.layer_aggregator import LayerAggregator

mappers = {
    'espn': ESPNLayerMapper(),
    'kalshi': KalshiLayerMapper(),
}

aggregator = LayerAggregator()
for provider_name, api_data in fetch_all_providers().items():
    mapper = mappers[provider_name]
    for item in api_data:
        instr, outcome, expr, context, listing = mapper.map_to_layers(item)
        aggregator.register_listing(listing)

# Get aggregated results
aggregated_views = aggregator.finalize()
```

### 2. Normalization → Arbitrage Detection

**Current**: ArbitrageDetector works with Event/Market/Outcome structures
**Future**: Update to work with AggregatedInstrumentView

```python
# BEFORE (current code)
detector = ArbitrageDetector(events)
opportunities = detector.find_opportunities()

# AFTER (with 5-layer system)
from arbitrage import ArbitrageDetector

detector = ArbitrageDetector()
opportunities = detector.find_opportunities(
    aggregated_views=aggregator.finalize(),
    min_confidence=0.7,
    min_roi=0.02  # 2%
)

# Result: List of Opportunity objects
# Each has: instrument, outcome, providers, best_prices, roi
```

### 3. Arbitrage Detection → Execution

**Current**: Trade executor takes Order objects
**Future**: Generate Orders from AggregatedInstrumentView

```python
class Opportunity:
    """Result from ArbitrageDetector"""
    instrument: CanonicalInstrument
    outcome: CanonicalOutcome
    providers: List[str]
    prices: Dict[str, float]
    roi: float
    confidence: float
    
    def to_orders(self) -> List[Order]:
        """Convert to tradeable orders"""
        # BUY low-priced outcomes, SELL high-priced outcomes
        # Example: BUY Polymarket NO @ 0.48, SELL Kalshi YES @ 0.55
        orders = []
        # ... order generation logic
        return orders

# In execution:
executor = TradeExecutor()
for opp in opportunities:
    orders = opp.to_orders()
    execution_result = executor.execute_atomic(orders)
```

## Modified Files

### 1. `src/arbitragebot/main.py` (WILL NEED UPDATE)

```python
# Current flow
def main():
    providers = init_providers()
    events = fetch_from_all(providers)
    detector = ArbitrageDetector(events)
    opportunities = detector.find()
    
# New flow with 5-layer
def main():
    providers = init_providers()
    raw_data = fetch_from_all(providers)
    
    # NEW: Use 5-layer aggregator
    aggregator = LayerAggregator()
    for provider_name, items in raw_data.items():
        mapper = get_mapper(provider_name)
        for item in items:
            instr, outcome, expr, context, listing = mapper.map_to_layers(item)
            aggregator.register_listing(listing)
    
    aggregated = aggregator.finalize()
    
    # UPDATED: ArbitrageDetector takes aggregated views
    detector = ArbitrageDetector()
    opportunities = detector.find_opportunities(aggregated, min_confidence=0.7)
```

### 2. `src/arbitragebot/arbitrage/detector.py` (WILL NEED UPDATE)

```python
# CURRENT
class ArbitrageDetector:
    def __init__(self, events):
        self.events = events
    
    def find_opportunities(self):
        for event in self.events:
            for market in event.markets:
                # Compare outcomes across providers

# UPDATED
class ArbitrageDetector:
    def __init__(self):
        self.opportunities = []
    
    def find_opportunities(self, aggregated_views: Dict[str, AggregatedInstrumentView],
                          min_confidence: float = 0.7,
                          min_roi: float = 0.01):
        """Find arbitrage in aggregated instrument views"""
        
        for key, view in aggregated_views.items():
            if view.confidence_score < min_confidence:
                continue
            
            if len(view.providers) < 2:
                continue
            
            # Calculate ROI
            total_implied = sum(
                min(p.implied_probability for p in prices.values())
                for prices in view.prices_by_state.values()
            )
            
            roi = 1.0 - total_implied
            
            if roi >= min_roi:
                self.opportunities.append(Opportunity(
                    instrument=view.instrument,
                    outcome=view.outcome,
                    providers=view.providers,
                    prices=view.prices_by_state,
                    roi=roi,
                    confidence=view.confidence_score,
                ))
        
        return self.opportunities
```

### 3. New File: `src/arbitragebot/normalization/providers.py`

Register all provider mappers in one place:

```python
from .layer_mappers import ESPNLayerMapper, KalshiLayerMapper, PolymarketLayerMapper

PROVIDER_MAPPERS = {
    'espn': ESPNLayerMapper(),
    'kalshi': KalshiLayerMapper(),
    'polymarket': PolymarketLayerMapper(),
    # 'draftkings': DraftKingsLayerMapper(),  # Future
    # 'fandue': FanDuelLayerMapper(),  # Future
    # 'predictit': PredictItLayerMapper(),  # Future
}

def get_mapper(provider_name: str):
    return PROVIDER_MAPPERS.get(provider_name)

def aggregate_all_providers(provider_data: Dict[str, List[dict]]):
    """End-to-end aggregation for all providers"""
    from .layer_aggregator import LayerAggregator
    
    aggregator = LayerAggregator()
    
    for provider_name, items in provider_data.items():
        mapper = get_mapper(provider_name)
        if not mapper:
            logging.warning(f"No mapper for {provider_name}")
            continue
        
        for item in items:
            try:
                instr, outcome, expr, context, listing = mapper.map_to_layers(item)
                aggregator.register_listing(listing)
            except Exception as e:
                logging.error(f"Failed to map {provider_name} item: {e}")
    
    return aggregator.finalize()
```

## Data Flow Example: Jaguars Super Bowl

```
1. DATA COLLECTION
   ESPN API returns:
   {
     "id": "sb59",
     "home_team": "Jacksonville Jaguars",
     "away_team": "Kansas City Chiefs",
     "home_moneyline": -110,
     ...
   }
   
   Kalshi API returns:
   {
     "id": "kalshi_jag_win",
     "title": "Will Jacksonville Jaguars beat Kansas City Chiefs?",
     "yes_bid": 0.54,
     "yes_ask": 0.56,
     ...
   }

2. NORMALIZATION (5-LAYER MAPPERS)
   ESPN → Layer 1: Instrument = "jacksonville_jaguars_vs_kansas_city_chiefs"
           Layer 2: Outcome = {HOME: "Yes", AWAY: "No"}
           Layer 3: Expression = Moneyline
           Layer 5: Listing = {price: 1.91, provider: espn}
   
   Kalshi → Layer 1: Instrument = "jacksonville_jaguars_vs_kansas_city_chiefs"
            Layer 2: Outcome = {YES: "Yes", NO: "No"}
            Layer 3: Expression = Binary
            Layer 5: Listing = {price: 0.55, provider: kalshi}

3. AGGREGATION
   LayerAggregator groups by (Layer 1 + Layer 2):
   
   AggregatedInstrumentView {
     instrument: "Jaguars vs Chiefs",
     outcome: {HOME: "Yes", AWAY: "No"},
     providers: ["espn", "kalshi"],
     prices_by_state: {
       "HOME": {"espn": 1.91, "kalshi": 0.55},
       "AWAY": {"espn": 2.40, "kalshi": 0.45}
     },
     confidence: 0.85
   }

4. ARBITRAGE DETECTION
   Detector calculates:
   - Best YES price: 0.55 (Kalshi)
   - Best NO price: (1/2.40) = 0.417 (ESPN)
   - Total implied: 0.55 + 0.417 = 0.967
   - ROI: 1.0 - 0.967 = 3.3% ✓ Opportunity!

5. EXECUTION
   Orders:
   - BUY YES on Kalshi @ 0.55
   - SELL HOME on ESPN @ 1.91 (hedge)
   - Result: Locked in 3.3% profit regardless of outcome
```

## Migration Checklist

- [ ] Create new provider mapper files (in progress)
- [ ] Create aggregate_all_providers() helper
- [ ] Update ArbitrageDetector to use AggregatedInstrumentView
- [ ] Update main.py flow to use 5-layer system
- [ ] Update UI dashboard to render per-Instrument
- [ ] Add confidence filtering (min 0.7)
- [ ] Test end-to-end with live APIs
- [ ] Deprecate old aggregation code
- [ ] Deploy to Render

## Backwards Compatibility

**Old code paths**: Continue working until all modules updated
**Transition**: Feature flags to toggle between old/new aggregation

```python
USE_5_LAYER_AGGREGATION = os.getenv("USE_5_LAYER", "false").lower() == "true"

if USE_5_LAYER_AGGREGATION:
    aggregated = aggregate_all_providers(provider_data)
    opportunities = detector.find_opportunities(aggregated)
else:
    # Use old code path
    events = legacy_aggregation(provider_data)
    opportunities = detector.find_opportunities_legacy(events)
```

## Performance Considerations

| Operation | Complexity | Time (est.) |
|-----------|-----------|------------|
| Map item through 5 layers | O(1) | <1ms |
| Aggregate 1000 items | O(n) | 50ms |
| Calculate confidence | O(p²) | <1ms (p=3 providers) |
| Find opportunities | O(n) | <100ms |
| **Total pipeline** | **O(n)** | **<200ms** |

All operations are fast enough for real-time trading.

## Summary

The 5-layer system is a fundamental redesign that enables:

1. **Cross-provider matching**: Different formats → same outcome
2. **Confidence scoring**: Know quality of each match
3. **Scalability**: Add providers by adding a mapper
4. **Determinism**: Same instrument always gets same ID
5. **Clarity**: Layers make logic explicit and testable

Once integrated with ArbitrageDetector and the UI, the system will find real arbitrage opportunities across Kalshi, Polymarket, and ESPN.
