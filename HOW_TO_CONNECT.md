# How to Connect Everything: Visual Summary

## The Big Picture

Your **arbitrage bot** has three major pieces that need to talk to each other:

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  FRONTEND    │◄───────►│  BACKEND     │◄───────►│   APIS &     │
│  (React UI)  │ HTTP/WS │  (FastAPI)   │ HTTP    │  DATABASE    │
│  Port 3000   │         │  Port 8000   │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
    Dashboard              Real-time Data           Kalshi, DraftKings,
    Tables, Charts         Stream (/stream)        ESPN, Supabase
    Controls               Data Aggregation        
                          Paper Trading Engine
```

---

## Your Backend Already Has Most of It!

### ✅ What's Already Built (in `src/arbitragebot/`)

- **Data Sources**: Kalshi, DraftKings, ESPN (fetch market data)
- **Paper Trading Engine**: Simulates trades without real money
- **Database Integration**: Supabase storage for trades/positions
- **Strategy Engine**: Calculates arbitrage opportunities
- **Configuration System**: Load API keys from environment

### ❌ What You Need to Add (in `web/backend/`)

- **`/stream` WebSocket Endpoint**: Sends live data to frontend every 2 seconds
- **Environment Variables**: `.env` file with API credentials
- **Data Formatting**: Transform arbitragebot data → frontend schema

---

## The Connection Process

### 1️⃣ Frontend Needs Backend URL

```javascript
// web/frontend/.env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
// Or production: https://your-backend.com
```

### 2️⃣ Frontend Connects on Load

```javascript
// web/frontend/hooks/useRealTimeData.js
const ws = new WebSocket('ws://localhost:8000/stream');
// Stays open forever, receiving updates
```

### 3️⃣ Backend Sends Updates Every 2 Seconds

```python
# web/backend/app.py
@app.websocket("/stream")
async def websocket_stream(websocket):
    while True:
        # Collect data from Kalshi, DraftKings, ESPN
        opportunities = collect_market_data(sources_config)
        
        # Get positions from Supabase
        positions = fetch_positions(client)
        
        # Send to frontend
        await websocket.send_json({
            "opportunities": [...],
            "positions": [...],
            "trades": [...],
            "metrics": {...}
        })
        
        # Wait 2 seconds
        await asyncio.sleep(2)
```

### 4️⃣ Frontend Updates Dashboard

```javascript
// web/frontend/store/botStore.js (Zustand)
// Automatic updates when data arrives
store.updateOpportunities(data.opportunities)
store.updatePositions(data.positions)
// React components re-render automatically
```

---

## Files You Need to Create/Edit

### Must Create

| File | What | Content |
|------|------|---------|
| `web/backend/.env` | Configuration | API keys, database credentials |
| `web/frontend/.env.local` | Configuration | Backend URL |

### Must Edit

| File | What | Code |
|------|------|------|
| `web/backend/app.py` | Add endpoint | `/stream` WebSocket (copy from STREAM_ENDPOINT_EXAMPLE.py) |

### Already Done For You

| File | What |
|------|------|
| `web/frontend/hooks/useRealTimeData.js` | Connection & auto-reconnect |
| `web/frontend/store/botStore.js` | State management |
| `web/frontend/pages/index.js` | Dashboard |
| `src/arbitragebot/data_sources/` | Market data fetching |
| `src/arbitragebot/storage/supabase.py` | Database operations |

---

## Step-by-Step: From Blank to Connected

### Minute 1-2: Create Configuration Files

```bash
# 1. Create backend config
cat > web/backend/.env << EOF
FRONTEND_ORIGINS=http://localhost:3000
KALSHI_API_KEY=your_key_or_dummy
SUPABASE_URL=https://your.supabase.co
SUPABASE_KEY=your_key_or_dummy
TRADING_MODE=paper
EOF

# 2. Create frontend config  
cat > web/frontend/.env.local << EOF
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
EOF
```

### Minute 3-5: Add /stream Endpoint

Open `web/backend/app.py` and add code from **STREAM_ENDPOINT_EXAMPLE.py** around line 60 (after the existing `/ws` endpoint).

Copy this section:
```python
@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    # ... (entire endpoint implementation)
```

### Minute 6-8: Start Servers

```bash
# Terminal 1: Backend
cd c:\Users\major\arbitragebot
python -m uvicorn web.backend.app:app --reload --port 8000
# Should show: "Uvicorn running on http://0.0.0.0:8000"

# Terminal 2: Frontend
cd c:\Users\major\arbitragebot\web\frontend
npm run dev
# Should show: "✓ Ready in 1000ms"
```

### Minute 9-10: Test

Open browser: **http://localhost:3000**

Check:
- ✅ Page loads
- ✅ Top-right shows **🟢 Connected** (not disconnected)
- ✅ Browser console shows **"WebSocket connected"**
- ✅ Dashboard updates every 2 seconds

**🎉 You're connected!**

---

## Real-World Data Flow Example

### Scenario: User Clicks "Trade" Button

```
1. FRONTEND
   ├─ User sees opportunity: "Kalshi: NFL Over 42.5 @ 1.91"
   ├─ Clicks "Trade" button
   └─ Prompts: "Enter stake: $100"

2. FRONTEND SENDS
   └─ POST /trade
      ├─ market_id: "event_123"
      ├─ stake: 100
      ├─ side: "buy"
      └─ exchange: "kalshi"

