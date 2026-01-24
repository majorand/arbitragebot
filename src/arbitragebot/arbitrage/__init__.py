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

from arbitragebot.arbitrage.detector import (
    ArbitrageDetector,
    detect_arbitrage_opportunities,
    ArbitrageOpportunity as SingleLegArbitrageOpportunity,
    ArbitrageLeg as SingleLegArbitrageLeg,
)

__all__ = [
    "is_arbitrage",
    "calculate_arbitrage_percentage",
    "allocate_stakes",
    "calculate_kelly_stakes",
    "assess_execution_risk",
    "ArbitrageOpportunity",
    "ArbitrageLeg",
    "ArbitrageDetector",
    "detect_arbitrage_opportunities",
    "SingleLegArbitrageOpportunity",
    "SingleLegArbitrageLeg",
]
