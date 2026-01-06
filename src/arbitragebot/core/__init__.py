"""Core arbitrage detection components."""

from arbitragebot.core.instruments import (
    Instrument,
    InstrumentExtractor,
    PredicateType,
    TEAM_ALIASES,
    OUTCOME_MAP,
)

__all__ = [
    "Instrument",
    "InstrumentExtractor",
    "PredicateType",
    "TEAM_ALIASES",
    "OUTCOME_MAP",
]
