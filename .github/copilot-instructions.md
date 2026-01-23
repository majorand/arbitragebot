# ArbitrageBot AI Coding Instructions

## Project Overview

A production sports arbitrage bot that detects profitable pricing discrepancies across betting markets (Kalshi, ESPN, Fanatics, etc.), executes trades automatically, and provides a real-time dashboard. The system uses a **5-layer canonical model** to match semantically identical markets across different providers and market formats.

## Architecture: Three Independent Layers

### 1. Core Engine (`src/arbitragebot/`)
- **Data Sources** (`data_sources/`): Provider-specific API clients (Kalshi, ESPN, Fanatics, etc.)
- **Normalization** (`normalization/`): 5-layer canonical model for cross-provider matching
- **Arbitrage Detection** (`arbitrage/`): Calculates edges, allocates stakes, identifies opportunities
- **Execution** (`execution/`): Paper trading engine + live exchange clients (`exchanges/`)
- **Storage** (`storage/supabase.py`): Postgres database for trades, positions, odds history

### 2. Backend API (`web/backend/app.py`)
- FastAPI server (port 8000) with WebSocket streaming (`/stream`) for real-time dashboard updates
- Background refresh loop (`REFRESH_INTERVAL=30s`) calls `collect_market_data()` from core engine
- Maintains `STATE` object with `latest_data`, `paper_engine`, `trading_mode`, and `supabase_client`
- Critical endpoints: `/odds`, `/mode`, `/trade`, `/positions`, `/trades`, `/metrics`

### 3. Frontend Dashboard (`web/frontend/`)
- Next.js 14 + React 18 with Tailwind CSS dark theme
- Real-time updates via `useRealTimeData()` hook → WebSocket (`ws://localhost:8000/stream`)
- State management: Zustand store (`store/botStore.ts`)
- Components: `OpportunitiesTable`, `PositionsView`, `TradeHistory`, `HealthMonitor`, `ConfigPanel`

**Key Insight**: These layers communicate via well-defined interfaces. Core engine returns `List[NormalizedOdds]`, backend serializes to JSON, frontend renders via React components.

---

## 5-Layer Canonical Model (Critical Concept)

The system matches markets across providers using **5 explicit layers** to separate concerns:

```python
# Layer 1: INSTRUMENT - What real-world fact is being resolved?
#   SHA256(subject + predicate) → canonical ID
#   Example: "Jacksonville Jaguars beat Kansas City Chiefs"

# Layer 2: OUTCOME - Binary result states (YES/NO, HOME/AWAY)
#   Combined with Layer 1 to create matching identity

# Layer 3: MARKET EXPRESSION - Provider-specific packaging
#   Moneyline (ESPN), Binary Contract (Kalshi), Probability Market (Polymarket)
#   These are just "wrappers" - same outcome, different format

# Layer 4: EVENT CONTEXT - Temporal/spatial metadata
#   Date, location, participants (for filtering & confidence scoring)

# Layer 5: PROVIDER LISTING - Raw API objects
#   Never used for matching, only for execution
```

**Files**: `normalization/canonical_layers.py`, `normalization/layer_mappers.py`, `normalization/layer_aggregator.py`

**When modifying matching logic**: Always work at Layer 1+2, never at event/market level. See `test_5_layer_simple.py` for examples.

---

## Critical Developer Workflows

### Running the System
```bash
# Start both servers (backend + frontend)
./start.sh                    # Linux/Mac
start.bat                     # Windows

# Or manually:
uvicorn app:app --reload --port 8000              # Terminal 1: Backend
cd web/frontend && npm run dev                     # Terminal 2: Frontend
# Dashboard: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Testing
```bash
# Run pytest tests (uses pytest, not unittest)
pytest tests/ -v

# Test specific provider integrations
python test_fanatics_kalshi_binary.py
python test_5_layer_simple.py
python test_aggregation_debug.py

# Debug normalization
python debug_extraction.py      # Subject/predicate extraction
python debug_sports.py          # Sports category normalization
```

### Environment Setup
Create `web/backend/backend.env` (NOT `.env`) with:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
KALSHI_API=https://api.kalshi.com
KALSHI_API_KEY=your_api_key
TRADING_MODE=paper              # Start in paper mode!
FRONTEND_ORIGINS=http://localhost:3000
```

**Never commit API keys**. Use placeholder values in examples.

---

## Project-Specific Patterns

### 1. Data Flow Pattern
All market data flows through the **normalization pipeline**:
```python
# Provider → Normalizer → CanonicalEvent → Aggregator → NormalizedOdds → Arbitrage Detector
espn_data = ESPNDataSource().fetch_events("basketball", "nba")
canonical = ESPNNormalizer().normalize_events(espn_data)
aggregated = aggregate_events(canonical, confidence_threshold=0.8)
opportunities = detect_arbitrage(aggregated, min_edge_pct=2.5)
```

### 2. State Management Pattern
Backend maintains singleton `STATE` object (defined in `app.py`):
```python
STATE.latest_data: deque[NormalizedOdds]  # Cached opportunities (max 1000)
STATE.paper_engine: PaperTradingEngine    # Paper trading balance & positions
STATE.trading_mode: str                   # "paper" or "live"
STATE.supabase_client: Client             # Database connection
STATE.config: TradingConfig               # Risk limits, max stake, etc.
```

**Important**: Always check `STATE.trading_mode` before executing real trades. Paper mode uses `PaperTradingEngine`, live mode uses `KalshiTradingClient`.