3. BACKEND PROCESSES
   ├─ Validates market exists
   ├─ Simulates trade (paper mode):
   │  └─ Subtracts $100 from cash_balance (now $9900)
   ├─ Records in Supabase:
   │  └─ INSERT INTO trades (trade_id, amount, status, timestamp)
   └─ Returns trade_id + status

4. NEXT /stream UPDATE (2 seconds later)
   ├─ Includes new trade in trades array
   ├─ Shows updated cash_balance: 9900
   ├─ May show new position if still open
   └─ Sends to frontend

5. FRONTEND RECEIVES
   ├─ Zustand updates trades array
   ├─ Zustand updates metrics.cash_balance
   └─ React re-renders dashboard

6. USER SEES
   ├─ New trade appears in "Trade History"
   ├─ Cash balance updated from $10000 → $9900
   └─ All happens smoothly without page refresh
```

---

## Data Connections Map

### Where Each Piece Gets Data

```
Kalshi Markets
    ↓
src/arbitragebot/data_sources/kalshi.py
    ↓
src/arbitragebot/main.py::collect_market_data()
    ↓
web/backend/app.py::websocket_stream()
    ↓
JSON: "opportunities": [...]
    ↓
Frontend /stream listener
    ↓
store.updateOpportunities()
    ↓
<OpportunitiesTable/> re-renders


User Submits Trade
    ↓
web/backend/app.py::POST /trade
    ↓
STATE.paper_engine.submit_order()  [Paper mode]
    ↓
src/arbitragebot/storage/supabase.py::record_trade()
    ↓
Supabase INSERT trades table
    ↓
Next /stream update includes new trade
    ↓
Frontend receives via WebSocket
    ↓
<TradeHistory/> shows new trade


Every 2 Seconds Automatically
    ↓
Backend /stream collects:
├─ Latest odds (Kalshi, DraftKings, ESPN)
├─ Current positions (Supabase)
├─ Trade history (Supabase)
├─ Metrics calculations
├─ Source health checks
    ↓
Sends complete state to frontend
    ↓
Frontend updates everything automatically
    ↓
User sees live updates without doing anything
```

---

## Troubleshooting at a Glance

### "Page loads but shows disconnected"

```
Check (in order):
1. Is backend running? 
   → Run: python -m uvicorn web.backend.app:app --reload --port 8000

2. Is /stream endpoint in app.py?
   → Add: Copy entire endpoint from STREAM_ENDPOINT_EXAMPLE.py

3. Does .env.local have correct API URL?
   → Check: NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

4. Check browser console for errors
   → Open: F12 → Console tab
   → Look for: WebSocket connection errors
```

### "Connected but no data showing"

```
Check:
1. Backend console for errors
   → Look for: "Failed to fetch Kalshi markets" etc

2. API credentials not set
   → Check: web/backend/.env has values

3. Dummy values might be OK (shows "No opportunities")
   → This is normal if you haven't set real API keys
```

### "Backend starts but /stream not working"

```
Check:
1. Did you add @app.websocket("/stream") endpoint?
   → You must add the entire endpoint to app.py

2. Syntax error in your code?
   → Check: Backend console for Python errors
   → Fix: Copy exact code from STREAM_ENDPOINT_EXAMPLE.py
```

---

## Environment Variables Explained

### Backend (.env)

| Variable | What | Get From |
|----------|------|----------|
| `FRONTEND_ORIGINS` | Allowed frontend URLs | Your frontend domain |
| `KALSHI_API_KEY` | Sports market access | Kalshi account (optional) |
| `SUPABASE_URL` | Database location | Supabase project settings |
| `SUPABASE_KEY` | Database authentication | Supabase project settings |
| `TRADING_MODE` | paper or live | You choose |

### Frontend (.env.local)

| Variable | What | Set To |
|----------|------|--------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend location | http://localhost:8000 (dev) or https://... (prod) |

---

## Quick Validation Checklist

```bash
# 1. Backend running?
curl http://localhost:8000/docs
# Should show: FastAPI Swagger UI

# 2. Frontend running?
curl http://localhost:3000
# Should show: HTML dashboard

# 3. Can reach from frontend?
# Open browser console and run:
fetch('http://localhost:8000/state').then(r => r.json()).then(console.log)
# Should show: state object with opportunities, positions, etc
```

---

## Production Deployment

### Frontend (Vercel)
```
1. Push code to GitHub
2. Connect GitHub repo to Vercel
3. Set env var: NEXT_PUBLIC_API_BASE_URL=https://your-backend.com
4. Auto-deploys on each push
```

### Backend (Your Choice)
```
Option 1: Railway.app (easiest)
Option 2: Heroku
Option 3: DigitalOcean
Option 4: AWS/GCP/Azure

All require:
- FRONTEND_ORIGINS set to production frontend URL
- All API keys and secrets configured
- Database accessible from backend
```

---

## Your Next 3 Steps

1. **Minute 1-5**: Create `.env` files + add `/stream` endpoint
2. **Minute 5-10**: Start both servers + test connection
3. **Minute 10+**: Read INTEGRATION_GUIDE.md for deeper understanding

Then:
- Add real Kalshi API key
- Connect real Supabase database
- Implement your trading strategy
- Deploy to production

---

**That's it!** You're now ready to connect everything. Start with QUICK_START_10MIN.md for detailed instructions.

See you on the other side of real-time arbitrage! 🚀
