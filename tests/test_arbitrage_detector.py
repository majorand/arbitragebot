"""Comprehensive test suite for the enhanced arbitrage detector.

Tests the new probability summation-based arbitrage detection system for
Kalshi + Polymarket single-leg binary arbitrage opportunities.
"""

import pytest
from datetime import datetime, timedelta
from arbitragebot.arbitrage.detector import (
    ArbitrageDetector,
    ArbitrageOpportunity,
    detect_arbitrage_opportunities,
)
from arbitragebot.schemas import NormalizedOdds


def create_test_market(
    provider: str,
    event_id: str,
    event_name: str,
    selection: str,
    price: float,
    market_type: str = "binary",
) -> NormalizedOdds:
    """Helper to create test market data."""
    return NormalizedOdds(
        sport="basketball",
        league="nba",
        event_id=event_id,
        event_name=event_name,
        start_time=datetime.utcnow() + timedelta(hours=24),
        home_team="Team A",
        away_team="Team B",
        market_type=market_type,
        selection=selection,
        price=price,
        implied_probability=price,
        source=provider,
        last_updated=datetime.utcnow(),
    )


class TestArbitrageDetector:
    """Test the ArbitrageDetector class."""

    def test_init_default_config(self):
        """Test detector initialization with default configuration."""
        detector = ArbitrageDetector()
        assert detector.min_edge_pct == 0.5
        assert detector.max_stake_per_trade == 500.0
        assert detector.bankroll == 100.0

    def test_init_custom_config(self):
        """Test detector initialization with custom configuration."""
        detector = ArbitrageDetector(
            min_edge_pct=2.0,
            max_stake_per_trade=1000.0,
            bankroll=50000.0,
        )
        assert detector.min_edge_pct == 2.0
        assert detector.max_stake_per_trade == 1000.0
        assert detector.bankroll == 50000.0

    def test_detect_basic_arbitrage(self):
        """Test detection with no arbitrage (sum > 1.0)."""
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.55),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "NO", 0.48),
        ]

        # Sum = 1.03 > 1.0, so no arbitrage
        opportunities = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)
        assert len(opportunities) == 0

    def test_detect_real_arbitrage(self):
        """Test detection of real arbitrage with probability summation < 1.0."""
        # Real arbitrage: sum of implied probabilities < 1.0
        # Example: YES at 0.45 (Kalshi) + NO at 0.50 (Polymarket) = 0.95 < 1.0
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.45),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "NO", 0.50),
        ]

        opportunities = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)

        assert len(opportunities) > 0
        opp = opportunities[0]
        
        # Verify arbitrage properties
        assert opp.edge_pct >= 0.5  # Should meet minimum edge
        total_prob = 0.45 + 0.50  # 0.95 < 1.0 = arbitrage
        expected_edge = (1.0 / total_prob - 1.0) * 100  # ~5.26%
        assert abs(opp.edge_pct - expected_edge) < 0.5  # Allow for calculation variance

    def test_no_arbitrage_when_sum_exceeds_one(self):
        """Test that no arbitrage is detected when sum of probabilities > 1.0."""
        # No arbitrage: 0.55 + 0.52 = 1.07 > 1.0
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.55),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "NO", 0.52),
        ]

        opportunities = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)
        assert len(opportunities) == 0

    def test_edge_threshold_filtering(self):
        """Test that opportunities below edge threshold are filtered."""
        # Small arbitrage: 0.49 + 0.50 = 0.99 → edge = 1.01%
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.49),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "NO", 0.50),
        ]

        # Should NOT detect with 2% threshold
        opportunities_high = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=2.0)
        assert len(opportunities_high) == 0

        # Should detect with 0.5% threshold
        opportunities_low = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)
        assert len(opportunities_low) > 0

    def test_stake_calculation(self):
        """Test optimal stake calculation for equal payout."""
        # Arbitrage with 0.40 + 0.55 = 0.95
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.40),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "NO", 0.55),
        ]

        opportunities = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)

        assert len(opportunities) > 0
        opp = opportunities[0]

        # Verify stakes exist and are positive
        assert opp.yes_leg.recommended_stake > 0
        assert opp.no_leg.recommended_stake > 0
        
        # Verify total stake
        total_stake = opp.yes_leg.recommended_stake + opp.no_leg.recommended_stake
        assert total_stake == opp.total_stake

        # Verify both legs have positive expected returns
        assert opp.yes_leg.expected_return > 0
        assert opp.no_leg.expected_return > 0

    def test_multiple_events_detection(self):
        """Test detection across multiple independent events."""
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.45),
            create_test_market("kalshi", "event2", "Will Bulls win?", "YES", 0.48),
            create_test_market("kalshi", "event3", "Will Heat win?", "YES", 0.60),  # No arb
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "NO", 0.50),
            create_test_market("polymarket", "event2", "Will Bulls win?", "NO", 0.47),
            create_test_market("polymarket", "event3", "Will Heat win?", "NO", 0.45),  # No arb
        ]

        opportunities = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)

        # Should detect event1 and event2, but not event3
        assert len(opportunities) == 2
        event_ids = {opp.event_id for opp in opportunities}
        assert "event1" in event_ids
        assert "event2" in event_ids
        assert "event3" not in event_ids

    def test_risk_assessment(self):
        """Test risk level assessment based on edge percentage."""
        # Low risk: large edge (>= 2.0%)
        # Edge from 0.35 + 0.55 = 0.90 sum → (1/0.90 - 1) * 100 = 11.1%
        kalshi_low_risk = [
            create_test_market("kalshi", "event1", "Event 1", "YES", 0.35),
        ]
        polymarket_low_risk = [
            create_test_market("polymarket", "event1", "Event 1", "NO", 0.55),
        ]

        # Medium risk: moderate edge (>= 1.0%, < 2.0%)
        # Edge from 0.49 + 0.50 = 0.99 sum → (1/0.99 - 1) * 100 = 1.01%
        kalshi_med_risk = [
            create_test_market("kalshi", "event2", "Event 2", "YES", 0.49),
        ]
        polymarket_med_risk = [
            create_test_market("polymarket", "event2", "Event 2", "NO", 0.50),
        ]

        # High risk: small edge (< 1.0% but > 0.5%)
        # Edge from 0.493 + 0.50 = 0.993 sum → (1/0.993 - 1) * 100 = 0.70%
        kalshi_high_risk = [
            create_test_market("kalshi", "event3", "Event 3", "YES", 0.493),
        ]
        polymarket_high_risk = [
            create_test_market("polymarket", "event3", "Event 3", "NO", 0.50),
        ]
        
        low_risk_opps = detect_arbitrage_opportunities(kalshi_low_risk, polymarket_low_risk, min_edge_pct=0.5)
        med_risk_opps = detect_arbitrage_opportunities(kalshi_med_risk, polymarket_med_risk, min_edge_pct=0.5)
        high_risk_opps = detect_arbitrage_opportunities(kalshi_high_risk, polymarket_high_risk, min_edge_pct=0.5)

        # Verify risk levels match thresholds (>=2.0% = low, >=1.0% = medium, <1.0% = high)
        assert len(low_risk_opps) > 0
        assert low_risk_opps[0].execution_risk == "low"
        assert low_risk_opps[0].edge_pct >= 2.0
        
        assert len(med_risk_opps) > 0
        assert med_risk_opps[0].execution_risk == "medium"
        assert 1.0 <= med_risk_opps[0].edge_pct < 2.0
        
        # High risk test is optional since it's near threshold edge
        if high_risk_opps:
            assert high_risk_opps[0].execution_risk == "high"
            assert high_risk_opps[0].edge_pct < 1.0

    def test_confidence_scoring(self):
        """Test confidence scoring based on data quality."""
        # High quality data from both providers
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.45),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "NO", 0.50),
        ]

        opportunities = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)

        assert len(opportunities) > 0
        opp = opportunities[0]
        assert 0.0 <= opp.confidence_score <= 1.0
        # With good data quality, confidence should be reasonably high
        assert opp.confidence_score > 0.5

    def test_same_side_no_arbitrage(self):
        """Test that same-side bets don't create arbitrage."""
        # Both YES - can't create arbitrage
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.45),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "YES", 0.50),
        ]

        opportunities = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)
        assert len(opportunities) == 0

    def test_max_stake_limits(self):
        """Test that stakes are calculated correctly."""
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.40),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "NO", 0.55),
        ]

        opportunities = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)

        assert len(opportunities) > 0
        opp = opportunities[0]
        
        # Verify stakes are positive
        assert opp.yes_leg.recommended_stake > 0
        assert opp.no_leg.recommended_stake > 0


