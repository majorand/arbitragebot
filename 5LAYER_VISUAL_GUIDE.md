# 5-Layer System - Visual Guide

## Layer Hierarchy

```
                    INSTRUMENT (What is it?)
                    ↑
                Real-world fact to be resolved
        "Jacksonville Jaguars beat Kansas City Chiefs"
                    ↓
        
        ┌─────────────────────────────────────────┐
        │                                         │
        ▼                                         ▼
        
    OUTCOME (What are results?)        MARKET EXPRESSION (How framed?)
    
    YES / NO                           Moneyline (ESPN)
    HOME / AWAY                        Binary (Kalshi)
    OVER / UNDER                       Probability (Polymarket)
        
        └─────────────────────────────────────────┘
                    ↓
                    
        EVENT CONTEXT (When/where?)
        
        Date: Feb 9, 2026
        Location: Allegiant Stadium
        Participants: JAG vs KC
                    ↓
                    
        PROVIDER LISTING (Raw API)
        
        {ESPN data}, {Kalshi data}, {Polymarket data}
```

## Data Flow

```
STEP 1: DATA COLLECTION
═══════════════════════════════════════════════════════════════

Provider 1: ESPN
    {
      "id": "sb59",
      "home_team": "Jacksonville Jaguars",
      "away_team": "Kansas City Chiefs",
      "home_moneyline": -110,
      "start_time": "2025-02-09T23:30:00"
    }

Provider 2: Kalshi
    {
      "id": "kalshi_jaguars_sb",
      "title": "Will Jacksonville Jaguars beat Kansas City Chiefs?",
      "yes_bid": 0.54,
      "yes_ask": 0.56,
      "expiration_ts": 1739046000000
    }

Provider 3: Polymarket
    {
      "id": "poly_sb59",
      "title": "Will Jacksonville Jaguars beat Kansas City Chiefs?",
      "outcomes": ["Yes", "No"],
      "lastPrice": 0.52
    }


STEP 2: NORMALIZATION (Apply 5 Layers)
═══════════════════════════════════════════════════════════════

ESPN Data → ESPNLayerMapper
└─ Layer 1 (Instrument): "jacksonville_jaguars_vs_kansas_city_chiefs"
└─ Layer 2 (Outcome): {HOME: "Jaguars", AWAY: "Chiefs"}
└─ Layer 3 (Expression): Moneyline
└─ Layer 4 (Context): Date=2/9, Venue=Allegiant
└─ Layer 5 (Listing): {price: 1.91, provider: espn}

Kalshi Data → KalshiLayerMapper
└─ Layer 1 (Instrument): "jacksonville_jaguars" (MISMATCH - needs both teams!)
└─ Layer 2 (Outcome): {YES: "Win", NO: "Lose"}
└─ Layer 3 (Expression): Binary
└─ Layer 4 (Context): Date=2/9, Expiration
└─ Layer 5 (Listing): {price: 0.55, provider: kalshi}

Polymarket Data → PolymarketLayerMapper
└─ Layer 1 (Instrument): "jacksonville_jaguars" (MISMATCH - needs both teams!)
└─ Layer 2 (Outcome): {YES: "Win", NO: "Lose"}
└─ Layer 3 (Expression): Probability
└─ Layer 4 (Context): Date=11/1, Created
└─ Layer 5 (Listing): {price: 0.52, provider: polymarket}


STEP 3: AGGREGATION (Group by Layer 1 + Layer 2)
═══════════════════════════════════════════════════════════════

Layer Aggregator:
    
    Instrument 1: "jacksonville_jaguars_vs_kansas_city_chiefs"
    ├─ ESPN: Outcome=HOME/AWAY, Price=1.91
    │ (Currently stands alone because Kalshi/Polymarket have different Instrument ID)
    
    Instrument 2: "jacksonville_jaguars"
    ├─ Kalshi: Outcome=YES/NO, Price=0.55
    └─ Polymarket: Outcome=YES/NO, Price=0.52
    
    (AFTER FIX: All three will have same Instrument ID!)
    
    Instrument: "jacksonville_jaguars_vs_kansas_city_chiefs"
    ├─ ESPN:       Outcome=HOME/AWAY, Price=1.91, Confidence=0.85
    ├─ Kalshi:     Outcome=YES/NO, Price=0.55, Confidence=0.85
    └─ Polymarket: Outcome=YES/NO, Price=0.52, Confidence=0.85


STEP 4: ARBITRAGE DETECTION
═══════════════════════════════════════════════════════════════

View: Jacksonville Jaguars vs Kansas City Chiefs
├─ Providers: [ESPN, Kalshi, Polymarket]
├─ Best YES price: 0.52 (Polymarket)
├─ Best NO price: 0.45 (implied from Kalshi best for other outcome)
├─ Total implied prob: 0.52 + 0.45 = 0.97
└─ ROI: (1 - 0.97) = 0.03 = 3% PROFIT!

Detection Result:
┌────────────────────────────────────┐
│ ARBITRAGE OPPORTUNITY              │
├────────────────────────────────────┤
│ Instrument: Jaguars beat Chiefs    │
│ ROI: 3%                            │
│ Confidence: 85%                    │
│ Providers: ESPN, Kalshi, Polymarket│
│                                    │
│ Trade: BUY YES @ 0.52 + SELL HOME  │
│        @ 1.91 for 3% profit        │
└────────────────────────────────────┘
```

## Side-by-Side Comparison: Old vs New

