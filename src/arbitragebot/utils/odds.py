"""Odds conversion utilities for sports betting arbitrage.

Handles conversions between:
- American odds (e.g., -110, +150)
- Decimal odds (e.g., 1.91, 2.50)
- Implied probability (e.g., 0.524, 0.400)
"""

from __future__ import annotations
from typing import Tuple


def american_to_decimal(american_odds: float) -> float:
    """Convert American odds to decimal format.
    
    Args:
        american_odds: American odds (e.g., -110, +150)
        
    Returns:
        Decimal odds (e.g., 1.91, 2.50)
    """
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1


def decimal_to_american(decimal_odds: float) -> float:
    """Convert decimal odds to American format.
    
    Args:
        decimal_odds: Decimal odds (e.g., 1.91, 2.50)
        
    Returns:
        American odds (e.g., -110, +150)
    """
    if decimal_odds >= 2.0:
        return (decimal_odds - 1) * 100
    else:
        return -100 / (decimal_odds - 1)


def decimal_to_probability(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability.
    
    Args:
        decimal_odds: Decimal odds (e.g., 1.91)
        
    Returns:
        Implied probability (e.g., 0.524)
    """
    if decimal_odds <= 0:
        return 0.0
    return 1 / decimal_odds


def probability_to_decimal(probability: float) -> float:
    """Convert implied probability to decimal odds.
    
    Args:
        probability: Implied probability (0.0 to 1.0)
        
    Returns:
        Decimal odds
    """
    if probability <= 0 or probability >= 1:
        return 1.0
    return 1 / probability


def american_to_probability(american_odds: float) -> float:
    """Convert American odds to implied probability.
    
    Args:
        american_odds: American odds (e.g., -110)
        
    Returns:
        Implied probability (e.g., 0.524)
    """
    decimal = american_to_decimal(american_odds)
    return decimal_to_probability(decimal)


def remove_juice(prob_a: float, prob_b: float) -> Tuple[float, float]:
    """Remove bookmaker juice/vig to get true probabilities.
    
    When two-way market probabilities sum > 1.0, this removes the overround.
    
    Args:
        prob_a: Implied probability for outcome A
        prob_b: Implied probability for outcome B
        
    Returns:
        Tuple of (true_prob_a, true_prob_b) summing to 1.0
    """
    total = prob_a + prob_b
    if total <= 0:
        return (0.5, 0.5)
    return (prob_a / total, prob_b / total)


def calculate_vig(decimal_odds_list: list[float]) -> float:
    """Calculate bookmaker vig/juice percentage.
    
    Args:
        decimal_odds_list: List of decimal odds for all outcomes
        
    Returns:
        Vig percentage (e.g., 0.047 for 4.7% vig)
    """
    total_prob = sum(1/odds for odds in decimal_odds_list if odds > 0)
    return max(0, total_prob - 1.0)
