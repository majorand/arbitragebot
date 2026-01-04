# QUICK START GUIDE

## ✅ What's Been Completed

Your sports arbitrage bot dashboard is **fully built and ready to deploy**. Here's what's included:

### Backend (Python/FastAPI)
- ✅ FastAPI application with 7 REST endpoints + WebSocket
- ✅ Paper trading engine (simulated fills)
- ✅ Live trading client for Kalshi exchange
- ✅ Supabase database integration
- ✅ Real-time market data fetching from Kalshi, DraftKings, ESPN
- ✅ Arbitrage strategy detection and edge calculation
- ✅ CORS middleware for frontend integration

### Frontend (React/Next.js)
- ✅ Production-ready dashboard with dark mode
- ✅ Tailwind CSS styling (fully responsive)
- ✅ Real-time WebSocket updates
- ✅ 8 major UI components:
  - Header with mode toggle (Paper/Live)
  - Best Opportunity card (featured arbitrage)
  - Opportunities Table (sortable/filterable)
  - Positions View (open positions + equity curve)
  - Trade History (execution history)
  - Health Monitor (data feed status)
  - Configuration Panel (risk/strategy settings)
  - Error handling & loading states

---

## 🚀 How to Start (30 seconds)

### Option 1: Double-Click (Windows)
```
cd c:\Users\major\arbitragebot
start.bat
```

### Option 2: Command Line (All OS)

**Terminal 1 - Start Backend:**
```bash
cd c:\Users\major\arbitragebot
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Start Frontend:**
```bash
cd c:\Users\major\arbitragebot\web\frontend
npm run dev
```

### Option 3: Docker
```bash
docker build -t arbitrage-bot .
docker run -p 8000:8000 -p 3000:3000 --env-file web/backend/backend.env arbitrage-bot
```

---

## 📍 Access Points

Once running:

| Component | URL | Purpose |
|-----------|-----|---------|
| **Dashboard** | http://localhost:3000 | Main UI for viewing/executing trades |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation (Swagger) |
| **API Fallback** | http://localhost:8000/redoc | Alternative API docs (ReDoc) |

---

## ⚙️ Configuration

### 1. Backend Environment (`web/backend/backend.env`)

Create or edit this file with your credentials:

```env
# Supabase Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Kalshi Exchange API
KALSHI_API=https://api.kalshi.com
KALSHI_API_KEY=your-kalshi-api-key-here

# Trading Mode
TRADING_MODE=paper        # Start with 'paper' for testing

# Frontend CORS
FRONTEND_ORIGINS=http://localhost:3000,http://localhost:3001
```

### 2. Frontend Environment (`.env.local`)

Already created, but customize if needed:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 🎯 Dashboard Features

### Trading Mode Controls
- **Paper Mode** (Blue button): Simulate trades without real money
- **Live Mode** (Red button): Execute real trades on Kalshi
- Confirmation dialog when switching to live

### Best Opportunity Panel
Shows the top-ranked arbitrage opportunity with:
- Market details (event, teams, odds)
- Calculated edge % and expected value
- Recommended trade (side & size)
- One-click execution buttons

### Four Main Tabs

1. **🎯 Opportunities** - Table of all detected arbitrage opportunities
   - Filter by minimum edge, liquidity, venue
   - Sort by edge%, time, or liquidity
   - Click "Trade" to execute

2. **💼 Positions & PnL** - Portfolio view
   - Open positions with unrealized P&L
   - 7-day equity curve chart
   - Realized P&L tracking
   - Win rate and performance stats

3. **🏥 Health Monitor** - System status
   - Data feed connectivity (Kalshi, ESPN, DraftKings, Supabase)
   - Latency metrics for each feed
   - Recent events log
   - Real-time error alerts

4. **⚙️ Configuration** - Risk & strategy settings
   - Max exposure and stake per trade
   - Minimum edge % threshold
   - Venue selection (Kalshi, DraftKings, FanDuel)
   - Sport filters (NFL, NBA, MLB, NHL)
   - Save/load configuration presets

### Trade History
Always visible at bottom:
- All executed trades
- Status (filled, pending, rejected)
- Execution details (edge, venue, stake)
- Realized profit/loss

---

## 🔄 API Endpoints

All endpoints return JSON. WebSocket available at `/ws`.

```
GET  /mode                   → Get current mode (paper/live)
POST /mode                   → Change mode
     Body: {"mode": "paper"} or {"mode": "live"}

GET  /odds                   → Get market opportunities
     Response: [{"event": "...", "edge": 3.2, "venues": "...", ...}]

POST /trades                 → Execute a trade
     Body: {
       "market_id": "market_123",
       "side": "yes",
       "stake": 100,
       "exchange": "kalshi"
     }

