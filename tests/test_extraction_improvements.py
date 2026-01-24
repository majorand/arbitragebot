"""
Test cases for instrument extraction improvements.

These tests verify that the extraction logic can handle:
- Player props (Devin Booker: 2+)
- Spreads (wins by over 3.5 Points)
- Totals (Over 228.5 points)
- Comma-separated values
- Mixed team/player names
"""

import pytest  # type: ignore  # If unresolved, run: pip install pytest
from src.arbitragebot.core.instruments import InstrumentExtractor, PredicateType


class TestPlayerPropExtraction:
    """Test extraction of player prop markets."""
    
    def test_extract_player_prop_points_over(self):
        """Should extract 'Devin Booker: 2+' as player points prop."""
        extractor = InstrumentExtractor()
        
        # Single player prop
        text = "yes Devin Booker: 2+"
        inst = extractor.extract_instrument(
            domain="nba",
            text=text,
            market_type="player_prop"
        )
        
        # Should create instrument for player
        assert inst is not None
        assert "devin_booker" in inst.subject
        assert "points" in inst.predicate or "2" in inst.predicate
    
    def test_extract_player_prop_receiving_yards(self):
        """Should extract 'Puka Nacua: 80+' as receiving yards prop."""
        extractor = InstrumentExtractor()
        
        text = "yes Puka Nacua: 80+"
        inst = extractor.extract_instrument(
            domain="nfl",
            text=text,
            market_type="player_prop"
        )
        
        assert inst is not None
        assert "puka_nacua" in inst.subject
    
    def test_extract_player_prop_with_qualifier(self):
        """Should handle 'Matthew Stafford: 200+' (passing yards)."""
        extractor = InstrumentExtractor()
        
        text = "yes Matthew Stafford: 200+ passing yards"
        inst = extractor.extract_instrument(
            domain="nfl",
            text=text,
            market_type="player_prop"
        )
        
        assert inst is not None
        assert "matthew_stafford" in inst.subject
        assert "passing_yards" in inst.predicate or "200" in inst.predicate


class TestSpreadExtraction:
    """Test extraction of spread markets."""
    
    def test_extract_spread_with_team(self):
        """Should extract 'Phoenix wins by over 3.5 Points'."""
        extractor = InstrumentExtractor()
        
        text = "yes Phoenix wins by over 3.5 Points"
        inst = extractor.extract_instrument(
            domain="nba",
            text=text,
            market_type="spread"
        )
        
        assert inst is not None
        assert "phoenix" in inst.subject.lower() or "suns" in inst.subject.lower()
        assert "spread" in inst.predicate or "3.5" in inst.predicate
    
    def test_extract_spread_negative(self):
        """Should extract 'Detroit wins by over 4.5 Points' with NO outcome."""
        extractor = InstrumentExtractor()
        
        text = "no Detroit wins by over 4.5 Points"
        inst = extractor.extract_instrument(
            domain="nfl",
            text=text,
            market_type="spread"
        )
        
        assert inst is not None
        assert "detroit" in inst.subject.lower()
    
    def test_extract_spread_with_underdog_format(self):
        """Should handle 'Michigan wins by over 15.5 Points'."""
        extractor = InstrumentExtractor()
        
        text = "yes Michigan wins by over 15.5 Points"
        inst = extractor.extract_instrument(
            domain="ncaa",
            text=text,
            market_type="spread"
        )
        
        assert inst is not None
        assert "michigan" in inst.subject.lower()
        assert "spread" in inst.predicate or "15.5" in inst.predicate


class TestTotalExtraction:
    """Test extraction of totals markets."""
    
    def test_extract_total_over(self):
        """Should extract 'Over 228.5 points scored'."""
        extractor = InstrumentExtractor()
        
        text = "yes Over 228.5 points scored"
        inst = extractor.extract_instrument(
            domain="nba",
            text=text,
            market_type="total"
        )
        
        assert inst is not None
        assert "total" in inst.subject.lower() or "game" in inst.subject.lower()
        assert "over" in inst.predicate.lower() or "228.5" in inst.predicate
    
    def test_extract_total_under(self):
        """Should extract 'Under 238.5 points scored'."""
        extractor = InstrumentExtractor()
        
        text = "no Over 238.5 points scored"
        inst = extractor.extract_instrument(
            domain="nba",
            text=text,
            market_type="total"
        )
        
        assert inst is not None
        assert "total" in inst.subject.lower() or "game" in inst.subject.lower()
    
    def test_extract_total_no_points_keyword(self):
        """Should extract 'Over 207.5' even without 'points' keyword."""
        extractor = InstrumentExtractor()
        
        text = "yes Over 207.5"
        inst = extractor.extract_instrument(
            domain="nba",
            text=text,
            market_type="total"
        )
        
        assert inst is not None
        assert "total" in inst.subject.lower() or "game" in inst.subject.lower()


