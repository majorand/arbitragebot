"""Arbitrage calculation engine.

Detects profitable arbitrage opportunities across multiple sportsbooks
and calculates optimal stake allocation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class ArbitrageOpportunity:
    """Represents a detected arbitrage opportunity."""
    
    event_id: str
    event_name: str
    market_type: str
    sport: str
    league: str
    start_time: datetime
    
    # Legs of the arbitrage
    legs: List[ArbitrageLeg]
    
    # Metrics
    arbitrage_percentage: float  # e.g., 0.021 for 2.1% profit
    total_stake_required: float
    expected_profit: float
    
    # Risk factors
    vig_removed: float
    execution_risk: str  # "low", "medium", "high"
    
    detected_at: datetime


@dataclass
class ArbitrageLeg:
    """One leg of an arbitrage bet."""
    
    source: str  # e.g., "fanduel", "draftkings", "kalshi"
    selection: str  # e.g., "Team A Win", "YES", "OVER 45.5"
    
    # Odds in multiple formats
    decimal_odds: float
    american_odds: Optional[float]
    implied_probability: float
    
    # Stake allocation
    recommended_stake: float
    expected_return: float


def is_arbitrage(
    decimal_odds_list: List[float],
    fee_buffer: float = 0.005
) -> bool:
    """Check if a set of odds represents an arbitrage opportunity.
    
    Args:
        decimal_odds_list: List of decimal odds for all outcomes
        fee_buffer: Safety buffer for fees/slippage (default 0.5%)
        
    Returns:
        True if arbitrage exists after accounting for buffer
    """
    if not decimal_odds_list or any(o <= 0 for o in decimal_odds_list):
        return False
    
    total_implied_prob = sum(1/odds for odds in decimal_odds_list)
    return total_implied_prob < (1.0 - fee_buffer)


def calculate_arbitrage_percentage(decimal_odds_list: List[float]) -> float:
    """Calculate the arbitrage profit percentage.
    
    Args:
        decimal_odds_list: List of decimal odds
        
    Returns:
        Profit percentage (e.g., 0.021 for 2.1% profit)
    """
    if not decimal_odds_list or any(o <= 0 for o in decimal_odds_list):
        return 0.0
    
    total_implied_prob = sum(1/odds for odds in decimal_odds_list)
    if total_implied_prob >= 1.0:
        return 0.0
    
    return 1.0 - total_implied_prob


def allocate_stakes(
    bankroll: float,
    decimal_odds_list: List[float]
) -> List[float]:
    """Calculate optimal stake allocation for equal profit on all outcomes.
    
    Uses the standard arbitrage staking formula where each stake is proportional
    to the inverse of its odds.
    
    Args:
        bankroll: Total amount to stake across all legs
        decimal_odds_list: Decimal odds for each outcome
        
    Returns:
        List of stake amounts for each outcome
    """
    if not decimal_odds_list or bankroll <= 0:
        return [0.0] * len(decimal_odds_list)
    
    # Calculate inverse odds (implied probabilities)
    inv_odds = [1/odds for odds in decimal_odds_list if odds > 0]
    total_inv = sum(inv_odds)
    
    if total_inv <= 0:
        return [0.0] * len(decimal_odds_list)
    
    # Allocate stakes proportionally
    return [(bankroll * inv / total_inv) for inv in inv_odds]


def calculate_kelly_stakes(
    bankroll: float,
    decimal_odds_list: List[float],
    true_probabilities: List[float],
    kelly_fraction: float = 0.25
) -> List[float]:
    """Calculate Kelly Criterion stake allocation (optional, more aggressive).
    
    Warning: Kelly can be volatile. Use fractional Kelly (e.g., 0.25) for safety.
    
    Args:
        bankroll: Total bankroll
        decimal_odds_list: Decimal odds
        true_probabilities: Estimated true probabilities
        kelly_fraction: Fraction of Kelly to use (0.25 = quarter Kelly)
        
    Returns:
        List of recommended stakes
    """
    stakes = []
    
    for odds, true_prob in zip(decimal_odds_list, true_probabilities):
        # Kelly formula: f = (bp - q) / b
        # where b = odds - 1, p = true prob, q = 1 - p
        b = odds - 1
        p = true_prob
        q = 1 - p
        
        kelly_pct = max(0, (b * p - q) / b)
        fractional_kelly = kelly_pct * kelly_fraction
        
        stakes.append(bankroll * fractional_kelly)
    
    return stakes


def assess_execution_risk(
    liquidity_available: List[float],
    stakes_required: List[float]
) -> str:
    """Assess execution risk based on liquidity vs required stakes.
    
    Args:
        liquidity_available: Available liquidity for each leg
        stakes_required: Required stake for each leg
        
    Returns:
        Risk level: "low", "medium", or "high"
    """
    if not liquidity_available or not stakes_required:
        return "unknown"
    
    # Calculate liquidity ratios
    ratios = []
    for liq, stake in zip(liquidity_available, stakes_required):
        if stake <= 0:
            continue
        ratios.append(liq / stake)
    
    if not ratios:
        return "unknown"
    
    min_ratio = min(ratios)
    
    # Risk thresholds
    if min_ratio >= 10.0:
        return "low"
    elif min_ratio >= 3.0:
        return "medium"
    else:
        return "high"
