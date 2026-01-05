"""Deterministic mapping tables for provider-specific types to canonical types."""

from arbitragebot.normalization.schemas import Sport, MarketType, OutcomeType


# =====================================================
# MARKET TYPE MAPPING TABLES
# =====================================================

ESPN_MARKET_TYPE_MAP = {
    "win": MarketType.MONEYLINE,
    "spread": MarketType.SPREAD,
    "over_under": MarketType.TOTAL,
    "moneyline": MarketType.MONEYLINE,
    "total": MarketType.TOTAL,
}

KALSHI_MARKET_TYPE_MAP = {
    "YES_NO": MarketType.YES_NO,
    "BINARY": MarketType.YES_NO,
}

POLYMARKET_MARKET_TYPE_MAP = {
    "binary": MarketType.YES_NO,
    "categorical": MarketType.YES_NO,  # Treat as YES_NO for now
}

FANDUEL_MARKET_TYPE_MAP = {
    "MONEYLINE": MarketType.MONEYLINE,
    "SPREAD": MarketType.SPREAD,
    "TOTAL": MarketType.TOTAL,
}


# =====================================================
# SPORT MAPPING TABLES
# =====================================================

ESPN_SPORT_MAP = {
    "football": Sport.NFL,
    "basketball": Sport.NBA,
    "baseball": Sport.MLB,
    "hockey": Sport.NHL,
    "ncf": Sport.NCAAF,
    "ncb": Sport.NCAAB,
    "soccer": Sport.SOCCER,
    "tennis": Sport.TENNIS,
    "mma": Sport.MMA,
    "boxing": Sport.BOXING,
}

KALSHI_SPORT_MAP = {
    "sports": Sport.NFL,
    "politics": Sport.POLITICS,
    "weather": Sport.WEATHER,
    "economy": Sport.MACRO,
    "crypto": Sport.CRYPTO,
}

POLYMARKET_SPORT_MAP = {
    "nfl": Sport.NFL,
    "nba": Sport.NBA,
    "mlb": Sport.MLB,
    "nhl": Sport.NHL,
    "ncaaf": Sport.NCAAF,
    "ncaab": Sport.NCAAB,
    "soccer": Sport.SOCCER,
    "tennis": Sport.TENNIS,
    "mma": Sport.MMA,
    "boxing": Sport.BOXING,
    "politics": Sport.POLITICS,
    "crypto": Sport.CRYPTO,
}


# =====================================================
# OUTCOME TYPE MAPPING
# =====================================================

def map_outcome_type(market_type: MarketType, outcome_str: str) -> OutcomeType:
    """Map outcome string to canonical outcome type based on market type."""
    outcome_lower = outcome_str.lower().strip()
    
    if market_type == MarketType.YES_NO:
        if "yes" in outcome_lower:
            return OutcomeType.YES
        elif "no" in outcome_lower:
            return OutcomeType.NO
        else:
            # Treat ambiguous as YES (will be matched with NO)
            return OutcomeType.YES
    
    elif market_type == MarketType.MONEYLINE:
        if "home" in outcome_lower or "win" in outcome_lower:
            return OutcomeType.HOME
        elif "away" in outcome_lower:
            return OutcomeType.AWAY
        elif "draw" in outcome_lower or "tie" in outcome_lower:
            return OutcomeType.DRAW
        else:
            return OutcomeType.HOME
    
    elif market_type == MarketType.SPREAD:
        return OutcomeType.HOME if "+" in outcome_str else OutcomeType.AWAY
    
    elif market_type == MarketType.TOTAL:
        if "over" in outcome_lower:
            return OutcomeType.OVER
        elif "under" in outcome_lower:
            return OutcomeType.UNDER
        else:
            return OutcomeType.OVER
    
    return OutcomeType.YES


# =====================================================
# TEAM NAME NORMALIZATION
# =====================================================

TEAM_ALIAS_MAP = {
    # NFL
    "chiefs": "Kansas City",
    "kc": "Kansas City",
    "eagles": "Philadelphia",
    "phi": "Philadelphia",
    "49ers": "San Francisco",
    "sf": "San Francisco",
    "ravens": "Baltimore",
    "bal": "Baltimore",
    "patriots": "New England",
    "ne": "New England",
    "cowboys": "Dallas",
    "dal": "Dallas",
    "seahawks": "Seattle",
    "sea": "Seattle",
    "packers": "Green Bay",
    "gb": "Green Bay",
    "steelers": "Pittsburgh",
    "pit": "Pittsburgh",
    "bengals": "Cincinnati",
    "cin": "Cincinnati",
    "browns": "Cleveland",
    "cle": "Cleveland",
    "lions": "Detroit",
    "det": "Detroit",
    "vikings": "Minnesota",
    "min": "Minnesota",
    "bears": "Chicago",
    "chi": "Chicago",
    "texans": "Houston",
    "hou": "Houston",
    "colts": "Indianapolis",
    "ind": "Indianapolis",
    "titans": "Tennessee",
    "ten": "Tennessee",
    "jaguars": "Jacksonville",
    "jax": "Jacksonville",
    "dolphins": "Miami",
    "mia": "Miami",
    "panthers": "Carolina",
    "car": "Carolina",
    "saints": "New Orleans",
    "no": "New Orleans",
    "buccaneers": "Tampa Bay",
    "tb": "Tampa Bay",
    "falcons": "Atlanta",
    "atl": "Atlanta",
    "rams": "Los Angeles",
    "la": "Los Angeles",
    "cardinals": "Arizona",
    "ari": "Arizona",
    "chargers": "Los Angeles",
    "bolts": "Los Angeles",
    "broncos": "Denver",
    "den": "Denver",
    "raiders": "Las Vegas",
    "lv": "Las Vegas",
    
    # NBA
    "lakers": "Los Angeles Lakers",
    "celtics": "Boston Celtics",
    "warriors": "Golden State Warriors",
    "heat": "Miami Heat",
    "knicks": "New York Knicks",
    "suns": "Phoenix Suns",
    "bucks": "Milwaukee Bucks",
    "nets": "Brooklyn Nets",
    "mavericks": "Dallas Mavericks",
    "nuggets": "Denver Nuggets",
    
    # Add more as needed
}


def normalize_team_name(team_str: str) -> str:
    """Normalize team name to canonical form."""
    if not team_str:
        return ""
    
    # Try exact match first
    key = team_str.lower().strip()
    if key in TEAM_ALIAS_MAP:
        return TEAM_ALIAS_MAP[key]
    
    # Try abbreviation match (2-3 chars)
    if len(key) <= 3 and key in TEAM_ALIAS_MAP:
        return TEAM_ALIAS_MAP[key]
    
    # Return original if no match
    return team_str