```
OLD SYSTEM (Event-Based)
════════════════════════════════════════════════════════════

Event 1 (ESPN)
├─ Event ID: "espn_game_12345"
├─ Markets:
│  ├─ Moneyline (Home -110)
│  ├─ Spread (-2.5)
│  └─ Total (48.5)
└─ Outcomes: [Home wins, Away wins, Tie]

Event 2 (Kalshi)
├─ Event ID: "kalshi_market_67890"
├─ Markets:
│  └─ Binary (YES/NO)
└─ Outcomes: [YES, NO]

Event 3 (Polymarket)
├─ Event ID: "poly_abc123"
├─ Markets:
│  └─ Probability (Yes/No)
└─ Outcomes: [Yes, No]

Matching: FAILS!
  ESPN event ID ≠ Kalshi event ID ≠ Polymarket event ID
  System thinks these are 3 different events
  Result: No arbitrage detected ❌


NEW SYSTEM (5-Layer Based)
════════════════════════════════════════════════════════════

Data from all 3 providers:
┌─────────────────────────────────┐
│ Layer 1 (Instrument)            │
│ "jacksonville_jaguars_vs_...    │ ← Same ID for all!
│ Deterministic hash              │
└─────────────────────────────────┘
         ↓
┌─────────────────────────────────┐
│ Layer 2 (Outcome)               │
│ {YES: Win, NO: Lose}            │ ← All normalize to same
│ or {HOME: Win, AWAY: Lose}      │
└─────────────────────────────────┘
         ↓
┌─────────────────────────────────┐
│ Aggregator Groups               │
│ 3 providers → 1 view            │ ← All mapped to same view!
│ Confidence: 85%                 │
└─────────────────────────────────┘
         ↓
Matching: SUCCESS!
  All 3 providers price same outcome
  System finds 3% arbitrage opportunity
  Result: Arbitrage detected ✅
```

## Confidence Scoring

```
Provider Count Weight (0-1)
═══════════════════════════════════════════════════════════

1 provider:  0.33
2 providers: 0.67
3 providers: 1.00  ← Maximum

×

Outcome States Weight (0-1)
═══════════════════════════════════════════════════════════

1 outcome (YES only):     0.50
2 outcomes (YES and NO):  1.00  ← Both outcomes priced

×

Event Context Match (0-1)
═══════════════════════════════════════════════════════════

Dates match:             0.9
Dates differ slightly:   0.7
Dates very different:    0.3
No context provided:     0.5

=

FINAL CONFIDENCE
═══════════════════════════════════════════════════════════

Example 1: Perfect match
  (1.00) × (1.00) × (0.9) = 0.90 → TRADE ✓

Example 2: Good match
  (0.67) × (1.00) × (0.9) = 0.60 → SKIP ✗

Example 3: Weak match
  (0.33) × (0.50) × (0.5) = 0.08 → SKIP ✗

Typical threshold: 0.70 (70%)
```

## Provider Expression Mapping

```
Different providers use different expressions:

Moneyline (ESPN)
  -110  = implied probability 52.4%
           decimal odds 1.91
  +110  = implied probability 47.6%
           decimal odds 2.10

Binary (Kalshi)
  0.55  = implied probability 55%
           price in cents, range [0.00-1.00]

Probability (Polymarket)
  0.52  = implied probability 52%
           decimal from 0-1

ALL MAP TO SAME OUTCOME:
  "Jaguars win this game"
  
  ESPN -110  →  Layer 2: YES @ 52.4%
  Kalshi 0.55 →  Layer 2: YES @ 55.0%
  Poly 0.52  →  Layer 2: YES @ 52.0%
  
  Best YES price: 0.52 (Polymarket)
  
This is the power of Layer 3 (Expression): 
Different formats, same underlying outcome!
```

## Adding New Providers

```
To add FanDuel (sportsbook):

1. Create FanDuelLayerMapper (copy ESPN pattern)
   
   class FanDuelLayerMapper:
       def map_to_layers(self, game):
           # Extract FanDuel-specific fields
           # Map through 5 layers (same as others)
           # Return (instrument, outcome, expr, context, listing)

2. Register in providers.py
   
   PROVIDER_MAPPERS['fandue'] = FanDuelLayerMapper()

3. Done! The aggregator automatically:
   - Converts FanDuel data to 5 layers
   - Compares with other providers
   - Finds new cross-provider opportunities
   
   No changes needed to detector, UI, or execution!
```

## Matching Logic Visualization

```
Do all 3 providers match?

Step 1: Instrument ID
┌──────────────────────────────────────┐
│ ESPN:       a57f4ee06dc05df1...      │
│ Kalshi:     a57f4ee06dc05df1... ✓    │ ← SAME!
│ Polymarket: a57f4ee06dc05df1... ✓    │
└──────────────────────────────────────┘

Step 2: Outcome ID
┌──────────────────────────────────────┐
│ ESPN:       a98d03b02d895319...      │
│ Kalshi:     a98d03b02d895319... ✓    │ ← SAME!
│ Polymarket: a98d03b02d895319... ✓    │
└──────────────────────────────────────┘

Step 3: Group by (Instrument, Outcome)
┌──────────────────────────────────────┐
│ Key: a57f4ee06dc05df1 : a98d03b0...  │
│ Providers: [ESPN, Kalshi, Polymarket]│
│ Confidence: 0.85                     │
└──────────────────────────────────────┘

Result: MATCH! One aggregated view for all 3 providers.
```

---

**Visual Guide Version**: 1.0  
**Last Updated**: January 4, 2026
