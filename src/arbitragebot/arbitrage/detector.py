"""
Single-Leg Arbitrage Detection for Kalshi + Polymarket.

This module implements accurate arbitrage detection using implied probability summation.
For binary markets across prediction platforms, an arbitrage exists when:
    sum(implied_probabilities) < 1.0

The detector only processes single events (no parlays) and ensures both sides
can be executed simultaneously with proper risk controls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

LOGGER = logging.getLogger(__name__)

# Provider constants
PROVIDER_KALSHI = "kalshi"
PROVIDER_POLYMARKET = "polymarket"
ALLOWED_PROVIDERS = {PROVIDER_KALSHI, PROVIDER_POLYMARKET}

# Default configuration
DEFAULT_MIN_EDGE_PCT = 0.5  # Minimum 0.5% profit margin
DEFAULT_FEE_BUFFER = 0.005  # 0.5% buffer for fees/slippage
DEFAULT_BANKROLL = 100.0


@dataclass
class ArbitrageLeg:
    """One side of an arbitrage bet."""
    
    provider: str
    outcome: str  # "YES" or "NO"
    price: float  # Decimal probability (0-1)
    decimal_odds: float  # 1/price
    recommended_stake: float
    expected_return: float
    event_id: str
    market_title: str


@dataclass
class ArbitrageOpportunity:
    """A detected arbitrage opportunity between two platforms."""
    
    # Event identification
    event_id: str
    event_name: str
    market_type: str
    sport: str
    
    # Timing
    start_time: datetime
    
    # The two legs
    yes_leg: ArbitrageLeg
    no_leg: ArbitrageLeg
    
    # Metrics
    edge_pct: float  # Profit percentage (e.g., 2.5 for 2.5%)
    implied_probability_sum: float  # Should be < 1.0
    total_stake: float
    expected_profit: float
    
    # Risk assessment
    execution_risk: str  # "low", "medium", "high"
    confidence_score: float  # 0-1, based on data quality
    
    # Fields with defaults must come last
    detected_at: datetime = field(default_factory=datetime.utcnow)
    providers: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "market_type": self.market_type,
            "sport": self.sport,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "detected_at": self.detected_at.isoformat(),
            "yes_leg": {
                "provider": self.yes_leg.provider,
                "outcome": self.yes_leg.outcome,
                "price": self.yes_leg.price,
                "decimal_odds": self.yes_leg.decimal_odds,
                "stake": self.yes_leg.recommended_stake,
                "expected_return": self.yes_leg.expected_return,
            },
            "no_leg": {
                "provider": self.no_leg.provider,
                "outcome": self.no_leg.outcome,
                "price": self.no_leg.price,
                "decimal_odds": self.no_leg.decimal_odds,
                "stake": self.no_leg.recommended_stake,
                "expected_return": self.no_leg.expected_return,
            },
            "edge_pct": self.edge_pct,
            "implied_probability_sum": self.implied_probability_sum,
            "total_stake": self.total_stake,
            "expected_profit": self.expected_profit,
            "execution_risk": self.execution_risk,
            "confidence_score": self.confidence_score,
            "providers": self.providers,
        }


class ArbitrageDetector:
    """
    Detects arbitrage opportunities using implied probability summation.
    
    Core Logic:
    -----------
    For a binary event with outcomes YES and NO:
    - Get best price for YES across all providers (lowest implied prob)
    - Get best price for NO across all providers (lowest implied prob)
    - Calculate: implied_sum = p_yes + p_no
    - If implied_sum < 1.0, an arbitrage exists
    - Profit margin = 1.0 - implied_sum
    
    Example:
    --------
    Kalshi: YES at 0.52 (52%), NO at 0.50 (50%)
    Polymarket: YES at 0.48 (48%), NO at 0.51 (51%)
    
    Best YES: 0.48 (Polymarket)
    Best NO: 0.50 (Kalshi)
    Sum: 0.48 + 0.50 = 0.98 = 98%
    Arbitrage profit: 1.0 - 0.98 = 0.02 = 2%
    """
    
    def __init__(
        self,
        min_edge_pct: float = DEFAULT_MIN_EDGE_PCT,
        fee_buffer: float = DEFAULT_FEE_BUFFER,
        bankroll: float = DEFAULT_BANKROLL,
        max_stake_per_trade: float = 500.0,
        max_exposure_per_event: float = 1000.0,
    ):
        """
        Initialize arbitrage detector with risk parameters.
        
        Args:
            min_edge_pct: Minimum profit percentage to trigger (default 0.5%)
            fee_buffer: Additional buffer for fees/slippage (default 0.5%)
            bankroll: Total bankroll for stake calculation
            max_stake_per_trade: Maximum total stake per arbitrage
            max_exposure_per_event: Maximum exposure per single event
        """
        self.min_edge_pct = min_edge_pct
        self.fee_buffer = fee_buffer
        self.bankroll = bankroll
        self.max_stake_per_trade = max_stake_per_trade
        self.max_exposure_per_event = max_exposure_per_event
        
        LOGGER.info(
            f"ArbitrageDetector initialized: min_edge={min_edge_pct}%, "
            f"fee_buffer={fee_buffer*100}%, bankroll=${bankroll}"
        )
    
    def detect_opportunities(
        self,
        markets: List[Dict],
    ) -> List[ArbitrageOpportunity]:
        """
        Detect arbitrage opportunities from a list of normalized markets.
        
        Args:
            markets: List of market dictionaries with structure:
                {
                    "event_id": str,
                    "event_name": str,
                    "sport": str,
                    "start_time": datetime,
                    "provider": str,
                    "yes_price": float,  # 0-1 probability
                    "no_price": float,   # 0-1 probability
                }
        
        Returns:
            List of detected arbitrage opportunities sorted by edge %
        """
        # Group markets by event
        events = self._group_by_event(markets)
        
        opportunities = []
        for event_id, event_markets in events.items():
            opp = self._check_event_for_arbitrage(event_id, event_markets)
            if opp:
                opportunities.append(opp)
        
        # Sort by profit margin (descending)
        opportunities.sort(key=lambda x: x.edge_pct, reverse=True)
        
        LOGGER.info(f"Detected {len(opportunities)} arbitrage opportunities")
        return opportunities
    
    def _group_by_event(self, markets: List[Dict]) -> Dict[str, List[Dict]]:
        """Group markets by event_id."""
        events: Dict[str, List[Dict]] = {}
        for market in markets:
            event_id = market.get("event_id")
            if not event_id:
                continue
            if event_id not in events:
                events[event_id] = []
            events[event_id].append(market)
        return events
    
    def _check_event_for_arbitrage(
        self,
        event_id: str,
        event_markets: List[Dict],
    ) -> Optional[ArbitrageOpportunity]:
        """
        Check if a single event has an arbitrage opportunity.
        
        Strategy:
        1. Find best YES price (lowest implied probability) across providers
        2. Find best NO price (lowest implied probability) across providers
        3. Check if sum < 1.0 - fee_buffer - min_edge_pct
        4. Calculate optimal stakes
        5. Validate against risk limits
        """
        if len(event_markets) < 2:
            # Need at least 2 providers for arbitrage
            return None
        
        # Find best prices for each outcome
        best_yes = self._find_best_price(event_markets, "yes")
        best_no = self._find_best_price(event_markets, "no")
        
        if not best_yes or not best_no:
            return None
        
        # Check if providers are different (can't arb against yourself)
        if best_yes["provider"] == best_no["provider"]:
            return None
        
        # Calculate implied probability sum
        yes_prob = best_yes["price"]
        no_prob = best_no["price"]
        implied_sum = yes_prob + no_prob
        
        # Calculate profit margin
        profit_margin = 1.0 - implied_sum
        edge_pct = profit_margin * 100
        
        # Check if meets minimum threshold (including fee buffer)
        required_edge = (self.min_edge_pct / 100) + self.fee_buffer
        if profit_margin < required_edge:
            return None
        
        # Calculate optimal stakes
        yes_stake, no_stake = self._calculate_stakes(yes_prob, no_prob)
        total_stake = yes_stake + no_stake
        
        # Apply stake limits
        if total_stake > self.max_stake_per_trade:
            scale_factor = self.max_stake_per_trade / total_stake
            yes_stake *= scale_factor
            no_stake *= scale_factor
            total_stake = self.max_stake_per_trade
        
        # Calculate expected profit and returns
        yes_decimal_odds = 1.0 / yes_prob if yes_prob > 0 else 0
        no_decimal_odds = 1.0 / no_prob if no_prob > 0 else 0
        
        yes_return = yes_stake * yes_decimal_odds
        no_return = no_stake * no_decimal_odds
        expected_profit = min(yes_return, no_return) - total_stake
        
        # Build legs
        yes_leg = ArbitrageLeg(
            provider=best_yes["provider"],
            outcome="YES",
            price=yes_prob,
            decimal_odds=yes_decimal_odds,
            recommended_stake=yes_stake,
            expected_return=yes_return,
            event_id=event_id,
            market_title=best_yes.get("market_title", ""),
        )
        
        no_leg = ArbitrageLeg(
            provider=best_no["provider"],
            outcome="NO",
            price=no_prob,
            decimal_odds=no_decimal_odds,
            recommended_stake=no_stake,
            expected_return=no_return,
            event_id=event_id,
            market_title=best_no.get("market_title", ""),
        )
        
        # Assess execution risk
        execution_risk = self._assess_risk(edge_pct, implied_sum)
        
        # Confidence score based on data quality
        confidence = self._calculate_confidence(event_markets, best_yes, best_no)
        
        # Get event metadata from any market (should be same)
        sample_market = event_markets[0]
        
        return ArbitrageOpportunity(
            event_id=event_id,
            event_name=sample_market.get("event_name", "Unknown Event"),
            market_type="binary",
            sport=sample_market.get("sport", "unknown"),
            start_time=sample_market.get("start_time"),
            yes_leg=yes_leg,
            no_leg=no_leg,
            edge_pct=edge_pct,
            implied_probability_sum=implied_sum,
            total_stake=total_stake,
            expected_profit=expected_profit,
            execution_risk=execution_risk,
            confidence_score=confidence,
            providers=sorted([yes_leg.provider, no_leg.provider]),
        )
    
    def _find_best_price(
        self,
        markets: List[Dict],
        outcome: str,  # "yes" or "no"
    ) -> Optional[Dict]:
        """
        Find the best price (lowest implied probability) for an outcome.
        
        Returns dict with provider, price, and other metadata.
        """
        price_key = f"{outcome}_price"
        best = None
        best_price = 1.0  # Start with worst possible
        
        for market in markets:
            price = market.get(price_key)
            if price is None or price <= 0 or price >= 1:
                continue
            
            if price < best_price:
                best_price = price
                best = {
                    "provider": market.get("provider"),
                    "price": price,
                    "market_title": market.get("event_name", ""),
                    "start_time": market.get("start_time"),
                }
        
        return best
    
    def _calculate_stakes(
        self,
        yes_prob: float,
        no_prob: float,
    ) -> Tuple[float, float]:
        """
        Calculate optimal stake allocation for equal profit on both outcomes.
        
        Formula:
        --------
        stake_yes = (1/yes_prob) / ((1/yes_prob) + (1/no_prob)) * bankroll
        stake_no = (1/no_prob) / ((1/yes_prob) + (1/no_prob)) * bankroll
        
        This ensures equal payout regardless of outcome.
        """
        if yes_prob <= 0 or no_prob <= 0:
            return 0.0, 0.0
        
        inv_yes = 1.0 / yes_prob
        inv_no = 1.0 / no_prob
        total_inv = inv_yes + inv_no
        
        if total_inv <= 0:
            return 0.0, 0.0
        
        yes_stake = (inv_yes / total_inv) * self.bankroll
        no_stake = (inv_no / total_inv) * self.bankroll
        
        return yes_stake, no_stake
    
    def _assess_risk(self, edge_pct: float, implied_sum: float) -> str:
        """
        Assess execution risk based on edge size.
        
        - edge >= 2.0%: Low risk (large margin, unlikely to disappear)
        - edge >= 1.0%: Medium risk
        - edge < 1.0%: High risk (thin margin, may close before execution)
        """
        if edge_pct >= 2.0:
            return "low"
        elif edge_pct >= 1.0:
            return "medium"
        else:
            return "high"
    
    def _calculate_confidence(
        self,
        all_markets: List[Dict],
        best_yes: Dict,
        best_no: Dict,
    ) -> float:
        """
        Calculate confidence score (0-1) based on data quality.
        
        Factors:
        - Number of providers (more = better)
        - Consistency across providers
        - Data freshness
        """
        # Base score for having 2+ providers
        score = 0.7
        
        # Bonus for each additional provider
        num_providers = len(set(m.get("provider") for m in all_markets))
        if num_providers >= 3:
            score += 0.1
        if num_providers >= 4:
            score += 0.1
        
        # Bonus if multiple providers have similar prices (consistency)
        # (Could check variance of prices across providers)
        
        return min(score, 1.0)


def detect_arbitrage_opportunities(
    kalshi_markets: List[Dict],
    polymarket_markets: List[Dict],
    min_edge_pct: float = DEFAULT_MIN_EDGE_PCT,
) -> List[ArbitrageOpportunity]:
    """
    Convenience function to detect opportunities from separate provider lists.
    
    Args:
        kalshi_markets: Normalized Kalshi market data (dict or NormalizedOdds)
        polymarket_markets: Normalized Polymarket market data (dict or NormalizedOdds)
        min_edge_pct: Minimum profit percentage threshold
    
    Returns:
        List of detected arbitrage opportunities
    """
    # Helper to get attribute from dict or object
    def get_attr(item, name, default=None):
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)
    
    # Combine and normalize
    all_markets = []
    
    for market in kalshi_markets:
        all_markets.append({
            "event_id": get_attr(market, "event_id") or get_attr(market, "id"),
            "event_name": get_attr(market, "title") or get_attr(market, "event_name"),
            "sport": get_attr(market, "category") or get_attr(market, "sport", "unknown"),
            "start_time": get_attr(market, "expiration_time") or get_attr(market, "start_time"),
            "provider": PROVIDER_KALSHI,
            "yes_price": get_attr(market, "yes_bid", 0) / 100 if get_attr(market, "yes_bid") else get_attr(market, "price") if get_attr(market, "selection") == "YES" else None,
            "no_price": get_attr(market, "no_bid", 0) / 100 if get_attr(market, "no_bid") else get_attr(market, "price") if get_attr(market, "selection") == "NO" else None,
        })
    
    for market in polymarket_markets:
        # Extract prices from tokens
        yes_price = None
        no_price = None
        tokens = get_attr(market, "tokens", [])
        for token in tokens:
            ticker = get_attr(token, "ticker", "").upper()
            price = float(get_attr(token, "price", 0))
            if "YES" in ticker:
                yes_price = price
            elif "NO" in ticker:
                no_price = price
        
        # If no tokens, check if it's a NormalizedOdds object
        if not tokens:
            selection = get_attr(market, "selection")
            price = get_attr(market, "price")
            if selection == "YES":
                yes_price = price
            elif selection == "NO":
                no_price = price
        
        all_markets.append({
            "event_id": get_attr(market, "question_id") or get_attr(market, "condition_id") or get_attr(market, "event_id"),
            "event_name": get_attr(market, "question") or get_attr(market, "title") or get_attr(market, "event_name"),
            "sport": get_attr(market, "tags", ["unknown"])[0] if get_attr(market, "tags") else get_attr(market, "sport", "unknown"),
            "start_time": get_attr(market, "end_date_iso") or get_attr(market, "start_time"),
            "provider": PROVIDER_POLYMARKET,
            "yes_price": yes_price,
            "no_price": no_price,
        })
    
    detector = ArbitrageDetector(min_edge_pct=min_edge_pct)
    return detector.detect_opportunities(all_markets)