GET  /trades                 → Get trade history
GET  /positions              → Get open positions
GET  /metrics                → Get performance metrics
WS   /ws                     → WebSocket for real-time updates
```

See full docs at: **http://localhost:8000/docs**

---

## 🎨 Dashboard Colors & States

| Color | Meaning |
|-------|---------|
| 🔵 **Blue** | Paper mode, info, actions |
| 🔴 **Red** | Live mode, danger, errors |
| 🟢 **Green** | Profit, healthy status |
| 🟡 **Amber** | Warnings, pending trades |
| ⚫ **Gray** | Neutral, secondary |

---

## ⚠️ Important Notes

### Before Going Live
1. **Test in Paper Mode First** - Place test trades with fake money
2. **Verify Supabase Connection** - Check database credentials
3. **Monitor Health Tab** - Ensure all data feeds show "Connected"
4. **Start Small** - Begin with tiny stakes in live mode
5. **Keep Logs** - Monitor `http://localhost:8000/docs` for errors

### Common Issues & Fixes

**"Failed to load dashboard data"**
- Check if backend is running on port 8000
- Verify `.env.local` has correct API URL
- Check browser console (F12) for error details

**"No opportunities found"**
- Backend is running but no market data available
- Check Kalshi API credentials in `backend.env`
- Wait a few seconds (data fetches every 10 seconds)

**Frontend shows blank page**
- Clear browser cache: Ctrl+Shift+Del
- Rebuild: `npm run build && npm start`
- Check Node.js version: `node --version` (need 18+)

**WebSocket connection error**
- Verify `/ws` endpoint is accessible
- Check CORS settings on backend
- Look in browser Network tab → WS filter

---

## 📊 Example Workflow

1. **Open Dashboard**: http://localhost:3000
2. **Verify Mode**: Should show "📄 PAPER" (blue button)
3. **Check Health**: Click "🏥 Health Monitor" - all green?
4. **View Opportunities**: Click "🎯 Opportunities" tab
5. **Find Best Trade**: Look at top opportunity card
6. **Execute**: Click "Execute Trade" button
7. **Enter Stake**: Type amount (e.g., "100")
8. **Monitor**: Check "📄 Positions & PnL" for results
9. **Review History**: Scroll to trade history at bottom

---

## 🔐 Security Best Practices

✅ **DO:**
- Use strong, unique API keys
- Rotate credentials regularly
- Test in paper mode before live
- Monitor all trades in real-time
- Keep backend.env out of git

❌ **DON'T:**
- Hardcode secrets in code
- Commit API keys to git
- Run with `TRADING_MODE=live` until tested
- Give out your API credentials
- Use same credentials across environments

---

## 📚 Project Structure

```
arbitragebot/
├── app.py                    # FastAPI entrypoint
├── DEPLOYMENT.md             # Full deployment guide
├── start.bat / start.sh      # Startup scripts
├── web/
│   ├── backend/
│   │   ├── app.py           # FastAPI routes
│   │   ├── config.py        # Config loader
│   │   ├── socket_server.py  # WebSocket manager
│   │   └── backend.env      # Credentials
│   └── frontend/
│       ├── pages/index.js   # Dashboard component
│       ├── components/      # UI components
│       ├── lib/api.js       # API client
│       ├── .env.local       # Frontend config
│       └── README.md        # Frontend docs
└── src/arbitragebot/
    ├── main.py
    ├── data_sources/        # Data fetchers
    ├── exchanges/           # Trading clients
    ├── strategies/          # Arbitrage logic
    └── storage/             # Database helpers
```

---

## 🚦 Next Steps

1. **Install Requirements**
   ```bash
   pip install -r requirements.txt
   cd web/frontend && npm install
   ```

2. **Configure Credentials**
   - Edit `web/backend/backend.env`
   - Add Supabase URL & key
   - Add Kalshi API key

3. **Start Services**
   ```bash
   # Terminal 1
   uvicorn app:app --reload --port 8000
   
   # Terminal 2
   cd web/frontend && npm run dev
   ```

4. **Access Dashboard**
   - Open http://localhost:3000
   - Verify data is loading
   - Test paper trades

5. **Deploy**
   - See DEPLOYMENT.md for production setup
   - Consider Docker or cloud hosting
   - Setup monitoring & alerts

---

## 📞 Support Resources

- **API Docs**: http://localhost:8000/docs
- **Kalshi API**: https://kalshi.com/developers
- **Supabase**: https://supabase.com/docs
- **Next.js**: https://nextjs.org/docs
- **FastAPI**: https://fastapi.tiangolo.com/

---

**Status**: ✅ Ready to Deploy  
**Last Updated**: 2026-01-03  
**Version**: 0.3.0 (Production Ready)
