"""
Five-layer canonical model for unified arbitrage detection.

Layer 1: Instrument     (What real-world fact is being resolved)
Layer 2: Outcome       (Binary/multi result states of the instrument)
Layer 3: Market Expr   (How providers package outcomes)
Layer 4: Event Context (When/where/metadata - optional for matching)
Layer 5: Provider List (Raw API objects)

Matching occurs at Layer 1+2, NOT at event/market layer.
This enables cross-provider aggregation regardless of phrasing.
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional


# ============================================================================
# Layer 1: INSTRUMENT (Real-world fact being resolved)
# ============================================================================

class InstrumentDomain(Enum):
    """Categories of instruments - normalized across providers."""
    # Sports (normalized)
    NFL = "nfl"
    NBA = "nba"
    MLB = "mlb"
    NHL = "nhl"
    SOCCER = "soccer"
    UFC = "ufc"
    TENNIS = "tennis"
    GOLF = "golf"
    ESPORTS = "esports"
    
    # Non-sports (preserved from Kalshi/Polymarket)
    POLITICS = "politics"
    CRYPTO = "crypto"
    FINANCE = "finance"
    ECONOMICS = "economics"
    CLIMATE = "climate"
    TECH = "tech"
    CULTURE = "culture"
    ENTERTAINMENT = "entertainment"
    WORLD = "world"
    ELECTIONS = "elections"
    
    # Fallback
    OTHER = "other"


# Category normalization maps
SPORTS_CATEGORY_MAP = {
    # Kalshi variations
    "pro football": InstrumentDomain.NFL,
    "pro basketball": InstrumentDomain.NBA,
    "pro baseball": InstrumentDomain.MLB,
    "pro hockey": InstrumentDomain.NHL,
    "football": InstrumentDomain.NFL,
    "basketball": InstrumentDomain.NBA,
    "baseball": InstrumentDomain.MLB,
    "hockey": InstrumentDomain.NHL,
    
    # Polymarket variations
    "nfl": InstrumentDomain.NFL,
    "nba": InstrumentDomain.NBA,
    "mlb": InstrumentDomain.MLB,
    "nhl": InstrumentDomain.NHL,
    "soccer": InstrumentDomain.SOCCER,
    "ufc": InstrumentDomain.UFC,
    "tennis": InstrumentDomain.TENNIS,
    "golf": InstrumentDomain.GOLF,
    "esports": InstrumentDomain.ESPORTS,
    
    # ESPN variations
    "ncaaf": InstrumentDomain.NFL,  # College football still maps to NFL domain
    "ncaab": InstrumentDomain.NBA,  # College basketball maps to NBA domain
}

NON_SPORTS_CATEGORY_MAP = {
    # Shared Kalshi/Polymarket categories (preserve as-is)
    "politics": InstrumentDomain.POLITICS,
    "crypto": InstrumentDomain.CRYPTO,
    "finance": InstrumentDomain.FINANCE,
    "economics": InstrumentDomain.ECONOMICS,
    "climate": InstrumentDomain.CLIMATE,
    "tech": InstrumentDomain.TECH,
    "culture": InstrumentDomain.CULTURE,
    "entertainment": InstrumentDomain.ENTERTAINMENT,
    "world": InstrumentDomain.WORLD,
    "elections": InstrumentDomain.ELECTIONS,
    
    # Aliases
    "climate & science": InstrumentDomain.CLIMATE,
    "tech & science": InstrumentDomain.TECH,
    "geopolitics": InstrumentDomain.WORLD,
}


def normalize_category(category_str: str) -> InstrumentDomain:
    """Normalize category string to canonical domain.
    
    Args:
        category_str: Raw category from provider (e.g., "Pro Football", "NFL", "Politics")
        
    Returns:
        Normalized InstrumentDomain enum
        
    Examples:
        normalize_category("Pro Football") -> InstrumentDomain.NFL
        normalize_category("NFL") -> InstrumentDomain.NFL
        normalize_category("Politics") -> InstrumentDomain.POLITICS
    """
    normalized = category_str.lower().strip()
    
    # Check sports map first
    if normalized in SPORTS_CATEGORY_MAP:
        return SPORTS_CATEGORY_MAP[normalized]
    
    # Check non-sports map
    if normalized in NON_SPORTS_CATEGORY_MAP:
        return NON_SPORTS_CATEGORY_MAP[normalized]
    
    # Fallback
    return InstrumentDomain.OTHER


@dataclass
class CanonicalInstrument:
    """
    The fundamental real-world fact being resolved.
    
    Example: "Jacksonville Jaguars win Super Bowl LVII"
    
    This is domain-independent, provider-independent, and phrasing-independent.
    """
    instrument_id: str                    # SHA256 hash for determinism
    domain: InstrumentDomain             # Category (sports, politics, etc.)
    subject: str                         # The entity being measured
    predicate: str                       # The condition being measured
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    description: str = ""
    
    @staticmethod
    def compute_id(domain: InstrumentDomain, subject: str, predicate: str) -> str:
        """Generate deterministic instrument ID.
        
        Examples:
            nfl|jacksonville_jaguars_vs_kansas_city_chiefs|winner
            politics|biden|says_super_bowl_during_sotu
            crypto|bitcoin|exceeds_100k_by_eoy
        """
        # Normalize inputs
        domain_norm = domain.value if isinstance(domain, InstrumentDomain) else str(domain).lower()
        subject_norm = subject.lower().replace(" ", "_")
        predicate_norm = predicate.lower().replace(" ", "_")
        
        key = f"{domain_norm}|{subject_norm}|{predicate_norm}"
        return hashlib.sha256(key.encode()).hexdigest()


# ============================================================================
# Layer 2: OUTCOME (Binary or multi-state results)
# ============================================================================

class OutcomeResolution(Enum):
    """Standard outcome types."""
    BINARY = "binary"              # YES/NO
    BINARY_INVERSE = "binary_inverse"  # NO/YES (negation)
    MONEYLINE = "moneyline"        # HOME/AWAY
    TERNARY = "ternary"            # HOME/AWAY/DRAW
    MULTI = "multi"                # 3+ outcomes


@dataclass
class CanonicalOutcomeState:
    """One possible resolution state for an outcome.
    
    Example: YES resolves to True, NO resolves to False.
    """
    state_id: str                  # "YES", "NO", "JAGUARS", "CHIEFS", "DRAW"
    display_name: str              # "Yes", "Jacksonville Jaguars", "Over"
    resolves_to: bool              # True=instrument true, False=instrument false


@dataclass
class CanonicalOutcome:
    """
    Complete outcome definition for an instrument.
    
    Example: Jaguars Super Bowl instrument has:
      - State: YES (Jaguars win) → resolves_to=True
      - State: NO  (Jaguars lose) → resolves_to=False
    """
    outcome_id: str                # SHA256 of (instrument_id + outcome_type)
    instrument_id: str             # References Layer 1
    outcome_type: OutcomeResolution
    states: List[CanonicalOutcomeState] = field(default_factory=list)
    
    @staticmethod
    def compute_id(instrument_id: str, outcome_type: str) -> str:
        """Generate deterministic outcome ID."""
        key = f"{instrument_id}|{outcome_type}"
        return hashlib.sha256(key.encode()).hexdigest()


# ============================================================================
# Layer 3: MARKET EXPRESSION (How providers package outcomes)
# ============================================================================

class MarketExpressionType(Enum):
    """Canonical market types."""
    MONEYLINE = "moneyline"        # American odds on direct winner
    SPREAD = "spread"              # Point spread
    TOTAL = "total"                # Over/Under total score
    YES_NO = "yes_no"              # Binary yes/no contract
    BINARY = "binary"              # Generic binary
    FUTURES = "futures"            # Season/tournament outcome


@dataclass
class CanonicalMarketExpression:
    """
    How a provider packages an outcome for trading.
    
    Examples:
      - ESPN: Moneyline (HOME/AWAY odds)
      - Polymarket: Yes/No (probability market)
      - Kalshi: Binary (contract)
      - DraftKings: Spread -2.5 (derivative)
    
    KEY POINT: Different expressions can map to same outcome!
    """
    market_expr_id: str            # SHA256 of (outcome_id + expr_type + line)
    outcome_id: str                # References Layer 2
    expression_type: MarketExpressionType
    line: Optional[float] = None   # For spread/total (2.5, -110, etc.)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @staticmethod
    def compute_id(outcome_id: str, expr_type: str, line: Optional[float] = None) -> str:
        """Generate deterministic market expression ID."""
        line_str = f"|{line}" if line is not None else ""
        key = f"{outcome_id}|{expr_type}{line_str}"
        return hashlib.sha256(key.encode()).hexdigest()


# ============================================================================
# Layer 4: EVENT CONTEXT (When/where - metadata, NOT for matching)
# ============================================================================

@dataclass
class CanonicalEventContext:
    """
    Contextual metadata about when/where instrument resolves.
    
    This is for UI display and confidence scoring ONLY.
    NOT required for matching.
    
    Examples:
      - Super Bowl LVII, Feb 11, 2026, Jaguars vs Chiefs
      - Biden SOTU, Feb 4, 2026
      - Rihanna Halftime, Feb 11, 2026
    """
    context_id: str                # SHA256 of (instrument_id + event_date + location)
    instrument_id: str
    
    # Event details (all optional - used for UI/confidence)
    event_name: Optional[str] = None
    event_date: Optional[datetime] = None
    location: Optional[str] = None
    participants: List[str] = field(default_factory=list)
    league: Optional[str] = None
    
    @staticmethod
    def compute_id(instrument_id: str, event_date: Optional[datetime] = None,
                   location: Optional[str] = None) -> str:
        """Generate deterministic context ID."""
        date_str = event_date.isoformat() if event_date else "unknown"
        location_norm = (location or "unknown").lower().replace(" ", "_")
        key = f"{instrument_id}|{date_str}|{location_norm}"
        return hashlib.sha256(key.encode()).hexdigest()


# ============================================================================
# Layer 5: PROVIDER LISTING (Raw API objects - never used for matching)
# ============================================================================

@dataclass
class CanonicalProviderListing:
    """
    Raw API object from a provider.
    
    This is for bookkeeping, execution, and reference ONLY.
    Never participates in matching logic.
    """
    listing_id: str                # Provider's internal ID
    provider_name: str             # "espn", "kalshi", "polymarket"
    
    # References to upper layers
    market_expr_id: str            # Layer 3
    outcome_id: str                # Layer 2
    instrument_id: str             # Layer 1
    context_id: str                # Layer 4
    
    # Price information
    price: float                   # Provider's quoted price
    price_format: str              # "decimal", "american", "cents", "probability"
    implied_probability: float     # Normalized to 0-1
    
    # Metadata
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    raw_api_object: Dict = field(default_factory=dict)  # Full original data


# ============================================================================
# Aggregated Cross-Provider View (Output of aggregation)
# ============================================================================

@dataclass
class AggregatedInstrumentView:
    """
    The view presented to the arbitrage detector.
    
    One row per Instrument, with best prices from all providers.
    """
    instrument: CanonicalInstrument
    outcome: CanonicalOutcome
    context: Optional[CanonicalEventContext] = None
    
    # Prices per outcome state, grouped by provider
    # {state_id: {provider: CanonicalProviderListing}}
    prices_by_state: Dict[str, Dict[str, CanonicalProviderListing]] = field(
        default_factory=dict
    )
    
    # Cross-provider metadata
    providers: List[str] = field(default_factory=list)  # Unique providers offering this
    max_providers: int = 0                              # How many could theoretically offer it
    
    # Quality metrics
    confidence_score: float = 0.0                       # 0-1 from Layer 4 matching
    outcome_count: int = 0                              # How many outcome states have prices
    
    def best_price_for_state(self, state_id: str) -> Optional[tuple[str, float]]:
        """Return (provider, price) for best price on a state."""
        if state_id not in self.prices_by_state:
            return None
        
        prices = self.prices_by_state[state_id]
        if not prices:
            return None
        
        # For arbitrage: lower price = better value
        # Return provider with minimum price
        best_provider = min(prices.items(), key=lambda x: x[1].price)
        return (best_provider[0], best_provider[1].price)
