# Data Flow & Integration Architecture

## High-Level Architecture Diagram

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    FRONTEND - React Dashboard                     ┃
┃              (http://localhost:3000)                              ┃
┃                                                                    ┃
┃  ┌─────────────────────────────────────────────────────────┐    ┃
┃  │  pages/index.js (Main Dashboard)                        │    ┃
┃  │  ├─ Hook: useRealTimeData()                              │    ┃
┃  │  │  └─ Connects to ws://localhost:8000/stream           │    ┃
┃  │  ├─ Hook: useBotStore() → Zustand State                │    ┃
┃  │  └─ Renders Components:                                 │    ┃
┃  │     ├─ OpportunitiesTable (from opportunities array)   │    ┃
┃  │     ├─ PositionsView (from positions array)            │    ┃
┃  │     ├─ TradeHistory (from trades array)                │    ┃
┃  │     └─ Health/Metrics (from health & metrics objects)  │    ┃
┃  └─────────────────────────────────────────────────────────┘    ┃
┃                           ▲                                       ┃
┃                           │ WebSocket Messages                    ┃
┃                      Every 2 seconds                              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━┼━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                             │
                             │ ws://localhost:8000/stream
                             ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃              BACKEND - FastAPI Server (Port 8000)                 ┃
┃              (http://localhost:8000)                              ┃
┃                                                                    ┃
┃  ┌──────────────────────────────────────────────────────────┐   ┃
┃  │  web/backend/app.py                                      │   ┃
┃  │                                                           │   ┃
┃  │  @app.websocket("/stream")                               │   ┃
┃  │  ├─ Every 2 seconds:                                     │   ┃
┃  │  │  ├─ Call collect_market_data() ──┐                   │   ┃
┃  │  │  ├─ Call fetch_positions()        ├──┐ Build State  │   ┃
┃  │  │  ├─ Call fetch_trades()           │  │ Object      │   ┃
┃  │  │  ├─ Call count_trades()           │  │              │   ┃
┃  │  │  └─ Call get_supabase_client()    │  │              │   ┃
┃  │  │                                   └──┘              │   ┃
┃  │  └─ Send state as JSON to frontend                     │   ┃
┃  │                                                           │   ┃
┃  │  Other Endpoints:                                        │   ┃
┃  │  ├─ GET  /state      (polling fallback)                │   ┃
┃  │  ├─ POST /trade      (execute trade)                   │   ┃
┃  │  ├─ POST /mode       (switch paper/live)              │   ┃
┃  │  ├─ GET  /mode       (get current mode)               │   ┃
┃  │  └─ GET  /odds       (fetch current odds)             │   ┃
┃  └──────────────────────────────────────────────────────────┘   ┃
┃            ▲                          ▲                   ▲      ┃
┃            │                          │                   │      ┃
┃            │ market_data              │ positions         │      ┃
┃            │ opportunities            │ trades            │ mode ┃
┃            │                          │                   │      ┃
┗━━━━━━━━━━━┼──────────────────────────┼───────────────────┼━━━━━━┛
             │                          │                   │
             │                          │                   │
        ┌────┴────────┐           ┌─────┴──────┐      ┌────┴──────┐
        │              │           │             │      │           │
        ▼              ▼           ▼             ▼      ▼           ▼
   ┌─────────────┐ ┌────────┐ ┌─────────────┐ ┌──┐ ┌──────────┐ ┌───┐
   │   KALSHI    │ │DRAFTKINGS│ │   ESPN      │ │Env│ │Supabase │ │App│
   │   API       │ │Sportsbook│ │   Events    │ │Vars│ │Database │ │STATE│
   │   (Sports   │ │  (Odds   │ │   (Scores   │ │    │ │(Trades, │ │Paper│
   │  Prediction │ │  Data)   │ │  & Teams)   │ │    │ │Positions)│ │Engine│
   │  Markets)   │ │          │ │            │ │    │ │         │ │    │
   └─────────────┘ └────────┘ └─────────────┘ └──┘ └──────────┘ └───┘
         ▲               ▲            ▲                    │
         │               │            │                    │
         └───────────────┼────────────┘                    │
              Collected by:                         Stores/Updates:
         collect_market_data()                   record_trade()
         (src/arbitragebot/main.py)              fetch_trades()
                                                 fetch_positions()
                                                 (src/arbitragebot/storage/supabase.py)
```

---

## Detailed Data Flow: Step by Step

### 1. **WebSocket Connection Initialization**

```
User opens Dashboard
         ↓
Browser navigates to http://localhost:3000
         ↓
React renders pages/index.js
         ↓
useRealTimeData() hook is called
         ↓
Creates WebSocket: ws://localhost:8000/stream
         ↓
Backend: @app.websocket("/stream") accepts connection
         ↓
console.log("✅ WebSocket connected")
         ↓
Start streaming state every 2 seconds
```

### 2. **Data Collection Cycle (Repeats Every 2 Seconds)**

```
Backend /stream handler executes:

Step 1: FETCH MARKET DATA
────────────────────────
collect_market_data() runs:
  │
  ├─→ KalshiDataSource.fetch_markets()
  │     └─→ GET https://api.kalshi.com/exchange/v2/markets
  │         └─→ Returns: [Market, Market, ...]
  │
  ├─→ DraftKingsDataSource.fetch_odds("42648")
  │     └─→ GET https://sportsbook.draftkings.com/.../v5/...
  │         └─→ Returns: [Odds, Odds, ...]
  │
  └─→ ESPNDataSource.fetch_events("basketball", "nba")
        └─→ GET https://site.api.espn.com/...
            └─→ Returns: [Event, Event, ...]

Result: List[NormalizedOdds] opportunities


Step 2: FETCH DATABASE STATE
──────────────────────────
Supabase database queries:
  │
  ├─→ fetch_positions(client)
  │     └─→ SELECT * FROM positions WHERE quantity != 0
  │         └─→ Returns: {"market_123": 50, "market_456": -25}
  │
  ├─→ fetch_trades(client)
  │     └─→ SELECT * FROM trades ORDER BY timestamp DESC LIMIT 50
  │         └─→ Returns: [{trade_id, event_id, stake, ...}, ...]
  │
  ├─→ count_trades(client)
  │     └─→ SELECT COUNT(*) FROM trades
  │         └─→ Returns: 42
  │
  └─→ STATE.paper_engine.cash_balance
        └─→ Returns: 9,750.50 (remaining balance)

Result: positions dict, trades list, counts


Step 3: FORMAT DATA FOR FRONTEND
────────────────────────────────
Transform database objects into frontend schema:

opportunities → [
  {
    market_id: "event_123",
    sport: "NFL",
    league: "NFL",
    home_team: "Chiefs",
    away_team: "Cowboys",
    selection: "Over 42.5",
    price: 1.91,
    implied_probability: 0.52,
    venue: "kalshi",
    edge: 0.045,  ← Your arbitrage strategy calculates this
    recommended_side: "yes"
  },
  ...
]

positions → [
  {
    position_id: "market_123",
    market_id: "market_123",
    quantity: 50,
    unrealized_pnl: 2.50
  },
  ...
]

trades → [
  {
    trade_id: "trade_001",
    market_id: "market_123",
    timestamp: "2024-01-04T15:32:00Z",
    side: "buy",
    stake: 100,
    price: 1.85,
    status: "filled",
    pnl: 8.50
  },
  ...
]

metrics → {
  total_trades: 42,
  cash_balance: 9750.50,
  portfolio_value: 9758.00,
  total_pnl: 250.50,
  win_rate: 0.667,
  sharpe_ratio: 1.45,
  max_drawdown: 0.05,
  open_positions: 2
}

health → {
  kalshi: {status: "connected", latency: 45ms},
  draftkings: {status: "connected", latency: 52ms},
  espn: {status: "connected", latency: 38ms},
  supabase: {status: "connected", latency: 12ms}
}

mode → "paper"


Step 4: SEND TO FRONTEND
────────────────────────
await websocket.send_json({
  opportunities: [...],
  positions: [...],
  trades: [...],
  metrics: {...},
  health: {...},
  mode: "paper"
})
```

### 3. **Frontend Receives Data**

```
WebSocket message arrives:
         ↓
ws.onmessage(event) triggered
         ↓
Parse JSON: data = JSON.parse(event.data)
         ↓
handleStreamMessage(data) called:
  │
  ├─→ store.updateOpportunities(data.opportunities)
  │     └─→ Zustand updates: opportunities array
  │
  ├─→ store.updatePositions(data.positions)
  │     └─→ Zustand updates: positions array
  │
  ├─→ store.updateTrades(data.trades)
  │     └─→ Zustand updates: trades array
  │
  ├─→ store.updateMetrics(data.metrics)
  │     └─→ Zustand updates: metrics object
  │
  ├─→ store.updateHealth(source, status)
  │     └─→ Zustand updates: health object
  │
  └─→ store.setMode(data.mode)
        └─→ Zustand updates: mode
         ↓
React components re-render:
  │
  ├─→ pages/index.js subscribes to store changes
  │     └─→ Detects data changed → forces re-render
  │
  └─→ Components read from store:
      ├─→ OpportunitiesTable reads: useBotStore(s => s.opportunities)
      ├─→ PositionsView reads: useBotStore(s => s.positions)
      ├─→ TradeHistory reads: useBotStore(s => s.trades)
      └─→ Metrics read: useBotStore(s => s.metrics)
         ↓
Dashboard updates with latest data
```

---

## API Endpoints Reference

### WebSocket

**Connection**
```
ws://localhost:8000/stream
or
wss://production-domain.com/stream
```

**Message Frequency**: Every 2 seconds

**Message Format**:
```json
{
  "opportunities": [{...}, ...],
  "positions": [{...}, ...],
  "trades": [{...}, ...],
  "metrics": {...},
  "health": {...},
  "mode": "paper|live"
}
```

### REST API (Fallback)

**Get Current State**
```
GET /state
Response:
{
  "opportunities": [...],
  "positions": {...},
  "trades": [...],
  "metrics": {...},
  "mode": "paper"
}
```

**Get Mode**
```
GET /mode
Response:
{
  "mode": "paper"
}
```

**Set Mode**
```
POST /mode
Body: {"mode": "paper" or "live"}
Response:
{
  "mode": "paper"
}
```

**Submit Trade**
```
POST /trade
Body: {
  "market_id": "event_123",
  "side": "buy",
  "stake": 100,
  "exchange": "kalshi"
}
Response:
{
  "trade_id": "trade_001",
  "event_id": "event_123",
  "status": "filled",
  "mode": "paper",
  "price": 1.85,
  "stake": 100,
  "timestamp": "2024-01-04T15:32:00Z"
}
```

**Get Trades**
```
GET /trades
Response:
[
  {
    "trade_id": "trade_001",
    "event_id": "event_123",
    "status": "filled",
    "mode": "paper",
    "price": 1.85,
    "stake": 100,
    "timestamp": "2024-01-04T15:32:00Z"
  },
  ...
]
```

**Get Positions**
```
GET /positions
Response:
{
  "market_123": 50,
  "market_456": -25
}
```

**Get Metrics**
```
GET /metrics
Response:
{
  "total_trades": 42,
  "cash_balance": 9750.50,
  "open_positions": 2
}
```

---

## Error Handling Flow

```
Error Occurs at Backend
     ↓
Example: KalshiDataSource.fetch_markets() fails
     ↓
Log error: "Failed to fetch Kalshi markets: Connection timeout"
     ↓
Continue with other sources (DraftKings, ESPN)
     ↓
Send partial state with available data:
{
  "opportunities": [...],  ← Fewer than expected
  "health": {
    "kalshi": {status: "disconnected", latency: null},
    "draftkings": {status: "connected", latency: 52},
    ...
  }
}
     ↓
Frontend receives:
  ├─→ Updates health monitor (shows red for Kalshi)
  ├─→ Shows available opportunities from other sources
  └─→ User sees "⚠️ Kalshi unavailable" but can still trade
```

---

## Performance Metrics

### Update Latency
```
Data Generated:          0ms   (backend starts collecting)
Network Transfer:        ~50ms (WebSocket message to frontend)
Store Update:            ~5ms  (Zustand state update)
React Re-render:         ~100ms (components update)
Total:                   ~155ms
```

### Data Size
```
Typical message:         ~80-150 KB (25 opportunities + 50 trades + metrics)
Message Rate:            1 message every 2 seconds
Bandwidth:               ~40-75 KB/s
```

### Scalability
```
Single Server:           Can handle ~500-1000 concurrent WebSocket connections
CPU Usage:               ~10-20% per 100 connections
Memory:                  ~50 MB base + 100 KB per connection
```

---

## Monitoring Checklist

- [ ] WebSocket connects: `ws.readyState === 1`
- [ ] Data updates every 2 seconds
- [ ] No JavaScript errors in console
- [ ] Backend logs show `collect_market_data()` succeeding
- [ ] Supabase queries complete in <200ms
- [ ] Health status for all sources showing in dashboard
- [ ] Trades execute and appear in history instantly
- [ ] Mode switches (paper ↔ live) work smoothly
- [ ] Paper balance persists after page reload
- [ ] Live balance updates from real account

---

See **INTEGRATION_GUIDE.md** for complete setup instructions.
See **BACKEND_SETUP.md** for detailed backend configuration.