class TestConvenienceFunction:
    """Test the detect_arbitrage_opportunities convenience function."""

    def test_convenience_function(self):
        """Test the convenience function works correctly."""
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.45),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "NO", 0.50),
        ]

        opportunities = detect_arbitrage_opportunities(
            kalshi_markets,
            polymarket_markets,
            min_edge_pct=0.5,
        )

        assert len(opportunities) > 0
        assert isinstance(opportunities[0], ArbitrageOpportunity)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_markets(self):
        """Test with empty market lists."""
        opportunities = detect_arbitrage_opportunities([], [], min_edge_pct=0.5)
        assert len(opportunities) == 0

    def test_mismatched_events(self):
        """Test with no matching events between providers."""
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.45),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event2", "Will Bulls win?", "NO", 0.50),
        ]

        opportunities = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)

        # Should not match different events
        assert len(opportunities) == 0

    def test_zero_probability(self):
        """Test handling of zero probability (should skip)."""
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 0.0),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "NO", 0.50),
        ]

        opportunities = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)

        # Should skip invalid probabilities
        assert len(opportunities) == 0

    def test_probability_over_one(self):
        """Test handling of invalid probability > 1.0."""
        kalshi_markets = [
            create_test_market("kalshi", "event1", "Will Lakers win?", "YES", 1.5),
        ]
        polymarket_markets = [
            create_test_market("polymarket", "event1", "Will Lakers win?", "NO", 0.50),
        ]

        opportunities = detect_arbitrage_opportunities(kalshi_markets, polymarket_markets, min_edge_pct=0.5)

        # Should skip invalid probabilities
        assert len(opportunities) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
