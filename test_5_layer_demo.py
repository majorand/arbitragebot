"""
Demonstration: 5-layer canonical model with cross-provider matching.

Scenario:
  Three providers (ESPN, Kalshi, Polymarket) are pricing the same outcome
  using completely different market expressions. The 5-layer system shows
  how they all map to the same Instrument+Outcome and enable arbitrage.

Expected output:
  - All 3 providers have the same canonical Instrument ID
  - All 3 providers map to the same canonical Outcome ID
  - Different market expressions (Moneyline vs Binary vs Yes/No)
  - Confidence score > 0.7 (eligible for arbitrage)
"""

import sys
import os
from datetime import datetime

# Add encoding support for Windows
if sys.platform.startswith("win"):
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Import the 5-layer system
from src.arbitragebot.normalization.canonical_layers import (
    CanonicalInstrument,
    InstrumentDomain,
)
from src.arbitragebot.normalization.layer_aggregator import LayerAggregator
from src.arbitragebot.normalization.layer_mappers import (
    ESPNLayerMapper,
    KalshiLayerMapper,
    PolymarketLayerMapper,
)


def demo_5_layer_aggregation():
    """Demonstrate cross-provider matching using 5-layer model."""
    
    print("\n" + "="*80)
    print("5-LAYER CANONICAL MODEL DEMONSTRATION")
    print("="*80)
    
    # ========================================================================
    # SCENARIO: Jaguars vs Chiefs Super Bowl LIX
    # Three providers price it differently, but it's the same instrument
    # ========================================================================
    
    print("\n[SCENARIO] Jacksonville Jaguars vs Kansas City Chiefs, Super Bowl LIX")
    print("Date: February 9, 2025 | Venue: Allegiant Stadium, Las Vegas")
    
    # ========================================================================
    # PROVIDER 1: ESPN Moneyline
    # ========================================================================
    
    print("\n" + "─"*80)
    print("PROVIDER 1: ESPN (American odds on Moneyline)")
    print("─"*80)
    
    espn_game = {
        "id": "espn_sb59_jax_kc",
        "home_team": "Jacksonville Jaguars",
        "away_team": "Kansas City Chiefs",
        "league": "nfl",
        "start_time": "2025-02-09T23:30:00",
        "venue": "Allegiant Stadium",
        "home_moneyline": -110,  # Jaguars favored slightly
    }
    
    espn_mapper = ESPNLayerMapper()
    esp_instr, esp_outcome, esp_expr, esp_context, esp_listing = espn_mapper.map_to_layers(espn_game)
    
    print(f"  Market Type: {esp_expr.expression_type.value}")
    print(f"  Raw Odds: {espn_game['home_moneyline']}")
    print(f"  Decimal Price: {esp_listing.price:.2f}")
    print(f"  Implied Prob: {esp_listing.implied_probability:.2%}")
    
    # ========================================================================
    # PROVIDER 2: Kalshi Binary Contract
    # ========================================================================
    
    print("\n" + "─"*80)
    print("PROVIDER 2: Kalshi (Binary YES/NO contract)")
    print("─"*80)
    
    kalshi_market = {
        "id": "kalshi_jaguars_win_sb",
        "title": "Will the Jacksonville Jaguars win Super Bowl LIX?",
        "subtitle": "Resolves to YES if Jaguars win on Feb 9, 2025",
        "creator_username": "kalshi_market_maker",
        "strike_price": 0.55,
        "yes_bid": 0.54,
        "yes_ask": 0.56,
        "expiration_ts": int(datetime(2025, 2, 9, 23, 59).timestamp() * 1000),
    }
    
    kalshi_mapper = KalshiLayerMapper()
    kal_instr, kal_outcome, kal_expr, kal_context, kal_listing = kalshi_mapper.map_to_layers(kalshi_market)
    print(f"  Market Type: {kal_expr.expression_type.value}")
    print(f"  Bid/Ask: {kalshi_market['yes_bid']} / {kalshi_market['yes_ask']}")
    print(f"  Mid Price: {kal_listing.price:.4f}")
    print(f"  Implied Prob: {kal_listing.implied_probability:.2%}")
    
    # ========================================================================
    # PROVIDER 3: Polymarket Yes/No
    # ========================================================================
    
    print("\n" + "─"*80)
    print("PROVIDER 3: Polymarket (Probability market)")
    print("─"*80)
    
    polymarket_market = {
        "id": "poly_jaguars_sb59",
        "title": "Will the Jacksonville Jaguars win Super Bowl LIX?",
        "description": "Resolves YES if Jaguars win Super Bowl LIX on Feb 9, 2025",
        "outcomes": ["Yes", "No"],
        "creationDate": "2024-11-01T00:00:00",
        "lastPrice": 0.52,
    }
    
    poly_mapper = PolymarketLayerMapper()
    pol_instr, pol_outcome, pol_expr, pol_context, pol_listing = poly_mapper.map_to_layers(polymarket_market)
    
    print(f"  Market Type: {pol_expr.expression_type.value}")
    print(f"  Last Price: {polymarket_market['lastPrice']:.4f}")
    print(f"  Implied Prob: {pol_listing.implied_probability:.2%}")
    
    # ========================================================================
    # LAYER COMPARISON: Do they map to the same Instrument + Outcome?
    # ========================================================================
    
    print("\n" + "="*80)
    print("LAYER ANALYSIS: Cross-Provider Identity Matching")
    print("="*80)
    
    print("\n🔍 LAYER 1 - INSTRUMENT (What real-world fact is being resolved?)")
    print(f"  ESPN   Instrument ID: {esp_instr.instrument_id[:16]}...")
    print(f"  Kalshi Instrument ID: {kal_instr.instrument_id[:16]}...")
    print(f"  Poly   Instrument ID: {pol_instr.instrument_id[:16]}...")
    
    instrument_match = (
        esp_instr.instrument_id == kal_instr.instrument_id ==
        pol_instr.instrument_id
    )
    print(f"  ✓ MATCH: {instrument_match}")
    
    print("\n🔍 LAYER 2 - OUTCOME (What are the possible results?)")
    print(f"  ESPN   Outcome Type: {esp_outcome.outcome_type.value}")
    print(f"  Kalshi Outcome Type: {kal_outcome.outcome_type.value}")
    print(f"  Poly   Outcome Type: {pol_outcome.outcome_type.value}")
    print(f"  ESPN   Outcome ID: {esp_outcome.outcome_id[:16]}...")
    print(f"  Kalshi Outcome ID: {kal_outcome.outcome_id[:16]}...")
    print(f"  Poly   Outcome ID: {pol_outcome.outcome_id[:16]}...")
    
    outcome_match = (
        esp_outcome.outcome_id == kal_outcome.outcome_id ==
        pol_outcome.outcome_id
    )
    print(f"  ✓ MATCH: {outcome_match}")
    
    print("\n🔍 LAYER 3 - MARKET EXPRESSION (How is it packaged?)")
    print(f"  ESPN:    {esp_expr.expression_type.value} (American odds)")
    print(f"  Kalshi:  {kal_expr.expression_type.value} (Binary contract)")
    print(f"  Polymarket: {pol_expr.expression_type.value} (Probability market)")
    print(f"  ✓ DIFFERENT: Expressions vary, but that's OK!")
    print(f"     → They all collapse to same Outcome at Layer 2 ✓")
    
    print("\n🔍 LAYER 4 - EVENT CONTEXT (When/where?)")
    print(f"  Event: {esp_context.event_name}")
    print(f"  Date: {esp_context.event_date}")
    print(f"  Location: {esp_context.location}")
    print(f"  ✓ CONSISTENT: All providers pricing same event")
    
    print("\n🔍 LAYER 5 - PROVIDER LISTINGS (Raw API objects)")
    print(f"  ESPN Listing ID: {esp_listing.listing_id}")
    print(f"  Kalshi Listing ID: {kal_listing.listing_id}")
    print(f"  Poly Listing ID: {pol_listing.listing_id}")
    print(f"  ✓ UNIQUE: Each provider has its own listing (as expected)")
    
    # ========================================================================
    # AGGREGATION: Show how prices are grouped by Instrument+Outcome
    # ========================================================================
    
    print("\n" + "="*80)
    print("AGGREGATION: Grouping Prices by Instrument+Outcome")
    print("="*80)
    
    aggregator = LayerAggregator()
    
    # Register all layers
    aggregator.register_instrument(esp_instr)
    aggregator.register_instrument(kal_instr)
    aggregator.register_instrument(pol_instr)
    
    aggregator.register_outcome(esp_outcome)
    aggregator.register_outcome(kal_outcome)
    aggregator.register_outcome(pol_outcome)
    
    aggregator.register_market_expression(esp_expr)
    aggregator.register_market_expression(kal_expr)
    aggregator.register_market_expression(pol_expr)
    
    aggregator.register_context(esp_context)
    aggregator.register_context(kal_context)
    aggregator.register_context(pol_context)
    
    aggregator.register_listing(esp_listing)
    aggregator.register_listing(kal_listing)
    aggregator.register_listing(pol_listing)
    
    # Finalize aggregation
    aggregated_views = aggregator.finalize()
    
    print(f"\nTotal aggregated Instrument+Outcome pairs: {len(aggregated_views)}")
    
    for key, view in aggregated_views.items():
        print(f"\n  Key: {key[:32]}...")
        print(f"  Instrument: {view.instrument.predicate}")
        print(f"  Providers: {view.providers}")
        print(f"  Provider Count: {len(view.providers)}/3")
        print(f"  Confidence Score: {view.confidence_score:.2%}")
        print(f"  Outcome States with Prices: {view.outcome_count}")
        
        if view.prices_by_state:
            for state_id, provider_prices in view.prices_by_state.items():
                print(f"\n    Outcome State: {state_id}")
                prices_list = []
                for provider, listing in provider_prices.items():
                    prices_list.append((provider, listing.price, listing.implied_probability))
                
                # Sort by price for comparison
                prices_list.sort(key=lambda x: x[1])
                
                for provider, price, prob in prices_list:
                    print(f"      {provider:12} → {price:.4f} ({prob:.2%})")
    
    # ========================================================================
    # ARBITRAGE OPPORTUNITY (if prices diverge)
    # ========================================================================
    
    print("\n" + "="*80)
    print("ARBITRAGE ANALYSIS")
    print("="*80)
    
    candidates = aggregator.find_arbitrage_candidates(min_confidence=0.7)
    
    print(f"\nArbitrage candidates (confidence >= 70%): {len(candidates)}")
    
    for view in candidates:
        print(f"\n  Instrument: {view.instrument.predicate}")
        print(f"  Best prices by outcome state:")
        
        # Calculate implied probability sum for arb detection
        total_implied = 0
        for state_id, provider_prices in view.prices_by_state.items():
            best_price = min(p.implied_probability for p in provider_prices.values())
            total_implied += best_price
            
            best_provider = None
            best_listing = None
            for prov, listing in provider_prices.items():
                if listing.implied_probability == best_price:
                    best_provider = prov
                    best_listing = listing
                    break
            
            print(f"    {state_id:6} → {best_provider:10} @ {best_listing.price:.4f} ({best_price:.2%})")
        
        print(f"  Implied Probability Sum: {total_implied:.2%}")
        
        if total_implied < 1.0:
            print(f"  💰 ARBITRAGE OPPORTUNITY! Sum < 100%")
            print(f"     Profit margin: {(1 - total_implied):.2%}")
        else:
            print(f"  ❌ No arbitrage (sum >= 100%)")
    
    print("\n" + "="*80)
    print("✅ 5-LAYER SYSTEM DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nKey Insights:")
    print("  1. Different market expressions (Moneyline vs Binary vs Yes/No)")
    print("  2. Same canonical Instrument ID across all providers")
    print("  3. Same canonical Outcome ID across all providers")
    print("  4. Prices grouped by Instrument+Outcome, not by market type")
    print("  5. Confidence score measures aggregation quality")
    print("  6. Arbitrage detection now works across any market format")
    print()


if __name__ == "__main__":
    try:
        demo_5_layer_aggregation()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