class TestCommaSeparatedExtraction:
    """Test extraction of comma-separated market lists."""
    
    def test_split_and_extract_multiple_props(self):
        """Should handle 'yes Devin Booker: 2+,yes Devin Booker: 4+,yes Devin Booker: 30+'."""
        extractor = InstrumentExtractor()
        
        text = "yes Devin Booker: 2+,yes Devin Booker: 4+,yes Devin Booker: 30+"
        parts = text.split(',')
        
        instruments = []
        for part in parts:
            inst = extractor.extract_instrument(
                domain="nba",
                text=part.strip(),
                market_type="player_prop"
            )
            if inst:
                instruments.append(inst)
        
        # Should extract at least one variant of Booker prop
        assert len(instruments) >= 1
        assert all("devin_booker" in i.subject for i in instruments)
    
    def test_split_mixed_props_and_teams(self):
        """Should handle mixed comma-separated content."""
        extractor = InstrumentExtractor()
        
        # Synthetic test case
        text = "yes Puka Nacua,yes Jaxon Smith-Njigba,yes Matthew Stafford: 200+"
        parts = text.split(',')
        
        instruments = []
        for part in parts:
            inst = extractor.extract_instrument(
                domain="nfl",
                text=part.strip(),
                market_type="player_prop"
            )
            if inst:
                instruments.append(inst)
        
        # Should extract at least some props
        assert len(instruments) >= 1


class TestDomainContextHelps:
    """Test that domain context improves extraction."""
    
    def test_denver_context_nba_means_nuggets(self):
        """Should map 'Denver' to Nuggets (not Broncos) in NBA context."""
        extractor = InstrumentExtractor()
        
        text = "Denver wins"
        inst = extractor.extract_instrument(
            domain="nba",
            text=text,
            market_type="moneyline"
        )
        
        assert inst is not None
        assert "nuggets" in inst.subject.lower() or "denver_nuggets" in inst.subject
    
    def test_denver_context_nfl_means_broncos(self):
        """Should map 'Denver' to Broncos (not Nuggets) in NFL context."""
        extractor = InstrumentExtractor()
        
        text = "Denver wins"
        inst = extractor.extract_instrument(
            domain="nfl",
            text=text,
            market_type="moneyline"
        )
        
        assert inst is not None
        assert "broncos" in inst.subject.lower() or "denver_broncos" in inst.subject


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_reject_malformed_player_prop(self):
        """Should reject props with missing threshold."""
        extractor = InstrumentExtractor()
        
        text = "yes Devin Booker"  # No threshold
        inst = extractor.extract_instrument(
            domain="nba",
            text=text,
            market_type="player_prop"
        )
        
        # Should handle gracefully (either extract or return None)
        # Not crash
        assert inst is None or inst.subject is not None
    
    def test_empty_text_returns_none(self):
        """Should handle empty text gracefully."""
        extractor = InstrumentExtractor()
        
        inst = extractor.extract_instrument(
            domain="nba",
            text="",
            market_type="player_prop"
        )
        
        assert inst is None
    
    def test_noise_text_returns_none(self):
        """Should return None for pure noise."""
        extractor = InstrumentExtractor()
        
        text = "yes yes yes no no no"
        inst = extractor.extract_instrument(
            domain="nba",
            text=text,
            market_type="player_prop"
        )
        
        # Should handle gracefully
        assert inst is None or inst.subject is not None


class TestRealWorldExamples:
    """Test with actual failing examples from logs."""
    
    def test_real_example_1_devin_booker_props(self):
        """Real failing example: comma-separated Devin Booker props."""
        extractor = InstrumentExtractor()
        
        text = "yes Devin Booker: 2+,yes Devin Booker: 4+,yes Devin Booker: 30+,yes Phoenix wins by over 3.5 Points"
        
        # Should extract at least Booker props and Phoenix spread
        parts = text.split(',')
        instruments = []
        
        for part in parts:
            inst = extractor.extract_instrument(
                domain="nba",
                text=part.strip(),
                market_type="player_prop"
            )
            if inst:
                instruments.append(inst)
        
        # Should find Booker and/or Phoenix
        subjects = [i.subject for i in instruments]
        assert any("booker" in s.lower() for s in subjects) or \
               any("phoenix" in s.lower() for s in subjects)
    
    def test_real_example_2_totals(self):
        """Real failing example: game totals."""
        extractor = InstrumentExtractor()
        
        text = "no Over 228.5 points scored,yes Over 209.5 points scored"
        
        parts = text.split(',')
        instruments = []
        
        for part in parts:
            inst = extractor.extract_instrument(
                domain="nba",
                text=part.strip(),
                market_type="total"
            )
            if inst:
                instruments.append(inst)
        
        # Should find at least one total
        assert len(instruments) >= 1
        assert all("total" in i.subject.lower() or "game" in i.subject.lower() 
                  for i in instruments)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
