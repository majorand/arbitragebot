# Frontend-Backend Integration Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend Dashboard (React)                   │
│              (web/frontend/pages/index.js & components)          │
│                         Port 3000                                │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/WebSocket
                         │ NEXT_PUBLIC_API_BASE_URL
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Server                         │
│              (web/backend/app.py & related files)               │
│                     Port 8000                                   │
│  - REST API endpoints (/odds, /trades, /positions, /metrics)   │
│  - WebSocket endpoint (/stream)                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐  ┌──────────────┐  ┌──────────┐
    │  Kalshi │  │ DraftKings/  │  │ Supabase │
    │   API   │  │  ESPN/Other  │  │   DB     │
    │         │  │ Sportsbooks  │  │          │
    └─────────┘  └──────────────┘  └──────────┘
```

---

## Step 1: Configure Backend Environment

Create `web/backend/.env` with your API credentials:

```env
# Frontend URL for CORS
FRONTEND_ORIGINS=http://localhost:3000,https://yourdomain.com

# Trading Configuration
TRADING_MODE=paper  # or 'live'

# Kalshi API (Sports Prediction)
KALSHI_API=https://api.kalshi.com
KALSHI_API_KEY=your_kalshi_api_key_here

# Supabase (Database)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Optional: Other Exchanges
POLYMARKET_API=https://api.polymarket.com
DRAFTKINGS_API=https://sportsbook.draftkings.com/sites/US-SB/api/v5
```

---

## Step 2: Update Backend `/stream` Endpoint

The frontend expects a WebSocket `/stream` endpoint that sends real-time data. Add this to `web/backend/app.py`:

```python
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """
    WebSocket endpoint that streams live bot state to frontend.
    Frontend connects to ws://localhost:8000/stream or wss://...
    """
    await websocket.accept()
    
    try:
        while True:
            # Get current bot state
            sources_config = _load_sources_config()
            
            # Collect live market data
            opportunities = collect_market_data(sources_config)
            
            # Get current positions and trades
            client = get_supabase_client()
            positions = fetch_positions(client)
            trades = fetch_trades(client)
            
            # Calculate metrics
            total_trades = count_trades(client)
            cash_balance = STATE.paper_engine.cash_balance
            
            # Build response matching frontend schema
            state = {
                "opportunities": [
                    {
                        "market_id": opp.event_id,
                        "sport": opp.sport,
                        "league": opp.league,
                        "home_team": opp.home_team,
                        "away_team": opp.away_team,
                        "selection": opp.selection,
                        "edge": 0.05,  # Calculate arbitrage edge
                        "recommended_side": "yes",
                        "venue": opp.source,
                        "price": opp.price,
                        "implied_probability": opp.implied_probability,
                    }
                    for opp in opportunities
                ],
                "positions": [
                    {
                        "position_id": pos_id,
                        "market_id": pos_id,
                        "quantity": qty,
                        "unrealized_pnl": qty * 0.01,  # Calculate based on current price
                    }
                    for pos_id, qty in positions.items()
                    if qty != 0
                ],
                "trades": [
                    {
                        "trade_id": trade["trade_id"],
                        "market_id": trade["event_id"],
                        "timestamp": trade["timestamp"],
                        "side": "buy",
                        "stake": trade["stake"],
                        "price": trade["price"],
                        "status": trade["status"],
                    }
                    for trade in trades[-50:]  # Last 50 trades
                ],
                "metrics": {
                    "total_trades": total_trades,
                    "cash_balance": cash_balance,
                    "portfolio_value": cash_balance + sum(
                        qty * 0.01 for qty in positions.values()
                    ),
                    "total_pnl": 0.0,  # Calculate from trade history
                    "win_rate": 0.0,  # Calculate from successful trades
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 0.0,
                    "open_positions": len([q for q in positions.values() if q != 0]),
                },
                "health": {
                    "kalshi": {"status": "connected", "latency": 45},
                    "draftkings": {"status": "connected", "latency": 52},
                    "polymarket": {"status": "disconnected", "latency": None},
                    "supabase": {"status": "connected", "latency": 12},
                },
                "mode": STATE.mode.mode,
            }
            
            # Send to frontend
            await websocket.send_json(state)
            
            # Update interval (adjust based on your needs)
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()
```

---

## Step 3: Backend REST Endpoints

Your backend should provide these REST endpoints (most already exist):

### Get Current State
```python
@app.get("/state")
async def get_state() -> dict:
    """Fallback endpoint if WebSocket unavailable (polling mode)"""
    sources_config = _load_sources_config()
    opportunities = collect_market_data(sources_config)
    client = get_supabase_client()
    
    return {
        "opportunities": [asdict(opp) for opp in opportunities],
        "positions": fetch_positions(client),
        "trades": fetch_trades(client),
        "metrics": {
            "cash_balance": STATE.paper_engine.cash_balance,
            "total_trades": count_trades(client),
        },
        "mode": STATE.mode.mode,
    }
