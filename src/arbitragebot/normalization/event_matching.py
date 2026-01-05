"""Event matching engine that finds equivalent events across providers."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from arbitragebot.normalization.schemas import CanonicalEvent, Sport

LOGGER = logging.getLogger(__name__)


class EventMatcher:
    """Rule-based event matching across providers."""
    
    # Matching thresholds
    TIME_WINDOW_MINUTES = 15  # Events must be within 15 minutes of each other
    TEAM_NAME_SIMILARITY = 0.7  # Fuzzy match threshold (0-1)
    
    def __init__(self):
        """Initialize the event matcher."""
        pass
    
    def match_events(self, events_by_provider: Dict[str, List[CanonicalEvent]]) -> List[List[CanonicalEvent]]:
        """Match equivalent events across providers.
        
        Args:
            events_by_provider: Dict mapping provider name → list of events
            
        Returns:
            List of matched event groups (each group = same event from different providers)
        """
        matched_groups = []
        seen_event_ids = set()
        
        # Sort providers to prefer ESPN as anchor
        provider_order = [p for p in ["espn", "kalshi", "polymarket"] if p in events_by_provider]
        
        # For each provider in order
        for provider in provider_order:
            events = events_by_provider.get(provider, [])
            
            for event in events:
                if event.event_id in seen_event_ids:
                    continue
                
                # Try to find matching events in other providers
                matched_group = [event]
                seen_event_ids.add(event.event_id)
                
                for other_provider in provider_order:
                    if other_provider == provider:
                        continue
                    
                    other_events = events_by_provider.get(other_provider, [])
                    
                    for other_event in other_events:
                        if other_event.event_id in seen_event_ids:
                            continue
                        
                        if self._events_match(event, other_event):
                            matched_group.append(other_event)
                            seen_event_ids.add(other_event.event_id)
                            break  # Only one match per provider
                
                # Only include groups with 2+ providers
                if len(matched_group) >= 2:
                    matched_groups.append(matched_group)
        
        return matched_groups
    
    def _events_match(self, event1: CanonicalEvent, event2: CanonicalEvent) -> bool:
        """Check if two events are the same using rule-based matching.
        
        Rules (in order):
        1. Same sport
        2. Same league (or close enough)
        3. Start times within ±15 minutes
        4. Team names match (with fuzzy matching)
        """
        
        # Rule 1: Same sport
        if event1.sport != event2.sport:
            return False
        
        # Rule 2: Same league or acceptable variation
        # (ESPN, Kalshi, and Polymarket all handle same league differently)
        # For now, accept if both are sports or both are same category
        
        # Rule 3: Start times within window
        # Handle both naive and aware datetimes
        try:
            # If one is aware and one is naive, make them comparable
            dt1 = event1.start_time
            dt2 = event2.start_time
            
            # Convert both to naive UTC for comparison
            if dt1.tzinfo is not None:
                dt1 = dt1.replace(tzinfo=None)
            if dt2.tzinfo is not None:
                dt2 = dt2.replace(tzinfo=None)
            
            time_diff = abs((dt1 - dt2).total_seconds())
            if time_diff > (self.TIME_WINDOW_MINUTES * 60):
                return False
        except (TypeError, AttributeError):
            # If comparison fails, skip time check
            pass
        
        # Rule 4: Team name matching
        # Allow either (A vs B) or (B vs A) ordering
        return (
            self._teams_match(event1.home_team, event2.home_team) and
            self._teams_match(event1.away_team, event2.away_team)
        ) or (
            self._teams_match(event1.home_team, event2.away_team) and
            self._teams_match(event1.away_team, event2.home_team)
        )
    
    def _teams_match(self, team1: str, team2: str) -> bool:
        """Check if two team names refer to the same team.
        
        Uses Levenshtein similarity as fallback.
        """
        if not team1 or not team2:
            return False
        
        t1 = team1.lower().strip()
        t2 = team2.lower().strip()
        
        # Exact match
        if t1 == t2:
            return True
        
        # Check if one is abbreviation of other
        if t1 in t2 or t2 in t1:
            return True
        
        # Fuzzy string matching
        similarity = SequenceMatcher(None, t1, t2).ratio()
        return similarity >= self.TEAM_NAME_SIMILARITY


class MatchedEventSet:
    """Collection of matched events across providers."""
    
    def __init__(self, events: List[CanonicalEvent]):
        """Initialize with matched events.
        
        Args:
            events: List of CanonicalEvent objects (same event from different providers)
        """
        if not events:
            raise ValueError("Must provide at least one event")
        
        # Use first event as canonical reference
        self.canonical_event = events[0]
        self.all_events = events
        self.events_by_provider = {
            event.provider_event_ids.get(provider, ""): event
            for event in events
            for provider in event.provider_event_ids.keys()
        }
        
        # Create merged event ID
        provider_ids = " | ".join(
            f"{provider}:{eid}"
            for provider, eid in self.canonical_event.provider_event_ids.items()
        )
        self.matched_id = f"matched_{provider_ids}"
    
    def display_name(self) -> str:
        """Human-readable matched event name."""
        return self.canonical_event.display_name()
    
    def get_providers(self) -> list[str]:
        """List of providers represented in this match."""
        providers = set()
        for event in self.all_events:
            providers.update(event.provider_event_ids.keys())
        return sorted(providers)
    
    def has_provider(self, provider: str) -> bool:
        """Check if provider is represented."""
        return any(provider in e.provider_event_ids for e in self.all_events)
