"""Canonical schemas for normalized odds across all providers.

This module defines the unified Event-Market-Outcome schema that all providers
are normalized into, along with enums for deterministic type mapping.
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional


class Sport(Enum):
    """Canonical sport types."""
    NFL = "nfl"
    NBA = "nba"
    MLB = "mlb"
    NHL = "nhl"
    NCAAF = "ncaaf"
    NCAAB = "ncaab"
    SOCCER = "soccer"
    TENNIS = "tennis"
    MMA = "mma"
    BOXING = "boxing"
    POLITICS = "politics"
    WEATHER = "weather"
    MACRO = "macro"
    CRYPTO = "crypto"
    ESPORTS = "esports"
    OTHER = "other"


class MarketType(Enum):
    """Canonical market types across providers."""
    MONEYLINE = "moneyline"      # Who wins (3-way for soccer)
    SPREAD = "spread"             # Point spread
    TOTAL = "total"               # Over/under total points
    YES_NO = "yes_no"             # Binary yes/no (Kalshi, Fanatics)
    PROP = "prop"                 # Player/game prop


class OutcomeType(Enum):
    """Canonical outcome types."""
    HOME = "home"
    AWAY = "away"
    YES = "yes"
    NO = "no"
    OVER = "over"
    UNDER = "under"
    DRAW = "draw"  # For soccer


@dataclass
class CanonicalOutcome:
    """A single outcome within a market."""
    outcome_type: OutcomeType
    title: str                      # "YES", "DET", "OVER 45.5", etc.
    implied_probability: float      # 0.0-1.0 normalized probability
    price: float                    # Original price (decimal, american, or cents)
    provider_outcome_id: str        # Provider's internal ID
    
    def __post_init__(self):
        """Validate probability range."""
        if not (0.0 <= self.implied_probability <= 1.0):
            raise ValueError(f"Probability must be 0-1, got {self.implied_probability}")


@dataclass
class CanonicalMarket:
    """A matched market across one or more providers."""
    market_id: str                  # Unique across canon
    market_type: MarketType
    line: Optional[float] = None    # For spreads/totals: -2.5, 45.5, etc.
    outcomes: List[CanonicalOutcome] = field(default_factory=list)
    
    # Provider-specific IDs for this market
    provider_market_ids: Dict[str, str] = field(default_factory=dict)
    
    def sum_implied_probabilities(self) -> float:
        """Sum of all outcome implied probabilities (should be ~1.0)."""
        return sum(o.implied_probability for o in self.outcomes)


@dataclass
class CanonicalEvent:
    """A matched event across one or more providers."""
    event_id: str                   # Unique canonical ID
    sport: Sport
    league: str                     # "NFL", "Premier League", "UFC", etc.
    home_team: str                  # Participant 1
    away_team: str                  # Participant 2
    start_time: datetime

    # Human-readable title/question (critical for YES/NO markets)
    event_name: str = ""
    
    markets: List[CanonicalMarket] = field(default_factory=list)
    
    # Provider-specific IDs for this event
    provider_event_ids: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def display_name(self) -> str:
        """Human-readable event name."""
        if self.event_name:
            return self.event_name
        return f"{self.home_team} @ {self.away_team}"


@dataclass
class ArbitrageOpportunitySingle:
    """Single arbitrage opportunity (one bet)."""
    provider: str
    outcome: CanonicalOutcome
    stake: float
    expected_payout: float
    
    
@dataclass
class DetectedArbitrage:
    """Complete arbitrage opportunity with all legs."""
    event_id: str
    event_name: str
    sport: Sport
    market_type: MarketType
    market_id: str
    
    # Arbitrage metrics
    implied_probability_sum: float  # e.g., 0.97 (3% edge)
    arbitrage_percentage: float     # e.g., 0.03 (3%)
    roi_percentage: float           # e.g., 3.1% actual ROI after math
    expected_profit: float          # $ profit on $100 stake
    
    # The bets
    legs: List[ArbitrageOpportunitySingle]
    
    # Risk assessment
    execution_risk: str             # "low", "medium", "high"
    notes: str = ""


# Provider name constants
PROVIDER_KALSHI = "kalshi"
PROVIDER_FANATICS = "fanatics"
PROVIDER_ESPN = "espn"
PROVIDER_FANDUEL = "fanduel"

CANONICAL_PROVIDERS = {PROVIDER_KALSHI, PROVIDER_FANATICS, PROVIDER_ESPN}