```

### Update Mode (Paper ↔ Live)
```python
# Already exists at POST /mode
# Frontend calls: await fetch(`${API_BASE_URL}/mode`, {
#   method: 'POST',
#   body: JSON.stringify({ mode: 'paper' or 'live' })
# })
```

### Submit Trade
```python
# Already exists at POST /trade
# Frontend calls: await fetch(`${API_BASE_URL}/trade`, {
#   method: 'POST',
#   body: JSON.stringify({
#     market_id: opportunity.market_id,
#     side: 'buy' or 'sell',
#     stake: 100,
#     exchange: 'kalshi'
#   })
# })
```

---

## Step 4: Configure Frontend API URL

### Development (Local)
Create `web/frontend/.env.local`:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Production (Vercel)
Set in Vercel project settings:
```
NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com
```

---

## Step 5: Data Source Integration

### Connect to Kalshi (Sports Prediction Markets)
File: `src/arbitragebot/data_sources/kalshi.py`

```python
# Already implemented - fetches actual market data
# Connects to: https://api.kalshi.com/exchange/v2/markets
# Requires: KALSHI_API_KEY environment variable
```

**Setup:**
1. Create Kalshi account at https://kalshi.com
2. Generate API key in account settings
3. Set `KALSHI_API_KEY` in `.env`

### Connect to DraftKings Sportsbook
File: `src/arbitragebot/data_sources/draftkings.py`

```python
# Already implemented - fetches DraftKings odds
# Connects to: https://sportsbook.draftkings.com/sites/US-SB/api/v5
# No API key required (public endpoints)
```

**Setup:**
1. No authentication needed - uses public API
2. Automatically collects NFL, NBA, MLB, NHL odds
3. Normalizes to `NormalizedOdds` format

### Connect to ESPN
File: `src/arbitragebot/data_sources/espn.py`

```python
# Already implemented - fetches ESPN events
# Connects to: https://site.api.espn.com/apis/site/v2
# No API key required (public endpoints)
```

### Connect to Supabase (Database)
File: `src/arbitragebot/storage/supabase.py`

```python
# Database operations for trades, positions, metrics
# Uses: supabase-py library
# Requires: SUPABASE_URL and SUPABASE_KEY
```

**Setup:**
1. Create Supabase project at https://supabase.com
2. Create these tables (or they auto-create):
   - `trades` - Records all trades
   - `positions` - Current open positions
   - `odds` - Historical odds data
3. Set `SUPABASE_URL` and `SUPABASE_KEY` in `.env`

---

## Step 6: Run the Complete Stack

### Terminal 1: Backend Server
```bash
cd c:\Users\major\arbitragebot
python -m web.backend.app
# Runs on http://localhost:8000
# Check health: curl http://localhost:8000/docs
```

### Terminal 2: Frontend Dev Server
```bash
cd c:\Users\major\arbitragebot\web\frontend
npm run dev
# Runs on http://localhost:3000
```

### Terminal 3: Monitor Real-Time Connection (Optional)
```bash
# Open browser DevTools → Console
# Should see: "Connecting to: ws://localhost:8000/stream"
# Then: "WebSocket connected"
# Then: Data updates every 2 seconds
```

---

## Step 7: Verify Integration

### Frontend Checklist
- [ ] Dashboard loads without errors
- [ ] Connection badge shows 🟢 Connected (top-right)
- [ ] Opportunities table shows live market data
- [ ] Can switch between PAPER and LIVE modes
- [ ] Paper mode shows configurable balance
- [ ] Live mode shows real account balance
- [ ] Trade history updates in real-time
- [ ] Positions view shows open positions

### Backend Checklist
- [ ] FastAPI server starts: `uvicorn web.backend.app:app --reload`
- [ ] OpenAPI docs accessible: http://localhost:8000/docs
- [ ] WebSocket connects: Test with `wscat` or browser console
- [ ] Data flows from all sources:
  - [ ] Kalshi markets updating
  - [ ] DraftKings odds loading
  - [ ] ESPN events fetching
  - [ ] Supabase storing trades
- [ ] No CORS errors in browser console

---

## Step 8: Data Flow Example

**User clicks "Trade" on an opportunity:**

1. **Frontend** → Prompts user for stake amount
2. **Frontend** → Sends POST to `/trade` with market_id, stake
3. **Backend** → Validates market exists in latest data
4. **Backend** → Paper Mode: Simulates order in `PaperTradingEngine`
5. **Backend** → Records trade in Supabase `trades` table
6. **Backend** → Updates position in Supabase `positions` table
7. **Backend** → Next WebSocket update includes:
   - New trade in `trades` array
   - Updated position in `positions` array
   - Refreshed `metrics` (cash_balance may have changed)
8. **Frontend** → Receives WebSocket message
9. **Frontend** → Zustand store updates
10. **Frontend** → React components re-render with new data

---

## Troubleshooting

### "Cannot find localhost:8000"
- [ ] Backend not running - check Terminal 1
- [ ] Backend crashed - check logs for errors
- [ ] Wrong API_BASE_URL - verify `.env.local`

### "WebSocket connection refused"
- [ ] Backend `/stream` endpoint not implemented
- [ ] Frontend trying `wss://` but backend is `ws://`
- [ ] Firewall blocking port 8000

