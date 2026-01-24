#!/usr/bin/env python3
"""Quick test of instrument extraction improvements."""

from src.arbitragebot.core.instruments import InstrumentExtractor

def test_extraction():
    extractor = InstrumentExtractor()
    
    tests = [
        {
            "name": "Player prop - Devin Booker: 2+",
            "text": "yes Devin Booker: 2+",
            "domain": "nba",
            "market_type": "player_prop",
        },
        {
            "name": "Spread - Phoenix wins by 3.5",
            "text": "yes Phoenix wins by over 3.5 Points",
            "domain": "nba",
            "market_type": "spread",
        },
        {
            "name": "Total - Over 228.5 points",
            "text": "yes Over 228.5 points scored",
            "domain": "nba",
            "market_type": "total",
        },
        {
            "name": "Team moneyline - Houston",
            "text": "yes Houston",
            "domain": "nba",
            "market_type": "moneyline",
        },
    ]
    
    print("=" * 70)
    print("INSTRUMENT EXTRACTION TESTS")
    print("=" * 70)
    
    for test in tests:
        inst = extractor.extract_instrument(
            domain=test["domain"],
            text=test["text"],
            market_type=test["market_type"]
        )
        
        print(f"\nTest: {test['name']}")
        print(f"  Text: {test['text']}")
        
        if inst:
            print(f"  ✓ Subject: {inst.subject}")
            print(f"  ✓ Predicate: {inst.predicate}")
        else:
            print(f"  ✗ FAILED to extract")
    
    # Test batch extraction
    print("\n" + "=" * 70)
    print("BATCH EXTRACTION TEST")
    print("=" * 70)
    
    batch_text = "yes Devin Booker: 2+,yes Devin Booker: 4+,yes Phoenix wins by over 3.5 Points"
    insts = extractor.extract_instruments_batch(
        domain="nba",
        text=batch_text
    )
    
    print(f"\nBatch text: {batch_text}")
    print(f"Extracted {len(insts)} instruments:")
    for i, inst in enumerate(insts, 1):
        print(f"  {i}. {inst.subject} ({inst.predicate})")

if __name__ == "__main__":
    test_extraction()
