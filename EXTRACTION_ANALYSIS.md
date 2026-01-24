# Subject Extraction Analysis

Generated: January 23, 2026

## Problem Statement

From recent logs, subject extraction is **failing for ~80% of market texts**, preventing arbitrage detection.

### Failing Examples (No Subject Found)
```
'yes Devin Booker: 2+,yes Devin Booker: 4+,yes Devin Booker: 30+,yes Phoenix wins by over 3.5 Points'
'yes Michigan wins by over 15.5 Points,yes Saint Louis wins by over 5.5 Points'
'yes Puka Nacua,yes Jaxon Smith-Njigba,yes RJ Harvey,yes Rhamondre Stevenson,yes Matthew Stafford: 2+'
'yes Kevin Durant: 2+,yes Alperen Sengun: 15+,yes Kevin Durant: 20+,yes CJ McCollum: 15+'
'no Over 228.5 points scored,yes Over 209.5 points scored,no Over 238.5 points scored'
'yes Cooper Kupp,yes Sam Darnold: 175+,yes Cooper Kupp: 3+'
```

### Working Examples (Extraction Successful)
```
'buffalo_bills_vs_jacksonville_jaguars' from text with Bills/Jaguars
'detroit_lions' from text with Detroit
'cleveland_browns' from text with Cleveland
'houston_texans' from text with Houston
'seattle_seahawks' from text with Seattle
```

## Root Causes

### 1. **Player Props Not Recognized**
Current: `InstrumentExtractor.extract_subject()` only handles **team matchups**.
- Player name extraction not implemented
- Props like "Devin Booker: 2+" are pure noise
- No "player_X_stat" domain or predicate types

Example:
```python
# FAILING:
text = "yes Devin Booker: 2+,yes Devin Booker: 4+,yes Devin Booker: 30+"
# Current logic: Looks for "vs" pattern or team aliases
# Result: None (no team names found)

# NEEDED:
text = "yes Devin Booker: 2+"
# Parse as: domain="nba", subject="devin_booker", predicate="points_over_2"
```

### 2. **Spread/Total Parsing Missing**
Current: Only "moneyline" mode implemented via `WIN_GAME` predicate.
- Spreads: "Michigan wins by over 15.5 Points" → no handler
- Totals: "Over 228.5 points scored" → no handler
- Player props: "Devin Booker: 30+" → no handler

### 3. **Comma-Separated Text**
Current: `_parse_matchup_from_text()` assumes single title per call.
- Data source returns comma-separated strings: "yes X,yes Y,no Z"
- Each comma-separated value should be parsed separately
- Current code tries to parse ALL as one matchup → fails

### 4. **Domain Not Passed**
- `extract_subject()` receives `domain=None` in many calls
- Falls back to `UNKNOWN_SPORT_TEAM_ALIASES` which drops aliases with collisions
- "Denver" could be Broncos (NFL) or Nuggets (NBA) - loses both

### 5. **Context Information Lost**
- Market source (ESPN, Kalshi, Fanatics) has metadata: league, sport, event date
- Current code ignores this when classifying

---

## Pattern Categories Found in Logs

### Category A: Team Matchups (WORKING) - ~15%
```
"buffalo_bills_vs_jacksonville_jaguars"
"detroit_lions"
"houston_texans"
"seattle_seahawks"
```
✅ Current logic handles these correctly.

### Category B: Player Props (FAILING) - ~50%
```
"yes Devin Booker: 2+"           → devin_booker POINTS_OVER_2
"yes Puka Nacua"                 → puka_nacua PLAYER_RECEIVING
"yes Matthew Stafford: 200+"     → matthew_stafford PASSING_YARDS_OVER_200
```
❌ Not recognized. No player domain/predicate.

### Category C: Game Spreads (FAILING) - ~20%
```
"yes Phoenix wins by over 3.5 Points"     → phoenix_suns COVER_SPREAD_3_5
"yes Michigan wins by over 15.5 Points"   → michigan_wolverines COVER_SPREAD_15_5
"no Detroit wins by over 4.5 Points"      → detroit_lions LOSES_OUTRIGHT
```
❌ Only "wins by" pattern recognized, not parsed into spread amount.

### Category D: Game Totals (FAILING) - ~10%
```
"no Over 228.5 points scored"  → GAME_TOTAL_228_5 (no team subject)
"yes Over 209.5 points scored" → GAME_TOTAL_209_5 (no team subject)
```
❌ No total extraction. "Over/Under" not in patterns.

### Category E: Unclear/Aggregates (FAILING) - ~5%
```
"yes Boston,yes Phoenix,yes SJ Sharks"  → Mixed, no pattern
"yes North Texas,yes Austin Peay,yes Appalachian St."  → Multi-team noise
```
❌ No clear subject, appears to be aggregated bet lists.

---

## Solution Approach

### Phase 1: Add Support for Core Pattern Types (This Sprint)

**1. Player Props Domain**
```python
# Add to PredicateType
POINTS_OVER = "points_over_X"
POINTS_UNDER = "points_under_X"
REBOUNDS_OVER = "rebounds_over_X"
ASSISTS_OVER = "assists_over_X"
PASSING_YARDS_OVER = "passing_yards_over_X"
RECEIVING_YARDS_OVER = "receiving_yards_over_X"

# Add to extract methods
def extract_subject(text):
    # NEW: Check for player name (Devin Booker, Puka Nacua, etc.)
    player = self._extract_player_name(text)
    if player:
        return player
    # EXISTING: Check for team
    ...
```

**2. Spread Extraction**
```python
def extract_spread_amount(text):
    # Pattern: "wins by over X.X" or "covers X.X"
    match = re.search(r'wins? by (?:over|under)?\s*([\d.]+)', text, re.I)
    if match:
        return float(match.group(1))
```

**3. Total Extraction**
```python
def extract_subject(text):
    # NEW: Check for "Over/Under X.X points"
    total_match = re.search(r'(over|under)\s+([\d.]+)\s+points', text, re.I)
    if total_match:
        return "game_total", float(total_match.group(2))
```

**4. Comma-Separated Parsing**
```python
def extract_instruments_batch(text):
    # Split on commas, parse each separately
    parts = text.split(',')
    instruments = []
    for part in parts:
        inst = self.extract_instrument(part.strip())
        if inst:
            instruments.append(inst)
    return instruments
```

### Phase 2: Data Enrichment
- Pass league/sport context to `extract_subject()` 
- Use ESPN metadata (home_team, away_team) to disambiguate
- Cache player names by sport

---

## Implementation Priority

| Pattern | Frequency | Difficulty | Value | Priority |
|---------|-----------|-----------|-------|----------|
| Team Matchups | 15% | Easy | Working | ✅ Done |
| Spreads (by N pts) | 20% | Easy | High | 🔴 **Do This First** |
| Player Props (Booker: 2+) | 50% | Medium | Very High | 🟠 **Do Second** |
| Totals (Over 200 pts) | 10% | Easy | Medium | 🟡 **Do Third** |
| Complex Aggregates | 5% | Hard | Low | 🟢 Do Last |

---

## Success Metrics

- [ ] Extract subject from 80%+ of failing cases
- [ ] Player props recognized in text
- [ ] Spreads parsed with amount
- [ ] Totals (Over/Under) identified
- [ ] Cross-provider matching improves from 0 → 5+ matches
- [ ] Arbitrage detection finds 10+ opportunities per run