### "No data showing in dashboard"
- [ ] API credentials not set (KALSHI_API_KEY, SUPABASE_KEY)
- [ ] Data sources failing silently - check backend logs
- [ ] WebSocket connected but no data - check `/stream` implementation

### "CORS errors in console"
- [ ] `FRONTEND_ORIGINS` not set in backend `.env`
- [ ] Wrong frontend URL - must match exactly
- [ ] Add frontend URL: `FRONTEND_ORIGINS=http://localhost:3000`

---

## File Map: How Data Flows

```
Real-World APIs & Databases
    ↓
src/arbitragebot/data_sources/
    ├── kalshi.py         → Kalshi API
    ├── draftkings.py     → DraftKings Sportsbook
    └── espn.py           → ESPN Events

    ↓
src/arbitragebot/main.py
    └── collect_market_data()  → Fetches from all sources

    ↓
web/backend/app.py
    ├── @app.websocket("/stream")  → Sends live updates
    ├── @app.get("/state")         → REST fallback
    └── @app.post("/trade")        → Executes trades

    ↓
src/arbitragebot/storage/supabase.py
    └── Stores trades, positions, metrics

    ↓
Frontend (web/frontend/)
    ├── hooks/useRealTimeData.js   → Receives WebSocket/REST data
    ├── store/botStore.js          → Stores in Zustand
    └── pages/index.js             → Renders dashboard
```

---

## Next Steps

1. **Set up environment variables** (.env files)
2. **Start backend server** with `uvicorn`
3. **Start frontend dev server** with `npm run dev`
4. **Test WebSocket connection** in browser console
5. **Verify data flows** from real APIs
6. **Deploy both** to production (Vercel for frontend, choose your hosting for backend)

---

## Production Deployment

### Frontend → Vercel
```bash
# Vercel auto-deploys from GitHub
# Set env vars in Vercel dashboard:
NEXT_PUBLIC_API_BASE_URL=https://your-backend.com
```

### Backend → Your Server/Cloud
```bash
# Option 1: Railway.app
# Option 2: Heroku  
# Option 3: DigitalOcean
# Option 4: AWS/GCP/Azure

# Set production env vars
FRONTEND_ORIGINS=https://your-frontend.com
KALSHI_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
```

---

**Questions?** Check the `/stream` endpoint implementation and data format in `hooks/useRealTimeData.js` for expected message structure.
