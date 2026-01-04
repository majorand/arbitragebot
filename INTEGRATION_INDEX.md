# Integration Files Index

## 📚 Complete Guide to Connecting Frontend & Backend

Below are all the files created to help you connect the frontend dashboard to your arbitrage bot backend and data sources.

---

## 🚀 Start Here (Read First)

| File | Purpose | Time |
|------|---------|------|
| **[QUICK_START_10MIN.md](./QUICK_START_10MIN.md)** | 🔥 **FASTEST PATH** - Get everything running in 10 min | 10 min |
| **[README_INTEGRATION.md](./README_INTEGRATION.md)** | Overview of all pieces & how they fit together | 5 min |

---

## 📖 Detailed Guides (Read These)

| File | What You'll Learn | Read When |
|------|------------------|-----------|
| **[INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** | Complete setup guide - environment, endpoints, data sources, deployment | Setting up properly |
| **[BACKEND_SETUP.md](./BACKEND_SETUP.md)** | Backend configuration - install, env vars, start server, test connection | Configuring backend |
| **[DATA_FLOW_ARCHITECTURE.md](./DATA_FLOW_ARCHITECTURE.md)** | Visual diagrams - how data flows through system, step-by-step | Understanding architecture |

---

## 💻 Code Examples (Copy-Paste)

| File | What's Inside | Use For |
|------|---------------|---------|
| **[STREAM_ENDPOINT_EXAMPLE.py](./STREAM_ENDPOINT_EXAMPLE.py)** | Complete `/stream` WebSocket endpoint implementation | Copy into `web/backend/app.py` |

---

## 🎯 Quick Reference

### Your Checklist

- [ ] Read **QUICK_START_10MIN.md** (10 minutes)
- [ ] Create `web/backend/.env` with API credentials
- [ ] Add `/stream` endpoint to `web/backend/app.py`
- [ ] Create `web/frontend/.env.local` with API URL
- [ ] Start backend: `python -m uvicorn web.backend.app:app --reload --port 8000`
- [ ] Start frontend: `npm run dev`
- [ ] Open http://localhost:3000 and check for 🟢 Connected badge
- [ ] Test WebSocket in browser console
- [ ] Read **INTEGRATION_GUIDE.md** for full details

### File Map

```
c:\Users\major\arbitragebot\
├── QUICK_START_10MIN.md              ← START HERE (10 min)
├── README_INTEGRATION.md              ← Overview
├── INTEGRATION_GUIDE.md               ← Complete guide
├── BACKEND_SETUP.md                   ← Backend config
├── DATA_FLOW_ARCHITECTURE.md          ← Diagrams & flow
├── STREAM_ENDPOINT_EXAMPLE.py         ← Code to copy
│
├── web/backend/
│   ├── .env                           ← CREATE: API keys
│   ├── app.py                         ← EDIT: Add /stream
│   └── socket_server.py               ← (existing)
│
├── web/frontend/
│   ├── .env.local                     ← CREATE: API_BASE_URL
│   ├── hooks/useRealTimeData.js       ← (ready to use)
│   ├── store/botStore.js              ← (ready to use)
│   └── pages/index.js                 ← (ready to use)
│
└── src/arbitragebot/
    ├── data_sources/
    │   ├── kalshi.py                  ← (ready to use)
    │   ├── draftkings.py              ← (ready to use)
    │   └── espn.py                    ← (ready to use)
    │
    └── storage/
        └── supabase.py                ← (ready to use)
```

---

## 🔗 Architecture Overview

```
FRONTEND (React, Port 3000)
    ↓ WebSocket ws://localhost:8000/stream
BACKEND (FastAPI, Port 8000)
    ↓
Sports APIs
├── Kalshi (Sports Markets)
├── DraftKings (Sportsbook)
└── ESPN (Events)
    ↓
Database
└── Supabase (Trades, Positions)
```

---

## 📝 Key Concepts

### WebSocket `/stream` Endpoint
- **Location**: `web/backend/app.py`
- **Purpose**: Sends live bot state to frontend every 2 seconds
- **Message Format**: JSON with opportunities, positions, trades, metrics
- **Fallback**: REST `/state` endpoint for polling mode

### Frontend Real-Time Connection
- **File**: `web/frontend/hooks/useRealTimeData.js`
- **Purpose**: Maintains WebSocket connection
- **Features**: Auto-reconnect, fallback to polling
- **Status**: Shows connection state in top-right badge

### State Management
- **File**: `web/frontend/store/botStore.js` (Zustand)
- **Purpose**: Centralized state for dashboard
- **Updates**: Incremental (no full reload)
- **Persistence**: Auto-syncs with backend

### Data Sources
- **Kalshi**: Sports prediction markets (requires API key)
- **DraftKings**: Sportsbook odds (no auth needed)
- **ESPN**: Game events & scores (no auth needed)
- **Supabase**: Database for trades & positions (requires setup)

---

## 🎬 Common Workflows

### Setting Up for First Time

1. Read: **QUICK_START_10MIN.md** (fastest)
2. Create: `web/backend/.env` with dummy values
3. Add: `/stream` endpoint to `web/backend/app.py`
4. Create: `web/frontend/.env.local` with API URL
5. Run: Backend on port 8000
6. Run: Frontend on port 3000
7. Test: Open http://localhost:3000

### Getting Real Data

1. Create: Kalshi account at https://kalshi.com
2. Get: API key from account settings
3. Set: `KALSHI_API_KEY` in `.env`
4. Restart: Backend server
5. Check: Dashboard shows real market data

### Deploying to Production

1. Deploy: Frontend to Vercel (auto from GitHub)
2. Set: `NEXT_PUBLIC_API_BASE_URL=https://your-backend.com` in Vercel
3. Deploy: Backend to Railway/Heroku (read INTEGRATION_GUIDE.md)
4. Test: Dashboard connects to production backend
5. Monitor: Check health dashboard for API status

### Troubleshooting Connection

1. Check: Backend running on port 8000
2. Check: Frontend `.env.local` has correct API URL
3. Check: Browser console for WebSocket errors
4. Check: Backend console for data collection errors
5. Test: `curl http://localhost:8000/docs` for API docs

---

## 🔧 Environment Variables

### Backend (`web/backend/.env`)
```env
FRONTEND_ORIGINS=http://localhost:3000          # For CORS
KALSHI_API_KEY=your_key                         # Get from Kalshi
SUPABASE_URL=https://your.supabase.co           # Get from Supabase
SUPABASE_KEY=your_key                           # Get from Supabase
TRADING_MODE=paper                              # paper or live
```

### Frontend (`web/frontend/.env.local`)
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 📊 Expected Data Flow

```
Every 2 seconds:

Backend:
  1. collect_market_data()          ← From Kalshi, DraftKings, ESPN
  2. fetch_positions()              ← From Supabase
  3. fetch_trades()                 ← From Supabase
  4. calculate_metrics()            ← From trades
  5. check_health()                 ← From all sources
  6. send_json(state)               ← To frontend

Frontend:
  1. ws.onmessage(state)            ← Receives update
  2. store.update*()                ← Zustand updates
  3. Components re-render           ← React updates UI
  4. Dashboard shows latest data    ← User sees update
```

---

## ✅ Success Indicators

- ✅ Backend starts without errors
- ✅ Frontend starts without errors
- ✅ Dashboard shows "🟢 Connected" badge
- ✅ Browser console shows "WebSocket connected"
- ✅ Data updates every 2 seconds
- ✅ No JavaScript errors in console
- ✅ Can switch between modes
- ✅ Paper balance shows in dashboard
- ✅ Can submit test trades

---

## 🆘 Common Issues

| Problem | Solution |
|---------|----------|
| "Cannot connect to ws://localhost:8000" | Backend not running - check Terminal 1 |
| "No data showing in dashboard" | API credentials not set - check .env files |
| "CORS error in console" | FRONTEND_ORIGINS not set in backend .env |
| "ModuleNotFoundError: arbitragebot" | PYTHONPATH not set - see BACKEND_SETUP.md |
| "Port 8000 already in use" | Kill existing process: `lsof -i :8000` |
| "WebSocket closes immediately" | Check backend logs for errors |

---

## 📱 Testing the Connection

### Browser Console Test
```javascript
// Open DevTools (F12) and run:
const ws = new WebSocket('ws://localhost:8000/stream');
ws.onopen = () => console.log('✅ Connected');
ws.onmessage = (e) => console.log('📊 Data:', JSON.parse(e.data));
ws.onerror = (e) => console.error('❌ Error:', e);
```

### curl Test
```bash
# Test backend is running
curl http://localhost:8000/docs

# Test getting state (polling endpoint)
curl http://localhost:8000/state
```

### Full Stack Test
1. Start backend
2. Start frontend
3. Open http://localhost:3000
4. Check console for "Connected"
5. Verify data appears on dashboard

---

## 🚀 Next Steps After Setup

1. **Get Real Data**: Add API credentials for Kalshi, Supabase
2. **Test Trades**: Submit test trades in paper mode
3. **Add Arbitrage Logic**: Implement edge calculation in `/stream`
4. **Risk Management**: Add position limits, daily loss limits
5. **Deploy**: Move to production servers
6. **Monitor**: Watch health dashboard and trades

---

## 📚 External Resources

- **FastAPI**: https://fastapi.tiangolo.com/
- **WebSockets**: https://fastapi.tiangolo.com/advanced/websockets/
- **Supabase**: https://supabase.com/docs
- **Kalshi API**: https://docs.kalshi.com
- **Next.js**: https://nextjs.org/docs
- **Zustand**: https://github.com/pmndrs/zustand

---

## 🎓 What You'll Understand After Reading These Files

1. **Architecture**: How frontend, backend, and APIs connect
2. **Data Flow**: How data moves from APIs → Backend → Frontend
3. **WebSocket**: Real-time communication between client & server
4. **State Management**: How Zustand keeps data synchronized
5. **Configuration**: Environment variables and setup
6. **Troubleshooting**: Common issues and solutions
7. **Deployment**: Getting to production

---

**Ready to start?** Begin with [QUICK_START_10MIN.md](./QUICK_START_10MIN.md) - you'll be connected in 10 minutes!
