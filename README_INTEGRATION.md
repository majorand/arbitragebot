# Integration Summary: Connecting Frontend to Backend & APIs

## Quick Answer

Your **frontend dashboard** (React) is now ready to receive **real-time data** from your **backend arbitrage bot** (FastAPI). Here's how the pieces connect:

### The Connection Chain

```
Sports APIs (Kalshi, DraftKings, ESPN)
           ↓
Backend FastAPI Server (@app.websocket("/stream"))
           ↓
Frontend React Dashboard (useRealTimeData hook)
           ↓
Zustand Store (botStore.js)
           ↓
Dashboard Components (tables, charts, metrics)
```

---

## 3 Key Files to Read

| File | Purpose |
|------|---------|
| **[INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** | Complete guide - env setup, API endpoints, data flow |
| **[BACKEND_SETUP.md](./BACKEND_SETUP.md)** | Backend configuration - install deps, set env vars, run server |
| **[DATA_FLOW_ARCHITECTURE.md](./DATA_FLOW_ARCHITECTURE.md)** | Visual diagrams - how data moves through the system |

---

## What You Need to Do (5 Steps)

### Step 1: Set Up Backend Environment
Create `web/backend/.env`:
```env
FRONTEND_ORIGINS=http://localhost:3000
KALSHI_API_KEY=your_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_key_here
TRADING_MODE=paper
```

### Step 2: Add `/stream` Endpoint to Backend
Update `web/backend/app.py` - see **STREAM_ENDPOINT_EXAMPLE.py** for the code.

The endpoint sends live data every 2 seconds:
```python
@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    # Collect market data from Kalshi, DraftKings, ESPN
    # Fetch positions/trades from Supabase database
    # Send to frontend as JSON
    await websocket.send_json(state)
```

### Step 3: Start Backend Server
```bash
cd c:\Users\major\arbitragebot
python -m uvicorn web.backend.app:app --reload --port 8000
```

### Step 4: Configure Frontend
Create `web/frontend/.env.local`:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Step 5: Start Frontend & Test
```bash
cd c:\Users\major\arbitragebot\web\frontend
npm run dev
# Opens http://localhost:3000
# Should show 🟢 Connected in top-right
```

---

## Data Sources Your Backend Already Has

✅ **Kalshi** - Sports prediction markets
- Setup: Get API key from https://kalshi.com
- Fetch: Real market data via `KalshiDataSource`
- Require: `KALSHI_API_KEY` environment variable

✅ **DraftKings** - Sportsbook odds
- Setup: None needed (public API)
- Fetch: NFL, NBA, MLB, NHL odds
- Automatic: Works out of the box

✅ **ESPN** - Game events & scores
- Setup: None needed (public API)
- Fetch: Live events and team information
- Automatic: Works out of the box

✅ **Supabase** - Database for trades/positions
- Setup: Create project at https://supabase.com
- Store: Trades, positions, historical odds
- Require: `SUPABASE_URL` and `SUPABASE_KEY`

---

## Frontend Architecture (Already Built)

✅ **Real-Time Connection**
- `hooks/useRealTimeData.js` - Connects to `/stream` endpoint
- Supports: WebSocket, SSE, REST polling (automatic fallback)
- Auto-reconnect: Exponential backoff if connection drops

✅ **State Management**
- `store/botStore.js` - Zustand store for all live data
- Centralized: Single source of truth
- Reactive: Components auto-update when data changes

✅ **Dashboard Components**
- Opportunities table
- Positions view
- Trade history
- Health monitor
- Metrics summary
- Config panel (paper balance control)

---

## Common Integration Patterns

### Example 1: User Submits a Trade

```
1. User clicks "Trade" button on opportunity
2. Frontend prompts for stake amount
3. Frontend POST to /trade endpoint:
   {
     "market_id": "event_123",
     "side": "buy",
     "stake": 100,
     "exchange": "kalshi"
   }
4. Backend executes trade (paper or live)
5. Backend records in Supabase
6. Next /stream message includes new trade in history
7. Frontend receives via WebSocket
8. Dashboard re-renders with new trade
9. User sees trade appear in history instantly
```

### Example 2: Mode Switch (Paper → Live)

```
1. User clicks "LIVE" button in dashboard
2. Browser shows confirmation: "WARNING: Real trades will execute!"
3. User confirms
4. Frontend POST to /mode:
   {"mode": "live"}
5. Backend updates STATE.mode
6. Next /stream message shows mode: "live"
7. Frontend reads live account balance from metrics.cash_balance
8. Dashboard displays real balance instead of paper balance
```

### Example 3: Real-Time Updates

```
Every 2 seconds backend:
1. Calls collect_market_data()
   └─ Kalshi, DraftKings, ESPN fetch latest odds
2. Calls fetch_positions() from Supabase
3. Calls fetch_trades() from Supabase
4. Calculates metrics (win_rate, sharpe_ratio, etc)
5. Checks health of each data source
6. Sends complete state to frontend via WebSocket

Frontend receives:
1. Zustand store updates automatically
2. Components that read from store re-render
3. User sees all data change smoothly
4. NO loading spinners (persistent connection)
5. NO full page reloads (incremental updates)
```

---

## Testing Checklist

- [ ] Backend starts: `python -m uvicorn web.backend.app:app --reload`
- [ ] Frontend starts: `npm run dev`
- [ ] Open http://localhost:3000
- [ ] See 🟢 Connected badge (top-right)
- [ ] See opportunities table populated
- [ ] See metrics updating every 2 seconds
- [ ] Open browser DevTools Console
- [ ] See "WebSocket connected" message
- [ ] See data messages every 2 seconds
- [ ] Switch between PAPER and LIVE modes
- [ ] Submit a test trade (paper mode)
- [ ] See trade appear in history instantly

---

## File Reference

### Backend Files to Modify
- `web/backend/.env` ← Create this with API keys
- `web/backend/app.py` ← Add `/stream` endpoint

### Frontend Files (Already Complete)
- `web/frontend/.env.local` ← Set API_BASE_URL
- `web/frontend/hooks/useRealTimeData.js` ← Connection management
- `web/frontend/store/botStore.js` ← State management
- `web/frontend/pages/index.js` ← Main dashboard
- `web/frontend/components/*.js` ← All UI components

### Data Source Files (Already Complete)
- `src/arbitragebot/data_sources/kalshi.py` ← Kalshi integration
- `src/arbitragebot/data_sources/draftkings.py` ← DraftKings
- `src/arbitragebot/data_sources/espn.py` ← ESPN
- `src/arbitragebot/storage/supabase.py` ← Database

---

## Environment Variables

### Backend (web/backend/.env)
```env
FRONTEND_ORIGINS=http://localhost:3000,https://yourdomain.com
KALSHI_API_KEY=your_kalshi_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
TRADING_MODE=paper
LOG_LEVEL=INFO
```

### Frontend (web/frontend/.env.local)
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Frontend (Vercel Production)
```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com
```

---

## Next Steps

1. **Read INTEGRATION_GUIDE.md** - Comprehensive setup guide
2. **Read BACKEND_SETUP.md** - Backend configuration details
3. **Read DATA_FLOW_ARCHITECTURE.md** - Visual diagrams & examples
4. **Review STREAM_ENDPOINT_EXAMPLE.py** - Copy into your app.py
5. **Set environment variables** in .env files
6. **Start backend server** on port 8000
7. **Start frontend dev server** on port 3000
8. **Test WebSocket connection** in browser console
9. **Submit test trades** and verify they appear
10. **Deploy to production** (Vercel for frontend, your choice for backend)

---

## Common Questions

**Q: Where does the live market data come from?**
A: Kalshi (sports markets), DraftKings (sportsbook), ESPN (events). Backend fetches from these and sends normalized data to frontend.

**Q: Where are trades stored?**
A: Supabase PostgreSQL database. Backend records every trade for history/analysis.

**Q: How often does data update?**
A: Every 2 seconds via WebSocket. Change this by editing the `await asyncio.sleep(2)` in `/stream` endpoint.

**Q: Can I trade immediately after connecting?**
A: Yes. Switch to PAPER mode (default), set a starting balance, and submit trades. No API setup needed for paper trading.

**Q: What if I don't have Kalshi API key?**
A: You'll still get DraftKings and ESPN data. Kalshi is optional. Set the other API keys first.

**Q: How do I deploy to production?**
A: Frontend → Vercel (auto-deploys from GitHub). Backend → Railway, Heroku, DigitalOcean, or your cloud provider.

---

## Support Resources

- Kalshi API: https://docs.kalshi.com
- Supabase Docs: https://supabase.com/docs
- FastAPI Docs: https://fastapi.tiangolo.com
- Next.js Docs: https://nextjs.org/docs
- Zustand Docs: https://github.com/pmndrs/zustand

---

**TL;DR**: Your frontend is ready. Add a `/stream` endpoint to your backend that sends real-time market data from your APIs. Connect them with the API_BASE_URL env var. Done!
