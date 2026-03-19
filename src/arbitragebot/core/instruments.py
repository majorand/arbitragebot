"""
Instrument-level extraction and matching for cross-provider arbitrage.

This module implements canonical instrument extraction that runs AFTER provider
normalization but BEFORE aggregation, ensuring all providers resolve to the same
instrument when pricing the same real-world outcome.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


# ============================================================================
# CANONICAL TEAM ALIASES (Sports-specific)
# ============================================================================

# Sport-specific alias tables. Keep NFL and NBA separate to avoid cross-sport
# collisions (e.g., "denver" means Broncos in NFL, Nuggets in NBA).

NFL_TEAM_ALIASES = {
    # Explicit directives
    "jax": "jacksonville_jaguars",
    "jaguars": "jacksonville_jaguars",
    "jacksonville": "jacksonville_jaguars",
    "chiefs": "kansas_city_chiefs",

    # NFL Teams (expanded)
    "kansas city": "kansas_city_chiefs",
    "kc": "kansas_city_chiefs",
    "ravens": "baltimore_ravens",
    "baltimore": "baltimore_ravens",
    "steelers": "pittsburgh_steelers",
    "pittsburgh": "pittsburgh_steelers",
    "bills": "buffalo_bills",
    "buffalo": "buffalo_bills",
    "dolphins": "miami_dolphins",
    "miami": "miami_dolphins",
    "patriots": "new_england_patriots",
    "new england": "new_england_patriots",
    "jets": "new_york_jets",
    "ny jets": "new_york_jets",
    "bengals": "cincinnati_bengals",
    "cincinnati": "cincinnati_bengals",
    "browns": "cleveland_browns",
    "cleveland": "cleveland_browns",
    "texans": "houston_texans",
    "houston": "houston_texans",
    "colts": "indianapolis_colts",
    "indianapolis": "indianapolis_colts",
    "titans": "tennessee_titans",
    "tennessee": "tennessee_titans",
    "broncos": "denver_broncos",
    "denver": "denver_broncos",
    "raiders": "las_vegas_raiders",
    "las vegas": "las_vegas_raiders",
    "chargers": "los_angeles_chargers",
    "la chargers": "los_angeles_chargers",
    "rams": "los_angeles_rams",
    "la rams": "los_angeles_rams",
    "49ers": "san_francisco_49ers",
    "san francisco": "san_francisco_49ers",
    "seahawks": "seattle_seahawks",
    "seattle": "seattle_seahawks",
    "cardinals": "arizona_cardinals",
    "arizona": "arizona_cardinals",
    "cowboys": "dallas_cowboys",
    "dallas": "dallas_cowboys",
    "eagles": "philadelphia_eagles",
    "philadelphia": "philadelphia_eagles",
    "giants": "new_york_giants",
    "ny giants": "new_york_giants",
    "packers": "green_bay_packers",
    "green bay": "green_bay_packers",
    "vikings": "minnesota_vikings",
    "minnesota": "minnesota_vikings",
    "lions": "detroit_lions",
    "detroit": "detroit_lions",
    "bears": "chicago_bears",
    "chicago": "chicago_bears",
    "saints": "new_orleans_saints",
    "new orleans": "new_orleans_saints",
    "falcons": "atlanta_falcons",
    "atlanta": "atlanta_falcons",
    "panthers": "carolina_panthers",
    "carolina": "carolina_panthers",
    "buccaneers": "tampa_bay_buccaneers",
    "tampa bay": "tampa_bay_buccaneers",
    "bucs": "tampa_bay_buccaneers",
}


NBA_TEAM_ALIASES = {
    "hawks": "atlanta_hawks",
    "atlanta": "atlanta_hawks",
    "celtics": "boston_celtics",
    "boston": "boston_celtics",
    "nets": "brooklyn_nets",
    "brooklyn": "brooklyn_nets",
    "hornets": "charlotte_hornets",
    "charlotte": "charlotte_hornets",
    "bulls": "chicago_bulls",
    "cavaliers": "cleveland_cavaliers",
    "cavs": "cleveland_cavaliers",
    "mavericks": "dallas_mavericks",
    "mavs": "dallas_mavericks",
    "nuggets": "denver_nuggets",
    "denver": "denver_nuggets",
    "pistons": "detroit_pistons",
    "detroit": "detroit_pistons",
    "warriors": "golden_state_warriors",
    "golden state": "golden_state_warriors",
    "rockets": "houston_rockets",
    "houston": "houston_rockets",
    "pacers": "indiana_pacers",
    "indiana": "indiana_pacers",
    "clippers": "los_angeles_clippers",
    "la clippers": "los_angeles_clippers",
    "lakers": "los_angeles_lakers",
    "la lakers": "los_angeles_lakers",
    "grizzlies": "memphis_grizzlies",
    "memphis": "memphis_grizzlies",
    "heat": "miami_heat",
    "miami": "miami_heat",
    "bucks": "milwaukee_bucks",
    "milwaukee": "milwaukee_bucks",
    "timberwolves": "minnesota_timberwolves",
    "wolves": "minnesota_timberwolves",
    "pelicans": "new_orleans_pelicans",
    "new orleans": "new_orleans_pelicans",
    "knicks": "new_york_knicks",
    "ny knicks": "new_york_knicks",
    "thunder": "oklahoma_city_thunder",
    "oklahoma city": "oklahoma_city_thunder",
    "okc": "oklahoma_city_thunder",
    "magic": "orlando_magic",
    "orlando": "orlando_magic",
    "76ers": "philadelphia_76ers",
    "sixers": "philadelphia_76ers",
    "philadelphia": "philadelphia_76ers",
    "suns": "phoenix_suns",
    "phoenix": "phoenix_suns",
    "trail blazers": "portland_trail_blazers",
    "blazers": "portland_trail_blazers",
    "portland": "portland_trail_blazers",
    "kings": "sacramento_kings",
    "sacramento": "sacramento_kings",
    "spurs": "san_antonio_spurs",
    "san antonio": "san_antonio_spurs",
    "raptors": "toronto_raptors",
    "toronto": "toronto_raptors",
    "jazz": "utah_jazz",
    "utah": "utah_jazz",
    "wizards": "washington_wizards",
    "washington": "washington_wizards",
}


SPORT_TEAM_ALIASES: Dict[str, Dict[str, str]] = {
    "nfl": NFL_TEAM_ALIASES,
    "nba": NBA_TEAM_ALIASES,
}

# Backward-compatible default (treat as NFL)
TEAM_ALIASES = NFL_TEAM_ALIASES


def _build_safe_unknown_aliases() -> Dict[str, str]:
    """Build a merged alias map for unknown sports domains.

    If an alias maps to different canonicals across sports (e.g., "denver"),
    drop it to avoid cross-sport collisions.
    """
    combined: Dict[str, str] = {}
    conflicts: Set[str] = set()

    for mapping in (NFL_TEAM_ALIASES, NBA_TEAM_ALIASES):
        for alias, canonical in mapping.items():
            if alias in conflicts:
                continue
            existing = combined.get(alias)
            if existing is None:
                combined[alias] = canonical
            elif existing != canonical:
                conflicts.add(alias)
                combined.pop(alias, None)

    return combined


UNKNOWN_SPORT_TEAM_ALIASES = _build_safe_unknown_aliases()


# ============================================================================
# CANONICAL PREDICATES
# ============================================================================

class PredicateType(Enum):
    """Canonical predicate types."""
    WIN_GAME = "win_game"
    WIN_SUPER_BOWL = "win_super_bowl"
    WIN_CHAMPIONSHIP = "win_championship"
    WIN_PLAYOFFS = "win_playoffs"
    COVER_SPREAD = "cover_spread"
    OVER_TOTAL = "over_total"
    # Player props
    PLAYER_POINTS_OVER = "player_points_over"
    PLAYER_POINTS_UNDER = "player_points_under"
    PLAYER_REBOUNDS_OVER = "player_rebounds_over"
    PLAYER_ASSISTS_OVER = "player_assists_over"
    PLAYER_PASSING_YARDS_OVER = "player_passing_yards_over"
    PLAYER_RECEIVING_YARDS_OVER = "player_receiving_yards_over"
    PLAYER_RUSHING_YARDS_OVER = "player_rushing_yards_over"
    # Totals
    GAME_TOTAL_OVER = "game_total_over"
    GAME_TOTAL_UNDER = "game_total_under"


PREDICATE_PATTERNS = {
    # Explicit directives
    "super bowl": PredicateType.WIN_SUPER_BOWL,
    "superbowl": PredicateType.WIN_SUPER_BOWL,
    "championship": PredicateType.WIN_CHAMPIONSHIP,
    # Defaults for win_game
    "moneyline": PredicateType.WIN_GAME,
    "win": PredicateType.WIN_GAME,
    "beat": PredicateType.WIN_GAME,
    # Spreads
    "cover": PredicateType.COVER_SPREAD,
    "spread": PredicateType.COVER_SPREAD,
    # Totals
    "over": PredicateType.GAME_TOTAL_OVER,
    "under": PredicateType.GAME_TOTAL_UNDER,
}


# ============================================================================
# OUTCOME NORMALIZATION
# ============================================================================

OUTCOME_MAP = {
    "YES": "true",
    "yes": "true",
    "Yes": "true",
    "NO": "false",
    "no": "false",
    "No": "false",
    "HOME": "true",
    "home": "true",
    "Home": "true",
    "AWAY": "false",
    "away": "false",
    "Away": "false",
    "1": "true",
    "2": "false",
}


# ============================================================================
# INSTRUMENT DATA MODEL
# ============================================================================

@dataclass
class Instrument:
    """
    A canonical instrument representing a real-world outcome.
    
    Instruments are provider-independent and represent what is being resolved,
    not how it's being asked or packaged.
    """
    instrument_id: str
    domain: str                      # sports, politics, culture
    subject: str                     # canonical entity (team/person)
    predicate: str                   # win_game, win_super_bowl
    context: Dict[str, any] = field(default_factory=dict)  # event name, league, date
    
    # Outcomes tracked on this instrument
    outcomes: Dict[str, Dict[str, float]] = field(default_factory=lambda: {"true": {}, "false": {}})
    
    @property
    def providers(self) -> Set[str]:
        """Get all providers pricing this instrument."""
        providers = set()
        for outcome_prices in self.outcomes.values():
            providers.update(outcome_prices.keys())
        return providers
    
    @property
    def has_arbitrage(self) -> bool:
        """Check if this instrument has cross-provider arbitrage opportunity."""
        if len(self.providers) < 2:
            return False
        
        if not self.outcomes.get("true") or not self.outcomes.get("false"):
            return False
        
        # Get best prices (lowest for buying)
        best_true = min(self.outcomes["true"].values()) if self.outcomes["true"] else float('inf')
        best_false = min(self.outcomes["false"].values()) if self.outcomes["false"] else float('inf')
        
        # Arbitrage exists if we can buy both outcomes for less than 1
        total_cost = best_true + best_false
        
        # Account for fees (assume 2% total)
        return total_cost < 0.98
    
    @property
    def roi(self) -> float:
        """Calculate return on investment percentage."""
        if not self.has_arbitrage:
            return 0.0
        
        best_true = min(self.outcomes["true"].values()) if self.outcomes["true"] else float('inf')
        best_false = min(self.outcomes["false"].values()) if self.outcomes["false"] else float('inf')
        
        total_cost = best_true + best_false
        return ((1.0 - total_cost) / total_cost) * 100


# ============================================================================
# INSTRUMENT EXTRACTOR
# ============================================================================

class InstrumentExtractor:
    """
    Extracts canonical instruments from normalized provider data.
    
    This runs AFTER provider normalization but BEFORE aggregation.
    """
    
    def __init__(self):
        self.instruments: Dict[str, Instrument] = {}
    
    def extract_subject(
        self,
        text: str,
        home_team: str = None,
        away_team: str = None,
        domain: str | None = None,
    ) -> Optional[str]:
        """
        Extract canonical subject from text.
        
        For sports: Returns team name in canonical form or player name.
        Returns None if subject cannot be determined.
        
        Args:
            text: Raw text from market title/question
            home_team: Structured home team (ESPN only)
            away_team: Structured away team (ESPN only)
            domain: Domain hint (nfl, nba, etc)
            
        Returns:
            Canonical subject or None
        """
        import logging
        logger = logging.getLogger(__name__)
        
        domain_norm = str(domain).lower().strip() if domain else ""

        # Try player prop first (more specific)
        player = self._extract_player_name(text)
        if player:
            logger.info(f"Text subject (player): '{player}' from text: '{text[:100]}'")
            return player

        # Try team matchup or single team
        # IMPORTANT: Do not fall back to NFL aliases for unknown leagues.
        # That creates bogus matches (e.g. NHL "Blackhawks" -> NFL "Bears").
        alias_map = SPORT_TEAM_ALIASES.get(domain_norm)

        # Reject placeholders early
        if text and re.search(r"\bmarket\b", text.lower()) and re.search(r"\bvs\b|\bv\.|@", text.lower()):
            # Common failure mode from normalizers: "... vs MARKET"
            return None

        # If we have structured team data, use it
        if home_team and away_team:
            # Normalize both teams
            home_canonical = self._normalize_team_name(home_team, alias_map)
            away_canonical = self._normalize_team_name(away_team, alias_map)
            
            # Return sorted pair for determinism
            teams = sorted([home_canonical, away_canonical])
            result = "_vs_".join(teams)
            logger.info(f"Structured subject: '{result}' from {home_team} vs {away_team}")
            return result
        
        # Otherwise extract from free text.
        # Prefer explicit matchup parsing over alias scanning.
        matchup = self._parse_matchup_from_text(text)
        if matchup:
            left_raw, right_raw = matchup
            left = self._normalize_team_name(left_raw, alias_map)
            right = self._normalize_team_name(right_raw, alias_map)
            teams = sorted([left, right])
            result = "_vs_".join(teams)
            logger.info(f"Text subject (parsed): '{result}' from text: '{text[:100]}'")
            return result

        # Fall back to alias scanning.
        # Only use unknown-domain alias scanning when the domain is truly unknown.
        text_normalized = self._normalize_text(text)
        if not alias_map and domain_norm in {"", "sports", "other"}:
            alias_map = UNKNOWN_SPORT_TEAM_ALIASES

        if not alias_map:
            # No alias map for this domain - try extracting a team name from
            # common phrases like "X wins by" or "Will X win"
            fallback = self._extract_team_from_phrase(text)
            if fallback:
                logger.info(f"Text subject (phrase): '{fallback}' from text: '{text[:100]}'")
                return fallback
            logger.warning(f"No subject found in text: '{text[:100]}'")
            return None
        
        found_teams: List[str] = []
        for alias, canonical in alias_map.items():
            # Match on word boundaries to reduce substring false positives
            if re.search(rf"\b{re.escape(alias)}\b", text_normalized):
                if canonical not in found_teams:
                    found_teams.append(canonical)
        
        if len(found_teams) >= 2:
            result = "_vs_".join(sorted(found_teams[:2]))
            logger.info(f"Text subject (multi): '{result}' from text: '{text[:100]}'")
            return result
        if len(found_teams) == 1:
            result = found_teams[0]
            logger.info(f"Text subject (single): '{result}' from text: '{text[:100]}'")
            return result

        # Last resort: extract team name from common phrases
        fallback = self._extract_team_from_phrase(text)
        if fallback:
            logger.info(f"Text subject (phrase fallback): '{fallback}' from text: '{text[:100]}'")
            return fallback

        logger.warning(f"No subject found in text: '{text[:100]}'")
        return None
    
    def _extract_team_from_phrase(self, text: str) -> Optional[str]:
        """Extract a team/entity name from common phrasing when no alias map matches.

        Patterns handled:
        - "X wins by over ..."  → X
        - "Will X win ..."      → X
        - "X to win ..."        → X
        - "X covers ..."        → X
        - "Over/Under N points" → game_total (no team)
        - "Over/Under N"        → game_total (no team, no keyword)
        """
        # Try team-based patterns first (more specific than bare totals)
        patterns = [
            r"(?:yes\s+)?([A-Z][a-zA-Z\s]+?)\s+wins?\b",
            r"Will\s+(?:the\s+)?([A-Z][a-zA-Z\s]+?)\s+win",
            r"([A-Z][a-zA-Z\s]+?)\s+to\s+win",
            r"([A-Z][a-zA-Z\s]+?)\s+covers?\b",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                name = m.group(1).strip()
                if name and len(name) > 1:
                    return name.lower().replace(" ", "_")

        # Handle totals (no team involved) - match with or without "points" keyword
        if re.search(r"\b(?:over|under)\s+[\d.]+", text, re.IGNORECASE):
            return "game_total"

        return None

    def _normalize_team_name(self, team: str, alias_map: Optional[Dict[str, str]]) -> str:
        """Normalize a team name to canonical form."""
        team_lower = team.lower().strip()
        
        # Check if already canonical
        if "_" in team_lower:
            if alias_map and team_lower in alias_map.values():
                return team_lower
            if team_lower in TEAM_ALIASES.values():
                return team_lower
        
        # Look up in aliases (if available)
        if alias_map:
            for alias, canonical in alias_map.items():
                if alias == team_lower:
                    return canonical
            for alias, canonical in alias_map.items():
                if re.search(rf"\b{re.escape(alias)}\b", team_lower):
                    return canonical
        
        # Fallback: snake_case the input
        return team_lower.replace(" ", "_")

    def _parse_matchup_from_text(self, text: str) -> Optional[tuple[str, str]]:
        """Parse a matchup from common sports title formats.

        Returns (left, right) if a clear two-team matchup is detected.
        """
        if not text:
            return None

        # Remove common league prefixes like "NBA:" and normalize separators.
        s = re.sub(r"^\s*[A-Z]{2,6}(?:\s+\w+)?\s*:\s*", "", str(text)).strip()
        s = re.sub(r"\s+", " ", s)

        # Prefer explicit separators
        for sep_pattern in [r"\s+vs\.?\s+", r"\s+v\.?\s+", r"\s+@\s+", r"\s+at\s+"]:
            parts = re.split(sep_pattern, s, flags=re.IGNORECASE)
            if len(parts) == 2:
                left = parts[0].strip(" -()[]")
                right = parts[1].strip(" -()[]")
                # Strip trailing dates like "2023-03-18" or "(02/09/2023)"
                right = re.sub(r"\b\d{4}-\d{2}-\d{2}\b.*$", "", right).strip()
                right = re.sub(r"\(\d{2}/\d{2}/\d{4}\)\s*$", "", right).strip()
                left = re.sub(r"\b\d{4}-\d{2}-\d{2}\b.*$", "", left).strip()
                left = re.sub(r"\(\d{2}/\d{2}/\d{4}\)\s*$", "", left).strip()

                if left and right and left.lower() != "market" and right.lower() != "market":
                    return (left, right)

        return None
    
    def _extract_player_name(self, text: str) -> Optional[str]:
        """
        Extract player name from text.
        
        Patterns:
        - "Devin Booker: 2+" → "devin_booker"
        - "Puka Nacua: 80+" → "puka_nacua"
        - "Matthew Stafford: 200+" → "matthew_stafford"
        
        Returns:
            Canonical player name or None
        """
        # Pattern: Capitalized Name(s): threshold
        match = re.search(r'([A-Z][a-z]+\s+[A-Z][a-z]+):\s*\d+', text)
        if match:
            name = match.group(1)
            return name.lower().replace(" ", "_")
        
        # Pattern: Single player name without threshold (less preferred)
        # Only match if it's a clear player name (capitalized)
        match = re.search(r'yes\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*$', text)
        if match:
            name = match.group(1)
            return name.lower().replace(" ", "_")
        
        return None
    
    def _extract_spread_info(self, text: str) -> Optional[tuple[str, float]]:
        """
        Extract spread amount from text.
        
        Patterns:
        - "Phoenix wins by over 3.5 Points" → ("cover_spread", 3.5)
        - "Michigan wins by over 15.5 Points" → ("cover_spread", 15.5)
        
        Returns:
            Tuple of (spread_type, amount) or None
        """
        # Pattern: "wins by over X.X" or "wins by X.X"
        match = re.search(r'wins?\s+by\s+(?:over|under)?\s*([\d.]+)', text, re.IGNORECASE)
        if match:
            try:
                amount = float(match.group(1))
                return ("cover_spread", amount)
            except ValueError:
                pass
        
        # Pattern: "covers X.X"
        match = re.search(r'covers?\s+([\d.]+)', text, re.IGNORECASE)
        if match:
            try:
                amount = float(match.group(1))
                return ("cover_spread", amount)
            except ValueError:
                pass
        
        return None
    
    def _extract_total_info(self, text: str) -> Optional[tuple[str, float]]:
        """
        Extract game total amount from text.
        
        Patterns:
        - "Over 228.5 points scored" → ("game_total", 228.5)
        - "Under 209.5 points" → ("game_total", 209.5)
        
        Returns:
            Tuple of (total_type, amount) or None
        """
        # Pattern: "Over/Under X.X points"
        match = re.search(r'(over|under)\s+([\d.]+)(?:\s+points)?', text, re.IGNORECASE)
        if match:
            try:
                amount = float(match.group(2))
                return ("game_total", amount)
            except ValueError:
                pass
        
        return None
    
    def extract_predicate(self, text: str, market_type: str = None) -> str:
        """
        Extract canonical predicate from text.
        
        Args:
            text: Raw text from market title/question
            market_type: Market type hint (moneyline, spread, player_prop, total, etc)
            
        Returns:
            Canonical predicate
        """
        text_lower = text.lower()
        
        # Explicit override: Super Bowl wins trump all other patterns
        if "super bowl" in text_lower or "superbowl" in text_lower:
            return PredicateType.WIN_SUPER_BOWL.value
        
        # Handle player props (specific patterns)
        if market_type and "player_prop" in market_type.lower():
            # Determine stat type from text
            if "passing" in text_lower and "yard" in text_lower:
                return PredicateType.PLAYER_PASSING_YARDS_OVER.value
            elif "receiving" in text_lower and "yard" in text_lower:
                return PredicateType.PLAYER_RECEIVING_YARDS_OVER.value
            elif "rushing" in text_lower and "yard" in text_lower:
                return PredicateType.PLAYER_RUSHING_YARDS_OVER.value
            elif "rebound" in text_lower:
                return PredicateType.PLAYER_REBOUNDS_OVER.value
            elif "assist" in text_lower:
                return PredicateType.PLAYER_ASSISTS_OVER.value
            else:
                # Default to points
                return PredicateType.PLAYER_POINTS_OVER.value
        
        # Handle totals
        if market_type and "total" in market_type.lower():
            if "over" in text_lower:
                return PredicateType.GAME_TOTAL_OVER.value
            elif "under" in text_lower:
                return PredicateType.GAME_TOTAL_UNDER.value
        
        # Handle spreads
        if market_type and ("spread" in market_type.lower() or "cover" in market_type.lower()):
            return PredicateType.COVER_SPREAD.value
        
        # Infer from text patterns (if no market_type hint)
        if ":" in text and re.search(r':\s*\d+', text):
            # Looks like player prop (e.g., "Booker: 25+")
            if "passing" in text_lower and "yard" in text_lower:
                return PredicateType.PLAYER_PASSING_YARDS_OVER.value
            elif "receiving" in text_lower and "yard" in text_lower:
                return PredicateType.PLAYER_RECEIVING_YARDS_OVER.value
            else:
                return PredicateType.PLAYER_POINTS_OVER.value
        
        if "over" in text_lower and "point" in text_lower:
            return PredicateType.GAME_TOTAL_OVER.value
        elif "under" in text_lower and "point" in text_lower:
            return PredicateType.GAME_TOTAL_UNDER.value
        
        if "wins by" in text_lower or "cover" in text_lower:
            return PredicateType.COVER_SPREAD.value
        
        # Check patterns in order of specificity
        for pattern, predicate_type in PREDICATE_PATTERNS.items():
            if pattern in text_lower:
                return predicate_type.value
        
        # Default based on market type
        if market_type and "moneyline" in market_type.lower():
            return PredicateType.WIN_GAME.value
        
        # Fallback
        return PredicateType.WIN_GAME.value
    
    def extract_instrument(self, 
                          domain: str,
                          text: str,
                          market_type: str = None,
                          home_team: str = None,
                          away_team: str = None,
                          event_name: str = None,
                          league: str = None,
                          event_date: str = None) -> Optional[Instrument]:
        """
        Extract a canonical instrument from market data.
        
        Args:
            domain: Domain (sports, politics, etc)
            text: Market title/question
            market_type: Market type (moneyline, spread, etc)
            home_team: Home team (if structured)
            away_team: Away team (if structured)
            event_name: Event name for context
            league: League for context
            event_date: Event date for context
            
        Returns:
            Instrument or None if extraction fails
        """
        # Extract subject
        subject = self.extract_subject(text, home_team, away_team, domain=domain)
        
        if subject is None:
            # Cannot determine subject - invalid instrument
            return None
        
        # Extract predicate
        predicate = self.extract_predicate(text, market_type)
        if predicate is None:
            return None

        # Enforce required assertions to avoid silent failures
        assert subject is not None, "Subject extraction failed"
        assert predicate is not None, "Predicate extraction failed"
        
        # Build instrument ID
        instrument_id = self._compute_instrument_id(domain, subject, predicate)
        
        # Check if we already have this instrument
        if instrument_id in self.instruments:
            return self.instruments[instrument_id]
        
        # Create new instrument
        instrument = Instrument(
            instrument_id=instrument_id,
            domain=domain,
            subject=subject,
            predicate=predicate,
            context={
                "event_name": event_name,
                "league": league,
                "event_date": event_date,
            }
        )
        
        self.instruments[instrument_id] = instrument
        return instrument

    def _normalize_text(self, text: str) -> str:
        """Lowercase and strip punctuation for reliable alias matching."""
        return re.sub(r"[^a-z0-9\s]", " ", text.lower())
    
    def _compute_instrument_id(self, domain: str, subject: str, predicate: str) -> str:
        """
        Compute deterministic instrument ID.
        
        Args:
            domain: Domain
            subject: Canonical subject
            predicate: Canonical predicate
            
        Returns:
            SHA256 hash
        """
        key = f"{domain}|{subject}|{predicate}"
        return hashlib.sha256(key.encode()).hexdigest()
    
    def add_outcome(self, 
                   instrument: Instrument,
                   outcome: str,
                   provider: str,
                   price: float) -> None:
        """
        Add an outcome price to an instrument.
        
        Args:
            instrument: The instrument
            outcome: Outcome (YES, NO, HOME, AWAY, etc)
            provider: Provider name
            price: Price/probability
        """
        # Normalize outcome
        normalized_outcome = OUTCOME_MAP.get(outcome, outcome.lower())
        
        if normalized_outcome not in ["true", "false"]:
            # Unknown outcome format
            return
        
        # Add to instrument
        instrument.outcomes[normalized_outcome][provider] = price
    
    def get_arbitrage_opportunities(self, min_roi: float = 0.5) -> List[Instrument]:
        """
        Get all instruments with arbitrage opportunities.
        
        Args:
            min_roi: Minimum ROI percentage
            
        Returns:
            List of instruments with arbitrage
        """
        opportunities = []
        
        for instrument in self.instruments.values():
            # Must have at least 2 providers
            if len(instrument.providers) < 2:
                continue
            
            # Must have both outcomes
            if not instrument.outcomes.get("true") or not instrument.outcomes.get("false"):
                continue
            
            # Check for arbitrage
            if instrument.has_arbitrage and instrument.roi >= min_roi:
                opportunities.append(instrument)
        
        # Sort by ROI descending
        opportunities.sort(key=lambda x: x.roi, reverse=True)
        
        return opportunities
    
    def extract_instruments_batch(self,
                                  domain: str,
                                  text: str,
                                  market_type: str = None,
                                  home_team: str = None,
                                  away_team: str = None,
                                  event_name: str = None,
                                  league: str = None,
                                  event_date: str = None) -> List[Instrument]:
        """
        Extract multiple instruments from comma-separated text.
        
        Some market data provides comma-separated values like:
        "yes Devin Booker: 2+,yes Devin Booker: 4+,yes Phoenix wins by over 3.5"
        
        This method splits and extracts each as a separate instrument.
        
        Args:
            domain: Domain (nba, nfl, etc)
            text: Comma-separated market text
            market_type: Market type hint
            home_team: Home team
            away_team: Away team
            event_name: Event name
            league: League
            event_date: Event date
            
        Returns:
            List of extracted instruments
        """
        instruments = []
        
        # Split on commas and extract each part
        parts = text.split(',')
        
        for part in parts:
            part_stripped = part.strip()
            if not part_stripped:
                continue
            
            # Remove "yes" / "no" prefix if present
            part_cleaned = re.sub(r'^(yes|no)\s+', '', part_stripped, flags=re.IGNORECASE)
            
            inst = self.extract_instrument(
                domain=domain,
                text=part_cleaned,
                market_type=market_type,
                home_team=home_team,
                away_team=away_team,
                event_name=event_name,
                league=league,
                event_date=event_date
            )
            
            if inst:
                instruments.append(inst)
        
        return instruments
    
    def validate_instrument(self, instrument: Instrument) -> bool:
        """
        Validate that an instrument is complete and ready for aggregation.
        
        Args:
            instrument: The instrument to validate
            
        Returns:
            True if valid
        """
        # Must have subject
        if not instrument.subject:
            return False
        
        # Must have predicate
        if not instrument.predicate:
            return False
        
        # Must have at least one outcome with at least one provider
        has_outcomes = False
        for outcome_prices in instrument.outcomes.values():
            if outcome_prices:
                has_outcomes = True
                break
        
        return has_outcomes
