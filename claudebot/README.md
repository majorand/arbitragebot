# ClaudeBot — Sports Arbitrage Scanner

Real-time sports arbitrage scanner and auto-executor. Monitors live odds across 18+ sportsbooks simultaneously, detects pricing inefficiencies, and executes paired opposing bets to lock in guaranteed profit.

## Installation

```bash
cd claudebot
npm install
```

To make `claudebot` available globally:
```bash
npm link
```

## Quick Start (Demo Mode)

```bash
npm start
# or
node src/cli.js scan --mode standard_arb --sports all --books 18 --threshold 0.03
```

Press `Ctrl+C` to stop and see session summary.

## CLI Usage

```
claudebot scan --mode <mode> --sports <sports> --books <N> --threshold <decimal>
```

### Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--mode` | Scan mode (see below) | `standard_arb` |
| `--sports` | Sports to scan (comma-separated or `all`) | `all` |
| `--books` | Number of bookmakers to scan | `18` |
| `--threshold` | Minimum arb margin to execute | `0.03` |

### Scan Modes

- **`standard_arb`** — Classic two-outcome arbitrage. Finds the best odds for each side across all bookmakers and locks in guaranteed profit when the combined implied probability is below 100%.
- **`latency_arb`** — Exploits odds feed timing differences between books. Shows latency in ms for each detection.
- **`midpoint_arb`** — Exploits line discrepancies around market consensus.

### Sports

`all`, `nfl`, `nba`, `mlb`, `nhl`, `epl`, `la_liga`, `ufc`, `tennis`

Combine multiple: `--sports nfl,nba,epl`

## Examples

```bash
# Standard arb, all sports, default settings
claudebot scan

# Latency arb on NFL and NBA only, lower threshold
claudebot scan --mode latency_arb --sports nfl,nba --threshold 0.02

# Midpoint arb on soccer leagues, higher threshold
claudebot scan --mode midpoint_arb --sports epl,la_liga --threshold 0.05

# Conservative: fewer books, higher threshold
claudebot scan --books 8 --threshold 0.05
```

## How It Works

### The Aodds Metric

Aodds represents the arbitrage margin — the guaranteed edge before fees. It is calculated as:

```
Aodds = 1 - (1/O1 + 1/O2)
```

Where O1 and O2 are the best available decimal odds for each outcome from different bookmakers.

- **Aodds > 0** means an arbitrage exists (combined implied probability < 100%)
- **Aodds = 0.03** means a 3% guaranteed margin
- **Aodds = 0.10** means a 10% guaranteed margin

### Stake Calculation

Given odds O1 and O2 and a total bankroll B:

```
Stake1 = B / (1 + O1/O2)
Stake2 = B - Stake1
Guaranteed Profit = (Stake1 × O1) - B
```

This ensures **equal profit regardless of which outcome wins**. The bankroll per trade is sized at 2-10% of total balance based on Aodds confidence.

### Feed Format

Each arb cycle prints exactly 4 lines:

```
+ ARB DETECTED: NFL | Chiefs vs Bills | ML | Aodds [0.087]
  BUY   Chiefs              ML          @ 2.64    via DraftKings      ~$42.18
  WEDGE Bills               ML          @ 3.28    via Pinnacle        ~$33.95
✓ SETTLED [+$2.84] | bal: $1,207.34
```

## Bookmakers

The scanner monitors odds across 18 bookmakers:

BetMGM, DraftKings, FanDuel, Unibet, Pinnacle, Betfair, BetUS, 1xBet, William Hill, PokerStars, Bovada, Million Hit, BetMCM, Pointsbet, Caesars, BetRivers, SuperDraft, Bet365

## Connecting Real APIs

To connect live bookmaker APIs, replace the demo odds generation in `src/books/index.js` with real API calls. Each bookmaker module should implement:

```javascript
async function fetchOdds(sport, market) {
  // Returns { oddsA: number, oddsB: number }
}
```

Set the environment variable `CLAUDEBOT_LIVE=1` and provide API keys:

```bash
export CLAUDEBOT_LIVE=1
export DRAFTKINGS_API_KEY=xxx
export PINNACLE_API_KEY=xxx
# etc.
```

## Project Structure

```
claudebot/
  src/
    cli.js          — Argument parsing, entry point, main loop
    scanner.js      — Odds ingestion and arb detection logic
    executor.js     — Stake calculation and trade placement
    settler.js      — Settlement monitoring and P&L update
    display.js      — Terminal rendering, header, feed formatting
    state.js        — Session state management
    books/
      index.js      — Bookmaker registry and odds interface
    sports/
      index.js      — Sport/market/league registry
  package.json
  README.md
```
