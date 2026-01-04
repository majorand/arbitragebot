"""Arbitrage package initialization."""

from arbitragebot.arbitrage.calculator import (
    is_arbitrage,
    calculate_arbitrage_percentage,
    allocate_stakes,
    calculate_kelly_stakes,
    assess_execution_risk,
    ArbitrageOpportunity,
    ArbitrageLeg,
)

__all__ = [
    "is_arbitrage",
    "calculate_arbitrage_percentage",
    "allocate_stakes",
    "calculate_kelly_stakes",
    "assess_execution_risk",
    "ArbitrageOpportunity",
    "ArbitrageLeg",
]
