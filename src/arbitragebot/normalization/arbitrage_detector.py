"""Market matching and arbitrage detection across normalized markets."""

import logging
import math
from typing import List, Optional

from arbitragebot.normalization.schemas import (
    CanonicalEvent, CanonicalMarket, CanonicalOutcome,
    MarketType, OutcomeType,
    DetectedArbitrage, ArbitrageOpportunitySingle
)
from arbitragebot.normalization.event_matching import MatchedEventSet

LOGGER = logging.getLogger(__name__)


class MarketMatcher:
    """Match markets across providers within a matched event set."""
    
    @staticmethod
    def find_matching_markets(matched_event_set: MatchedEventSet) -> List[List[CanonicalMarket]]:
        """Find matching markets across providers.
        
        Rules:
        1. Must be same market type
        2. If has line (spread/total), lines must match exactly
        3. Must exist on at least 2 providers
        
        Returns:
            List of market groups (each group = same market from 2+ providers)
        """
        markets_by_type_and_line = {}
        
        # Group markets by (type, line)
        for event in matched_event_set.all_events:
            for market in event.markets:
                key = (market.market_type, market.line)
                if key not in markets_by_type_and_line:
                    markets_by_type_and_line[key] = []
                markets_by_type_and_line[key].append(market)
        
        # Filter: keep only markets with 2+ providers
        matched_markets = [
            group for group in markets_by_type_and_line.values()
            if len(group) >= 2
        ]
        
        return matched_markets