### 3. WebSocket Streaming Pattern
Backend sends snapshot every 2 seconds:
```python
# Backend (app.py)
while True:
    opportunities = collect_market_data(...)
    positions = fetch_positions(STATE.supabase_client)
    trades = fetch_trades(STATE.supabase_client)
    await websocket.send_json({
        "opportunities": [asdict(o) for o in opportunities],
        "positions": positions,
        "trades": trades,
        # ... health, metrics, mode
    })
    await asyncio.sleep(2)
```

Frontend consumes via hook:
```typescript
// hooks/useRealTimeData.ts
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8000/stream');
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    setBotData(data);  // Triggers React re-render
  };
}, []);
```

### 4. Configuration YAML Pattern
Strategy configuration is defined in `config/strategy.yaml`:
```yaml
strategy:
  min_edge_pct: 2.5              # Minimum profit margin
  max_stake: 100.0               # Max bet per leg
  max_exposure_per_market: 500.0 # Total exposure limit
  per_day_loss_limit: 1000.0     # Daily stop-loss

trading:
  mode: paper                    # paper | live
  max_order_size: 100.0
```

Load via `TradingConfig` and `StrategyConfig` dataclasses in `config.py`.

---

## Integration Points & Dependencies

### External APIs
- **Kalshi**: Sports prediction markets (authenticated, rate-limited to 60 req/min)
- **ESPN**: Sports events & scores (public, no auth)
- **Fanatics**: Sportsbook odds (public, cached to avoid 429s)
- **Supabase**: Postgres database with schema in `SUPABASE_SCHEMA.sql`

### Database Schema (Simplified)
```sql
-- trades: Execution history
CREATE TABLE trades (
  trade_id TEXT PRIMARY KEY,
  event_id TEXT,
  side TEXT,        -- "YES" | "NO" | "HOME" | "AWAY"
  stake DECIMAL,
  odds DECIMAL,
  timestamp TIMESTAMPTZ,
  mode TEXT         -- "paper" | "live"
);

-- positions: Current holdings
CREATE TABLE positions (
  market_id TEXT PRIMARY KEY,
  quantity DECIMAL,
  avg_entry_price DECIMAL
);

-- odds_history: Price snapshots
CREATE TABLE odds_history (
  event_id TEXT,
  provider TEXT,
  yes_price DECIMAL,
  no_price DECIMAL,
  timestamp TIMESTAMPTZ
);
```

**Storage functions** are in `storage/supabase.py`: `record_trade()`, `fetch_positions()`, `store_odds()`.

### Cross-Component Communication
- **Backend → Frontend**: WebSocket JSON messages (2-second heartbeat)
- **Frontend → Backend**: HTTP POST for `/trade`, `/mode` mutations
- **Core Engine → Backend**: Direct Python imports (`collect_market_data()`)
- **Backend → Database**: Supabase client library

---

## Common Pitfalls & Gotchas

1. **Import Fallbacks**: `app.py` has try/except blocks for optional imports. Always test with `HAS_ARBITRAGEBOT` and `HAS_SUPABASE` flags before calling methods.

2. **Rate Limits**: Kalshi enforces 60 requests/minute. Use cached `STATE.latest_data` for frontend updates, only refresh from API every 30s.

3. **Paper vs Live Mode**: Always initialize in paper mode. Live mode requires Kalshi API credentials and executes real money trades.

4. **Canonical ID Matching**: Currently ~22% complete (5LAYER_README.md). Subject/predicate extraction needs normalization work. See `debug_extraction.py` for current issues.

5. **Frontend Build**: Next.js requires `npm run build` to catch TypeScript errors. Dev server (`npm run dev`) may not show all type issues.

6. **WebSocket Reconnection**: Frontend should implement reconnect logic with exponential backoff (currently basic).

---

## Documentation Index

- **Quick Start**: `START_HERE.md`, `QUICK_START_10MIN.md`
- **Architecture**: `DATA_FLOW_ARCHITECTURE.md`, `5LAYER_README.md`
- **Integration**: `INTEGRATION_GUIDE.md`, `HOW_TO_CONNECT.md`
- **Backend Setup**: `BACKEND_SETUP.md`, `STREAM_ENDPOINT_EXAMPLE.py`
- **Frontend**: `web/frontend/README.md`
- **Deployment**: `DEPLOYMENT.md`, `RENDER_DEPLOYMENT.md`

**Navigation Tip**: `DOCUMENTATION_MAP.md` and `MASTER_INDEX.md` contain comprehensive file indexes.

---

## When Making Changes

1. **Adding a new provider**: Create `data_sources/new_provider.py`, implement `fetch_markets()`, add normalizer in `normalization/`, update `collect_market_data()` in `main.py`.

2. **Modifying arbitrage logic**: Edit `arbitrage/` functions, ensure tests in `test_*` files still pass, update `StrategyConfig` if adding new parameters.

3. **Frontend components**: All React components are in `web/frontend/components/`, use Tailwind for styling, connect to store via `useBotStore()` hook.

4. **Database schema changes**: Update `SUPABASE_SCHEMA.sql`, modify `storage/supabase.py` functions, add migration script if needed.

5. **Matching algorithm**: Work in `normalization/layer_aggregator.py`, test with `test_5_layer_simple.py`, validate aggregation with `validate_aggregation()`.

This codebase emphasizes **separation of concerns** (data → normalization → arbitrage → execution) and **fail-safe defaults** (paper mode, graceful degradation). When in doubt, check the extensive markdown documentation before diving into code.