class ArbitrageDetector:
    """Detect arbitrage opportunities across matched markets."""
    
    # Fee assumptions (in basis points: 50 bps = 0.5% fee)
    DEFAULT_FEE_BPS = 25  # 0.25% typical take
    
    def detect_arbitrage(
        self,
        matched_markets: List[List[CanonicalMarket]],
        matched_event_set: MatchedEventSet,
        min_edge_pct: float = 0.5,
        fee_bps: int = DEFAULT_FEE_BPS
    ) -> List[DetectedArbitrage]:
        """Detect arbitrage opportunities across matched markets.
        
        Args:
            matched_markets: Groups of matched markets from different providers
            matched_event_set: The matched event containing these markets
            min_edge_pct: Minimum edge % to report (default 0.5%)
            fee_bps: Exchange fee in basis points (default 25 bps = 0.25%)
            
        Returns:
            List of detected arbitrage opportunities
        """
        opportunities = []
        fee_ratio = 1.0 - (fee_bps / 10000.0)
        
        for markets in matched_markets:
            if not markets:
                continue
            
            market_type = markets[0].market_type
            
            if market_type == MarketType.YES_NO:
                arb = self._detect_binary_arbitrage(
                    markets, matched_event_set, min_edge_pct, fee_ratio
                )
            elif market_type == MarketType.MONEYLINE:
                arb = self._detect_moneyline_arbitrage(
                    markets, matched_event_set, min_edge_pct, fee_ratio
                )
            elif market_type == MarketType.SPREAD:
                arb = self._detect_spread_arbitrage(
                    markets, matched_event_set, min_edge_pct, fee_ratio
                )
            elif market_type == MarketType.TOTAL:
                arb = self._detect_total_arbitrage(
                    markets, matched_event_set, min_edge_pct, fee_ratio
                )
            else:
                continue
            
            if arb:
                opportunities.append(arb)
        
        return opportunities
    
    def _detect_binary_arbitrage(
        self,
        markets: List[CanonicalMarket],
        matched_event_set: MatchedEventSet,
        min_edge_pct: float,
        fee_ratio: float
    ) -> Optional[DetectedArbitrage]:
        """Detect YES/NO arbitrage.
        
        Math:
        - Find best YES price and best NO price across all providers
        - Sum implied probabilities: sum_prob = best_yes + best_no
        - If sum_prob < 1 - (fees), arbitrage exists
        - Profit = (1 / sum_prob) - 1
        """
        
        # Find best YES and NO prices
        best_yes = None
        best_yes_outcome = None
        best_yes_market = None
        best_yes_provider = None
        
        best_no = None
        best_no_outcome = None
        best_no_market = None
        best_no_provider = None
        
        for market in markets:
            for outcome in market.outcomes:
                provider = list(market.provider_market_ids.keys())[0] if market.provider_market_ids else "unknown"
                
                if outcome.outcome_type == OutcomeType.YES:
                    if best_yes is None or outcome.implied_probability > best_yes:
                        best_yes = outcome.implied_probability
                        best_yes_outcome = outcome
                        best_yes_market = market
                        best_yes_provider = provider
                
                elif outcome.outcome_type == OutcomeType.NO:
                    if best_no is None or outcome.implied_probability > best_no:
                        best_no = outcome.implied_probability
                        best_no_outcome = outcome
                        best_no_market = market
                        best_no_provider = provider
        
        if not (best_yes and best_no and best_yes_outcome and best_no_outcome):
            return None
        
        # Calculate arbitrage
        sum_prob = best_yes + best_no
        
        # Apply fees (multiply both prices by fee_ratio)
        sum_prob_after_fees = best_yes * fee_ratio + best_no * fee_ratio
        
        # Check for arbitrage
        if sum_prob_after_fees >= 1.0:
            return None
        
        arbitrage_pct = (1.0 / sum_prob_after_fees) - 1.0
        
        if arbitrage_pct * 100 < min_edge_pct:
            return None
        
        # Calculate stakes (Kelly criterion style allocation)
        bankroll = 1.0  # Assume $1 stake
        stake_yes = bankroll * (best_no / sum_prob)
        stake_no = bankroll * (best_yes / sum_prob)
        
        expected_payout = bankroll / sum_prob_after_fees
        expected_profit = expected_payout - bankroll
        
        legs = [
            ArbitrageOpportunitySingle(
                provider=best_yes_provider,
                outcome=best_yes_outcome,
                stake=round(stake_yes, 4),
                expected_payout=round(stake_yes * (1.0 / best_yes), 4)
            ),
            ArbitrageOpportunitySingle(
                provider=best_no_provider,
                outcome=best_no_outcome,
                stake=round(stake_no, 4),
                expected_payout=round(stake_no * (1.0 / best_no), 4)
            )
        ]
        
        return DetectedArbitrage(
            event_id=matched_event_set.canonical_event.event_id,
            event_name=matched_event_set.display_name(),
            sport=matched_event_set.canonical_event.sport,
            market_type=MarketType.YES_NO,
            market_id=markets[0].market_id,
            implied_probability_sum=sum_prob,
            arbitrage_percentage=arbitrage_pct,
            roi_percentage=arbitrage_pct * 100,
            expected_profit=expected_profit,
            legs=legs,
            execution_risk="low" if arbitrage_pct > 0.05 else "medium"
        )
    
    def _detect_moneyline_arbitrage(
        self,
        markets: List[CanonicalMarket],
        matched_event_set: MatchedEventSet,
        min_edge_pct: float,
        fee_ratio: float
    ) -> Optional[DetectedArbitrage]:
        """Detect moneyline arbitrage (same logic as binary for 2-way)."""
        
        # For now, treat as binary (HOME vs AWAY)
        # TODO: Handle 3-way (DRAW)
        
        best_home = None
        best_home_outcome = None
        best_home_market = None
        best_home_provider = None
        
        best_away = None
        best_away_outcome = None
        best_away_market = None
        best_away_provider = None
        
        for market in markets:
            for outcome in market.outcomes:
                provider = list(market.provider_market_ids.keys())[0] if market.provider_market_ids else "unknown"
                
                if outcome.outcome_type == OutcomeType.HOME:
                    if best_home is None or outcome.implied_probability > best_home:
                        best_home = outcome.implied_probability
                        best_home_outcome = outcome
                        best_home_market = market
                        best_home_provider = provider
                
                elif outcome.outcome_type == OutcomeType.AWAY:
                    if best_away is None or outcome.implied_probability > best_away:
                        best_away = outcome.implied_probability
                        best_away_outcome = outcome
                        best_away_market = market
                        best_away_provider = provider
        
        if not (best_home and best_away and best_home_outcome and best_away_outcome):
            return None
        
        sum_prob = best_home + best_away
        sum_prob_after_fees = best_home * fee_ratio + best_away * fee_ratio
        
        if sum_prob_after_fees >= 1.0:
            return None
        
        arbitrage_pct = (1.0 / sum_prob_after_fees) - 1.0
        
        if arbitrage_pct * 100 < min_edge_pct:
            return None
        
        bankroll = 1.0
        stake_home = bankroll * (best_away / sum_prob)
        stake_away = bankroll * (best_home / sum_prob)
        
        expected_payout = bankroll / sum_prob_after_fees
        expected_profit = expected_payout - bankroll
        
        legs = [
            ArbitrageOpportunitySingle(
                provider=best_home_provider,
                outcome=best_home_outcome,
                stake=round(stake_home, 4),
                expected_payout=round(stake_home * (1.0 / best_home), 4)
            ),
            ArbitrageOpportunitySingle(
                provider=best_away_provider,
                outcome=best_away_outcome,
                stake=round(stake_away, 4),
                expected_payout=round(stake_away * (1.0 / best_away), 4)
            )
        ]
        
        return DetectedArbitrage(
            event_id=matched_event_set.canonical_event.event_id,
            event_name=matched_event_set.display_name(),
            sport=matched_event_set.canonical_event.sport,
            market_type=MarketType.MONEYLINE,
            market_id=markets[0].market_id,
            implied_probability_sum=sum_prob,
            arbitrage_percentage=arbitrage_pct,
            roi_percentage=arbitrage_pct * 100,
            expected_profit=expected_profit,
            legs=legs,
            execution_risk="low" if arbitrage_pct > 0.05 else "medium"
        )
    
    def _detect_spread_arbitrage(
        self,
        markets: List[CanonicalMarket],
        matched_event_set: MatchedEventSet,
        min_edge_pct: float,
        fee_ratio: float
    ) -> Optional[DetectedArbitrage]:
        """Detect spread arbitrage."""
        # TODO: Implement spread arbitrage
        return None
    
    def _detect_total_arbitrage(
        self,
        markets: List[CanonicalMarket],
        matched_event_set: MatchedEventSet,
        min_edge_pct: float,
        fee_ratio: float
    ) -> Optional[DetectedArbitrage]:
        """Detect total arbitrage."""
        # TODO: Implement total arbitrage
        return None
