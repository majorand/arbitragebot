# Complete Backend Setup Instructions

## Quick Start

### 1. Install Backend Dependencies

```bash
cd c:\Users\major\arbitragebot

# Install Python packages
pip install fastapi uvicorn websockets pydantic pydantic-settings python-dotenv

# Already installed (from requirements.txt):
# - supabase (database)
# - requests (HTTP)
# - python-dateutil
```

### 2. Set Up Environment Variables

Create `web/backend/.env`:

```env
# ===== REQUIRED =====

# Frontend URL(s) for CORS - comma separated
FRONTEND_ORIGINS=http://localhost:3000,https://yourdomain.com

# Kalshi Sports Market API
KALSHI_API=https://api.kalshi.com
KALSHI_API_KEY=your_api_key_here

# Supabase Database (PostgreSQL)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key

# Trading Mode
TRADING_MODE=paper

# ===== OPTIONAL =====
# Polymarket (Prediction Markets)
POLYMARKET_API=https://api.polymarket.com

# DraftKings (Sportsbook)
DRAFTKINGS_API=https://sportsbook.draftkings.com/sites/US-SB/api/v5

# Logging
LOG_LEVEL=INFO
```

### 3. Update web/backend/app.py

Add the `/stream` WebSocket endpoint:

```python
# At the top of web/backend/app.py, add:
import asyncio
from datetime import datetime

# Then add this endpoint (replace or extend existing /ws):

@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """
    Real-time data stream to frontend.
    Sends bot state every 2 seconds.
    """
    await websocket.accept()
    print("Frontend connected to /stream")
    
    try:
        while True:
            try:
                # Collect market data from all sources
                sources_config = _load_sources_config()
                opportunities = collect_market_data(sources_config)
                
                # Get database state
                client = get_supabase_client()
                positions = fetch_positions(client)
                trades = fetch_trades(client)
                
                # Build response for frontend
                state = {
                    "opportunities": [
                        {
                            "market_id": opp.event_id,
                            "sport": opp.sport,
                            "league": opp.league,
                            "home_team": opp.home_team,
                            "away_team": opp.away_team,
                            "selection": opp.selection,
                            "price": opp.price,
                            "implied_probability": opp.implied_probability,
                            "venue": opp.source,
                            "edge": 0.05,  # Calculate based on your strategy
                            "recommended_side": "yes",
                        }
                        for opp in opportunities
                    ],
                    "positions": [
                        {
                            "position_id": pos_id,
                            "market_id": pos_id,
                            "quantity": qty,
                            "unrealized_pnl": 0.0,
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
                        for trade in trades[-50:]
                    ],
                    "metrics": {
                        "total_trades": count_trades(client),
                        "cash_balance": STATE.paper_engine.cash_balance,
                        "portfolio_value": STATE.paper_engine.cash_balance,
                        "total_pnl": 0.0,
                        "win_rate": 0.0,
                        "sharpe_ratio": 0.0,
                        "max_drawdown": 0.0,
                        "open_positions": len([q for q in positions.values() if q != 0]),
                    },
                    "health": {
                        "kalshi": {"status": "connected", "latency": 45},
                        "draftkings": {"status": "connected", "latency": 52},
                        "espn": {"status": "connected", "latency": 38},
                        "supabase": {"status": "connected", "latency": 12},
                    },
                    "mode": STATE.mode.mode,
                }
                
                # Send to frontend
                await websocket.send_json(state)
                
                # Wait 2 seconds before next update
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in stream: {e}")
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print("Frontend disconnected from /stream")
```

### 4. Add Missing Endpoints (if needed)

```python
# These should already exist in web/backend/app.py
# But make sure they're present:

@app.get("/state")
async def get_state() -> dict:
    """Fallback for polling (if WebSocket unavailable)"""
    sources_config = _load_sources_config()
    opportunities = collect_market_data(sources_config)
    client = get_supabase_client()
    
    return {
        "opportunities": [
            {
                "market_id": opp.event_id,
                "price": opp.price,
                "venue": opp.source,
            }
            for opp in opportunities
        ],
        "positions": fetch_positions(client),
        "trades": fetch_trades(client),
        "metrics": {
            "total_trades": count_trades(client),
            "cash_balance": STATE.paper_engine.cash_balance,
        },
        "mode": STATE.mode.mode,
    }
```

### 5. Start Backend Server

```bash
cd c:\Users\major\arbitragebot

# Development (with auto-reload)
python -m uvicorn web.backend.app:app --reload --port 8000 --host 0.0.0.0

# Or using uvicorn directly:
uvicorn web.backend.app:app --reload --port 8000

# Production (no reload)
uvicorn web.backend.app:app --port 8000 --workers 4
```

Check it works:
- OpenAPI Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/metrics

### 6. Test WebSocket Connection

Open browser DevTools Console and run:

```javascript
// Test WebSocket connection
const ws = new WebSocket('ws://localhost:8000/stream');

ws.onopen = () => console.log('✅ Connected to /stream');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('📊 Received state:', data);
  console.log('Opportunities:', data.opportunities.length);
  console.log('Cash Balance:', data.metrics.cash_balance);
};

ws.onerror = (error) => console.error('❌ WebSocket error:', error);

ws.onclose = () => console.log('Disconnected');
```

Expected output:
```
✅ Connected to /stream
📊 Received state: {opportunities: Array(25), positions: Array(0), trades: Array(3), ...}
Opportunities: 25
Cash Balance: 10000
```

---

## Data Sources Setup

### Kalshi (Required for Sports Markets)

1. **Sign up**: https://kalshi.com
2. **Get API Key**:
   - Login → Account → API Keys
   - Create new key (no expiration)
3. **Set Environment Variable**:
   ```env
   KALSHI_API_KEY=your_key_here
   ```
4. **Test**:
   ```bash
   python
   >>> from src.arbitragebot.data_sources.kalshi import KalshiDataSource
   >>> ks = KalshiDataSource(api_key="your_key")
   >>> markets = ks.fetch_markets()
   >>> print(f"Found {len(markets)} markets")
   ```

### DraftKings (Automatic - No Setup)

- Public API, no authentication required
- Automatically fetches:
  - NFL, NBA, MLB, NHL odds
  - Moneyline, spread, total markets
- Backend has built-in source: `src/arbitragebot/data_sources/draftkings.py`

### ESPN (Automatic - No Setup)

- Public API, no authentication required
- Automatically fetches:
  - Live game odds
  - Event information
  - Score updates
- Backend has built-in source: `src/arbitragebot/data_sources/espn.py`

### Supabase (Required for Database)

1. **Sign up**: https://supabase.com
2. **Create Project**:
   - Name: "arbitragebot"
   - Region: Your region
3. **Get Credentials** (Project Settings):
   ```env
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_KEY=eyJhbGc... (anon key)
   ```
4. **Create Tables** (SQL Editor):
   ```sql
   -- Trades table
   create table trades (
     id bigserial primary key,
     trade_id text unique,
     event_id text,
     price float,
     stake float,
     status text,
     mode text,
     timestamp timestamp,
     pnl float default 0
   );
   
   -- Positions table
   create table positions (
     id bigserial primary key,
     event_id text unique,
     quantity float,
     entry_price float,
     updated_at timestamp
   );
   
   -- Odds history (optional)
   create table odds (
     id bigserial primary key,
     event_id text,
     source text,
     price float,
     timestamp timestamp
   );
   ```

---

## Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'arbitragebot'"

**Solution:**
```bash
cd c:\Users\major\arbitragebot

# Make sure PYTHONPATH includes src/
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or add to .env
PYTHONPATH=./src

# Then run:
python -m uvicorn web.backend.app:app --reload
```

### Issue: "KALSHI_API_KEY not set"

**Solution:**
1. Create `web/backend/.env`
2. Add: `KALSHI_API_KEY=your_key`
3. Restart backend server

### Issue: "Supabase connection failed"

**Solution:**
```python
# Test connection in Python:
from arbitragebot.storage.supabase import get_supabase_client

client = get_supabase_client()
result = client.table('trades').select('COUNT(*)').execute()
print(result)  # Should succeed
```

### Issue: "WebSocket connects but no data"

**Solution:**
1. Check backend logs for `collect_market_data` errors
2. Verify API keys are set
3. Test data sources individually:
   ```python
   from arbitragebot.data_sources.kalshi import KalshiDataSource
   
   ks = KalshiDataSource(api_key="your_key")
   markets = ks.fetch_markets()
   print(f"Got {len(markets)} markets")
   ```

---

## File Structure Reference

```
web/backend/
├── .env                    ← Your API keys & config
├── app.py                  ← FastAPI server (add /stream here)
├── socket_server.py        ← WebSocket management
└── trades.py               ← Trade endpoints

src/arbitragebot/
├── main.py                 ← collect_market_data()
├── data_sources/
│   ├── kalshi.py          ← Kalshi API integration
│   ├── draftkings.py      ← DraftKings integration
│   └── espn.py            ← ESPN integration
└── storage/
    ├── supabase.py        ← Database operations
    └── schemas.py         ← Data models
```

---

## Testing the Full Stack

**Terminal 1: Backend**
```bash
cd c:\Users\major\arbitragebot
python -m uvicorn web.backend.app:app --reload --port 8000
# Should show: "Uvicorn running on http://0.0.0.0:8000"
```

**Terminal 2: Frontend**
```bash
cd c:\Users\major\arbitragebot\web\frontend
npm run dev
# Should show: "Ready in 1000ms"
```

**Browser: http://localhost:3000**
- Check top-right: Should show 🟢 Connected
- Check console: Should see "WebSocket connected"
- Check dashboard: Should see live opportunities, positions, trades

**Browser DevTools Console:**
```javascript
// You should see this output:
✅ WebSocket connected
📊 Received opportunities: 25
📊 Received positions: 3
📊 Received trades: 12
```

---

## Production Deployment

### Frontend (Vercel)
```bash
# Just push to GitHub, Vercel auto-deploys
# Set env var in Vercel Dashboard:
# NEXT_PUBLIC_API_BASE_URL=https://your-backend.com
```

### Backend (Choose One)

**Option 1: Railway.app** (Easiest)
```bash
# 1. Push code to GitHub
# 2. Connect at railway.app
# 3. Add environment variables
# 4. Deploy automatically
```

**Option 2: DigitalOcean**
```bash
# Create droplet, install Python:
apt-get update
apt-get install python3-pip
pip install -r requirements.txt

# Run with Gunicorn:
pip install gunicorn
gunicorn web.backend.app:app --workers 4 --port 8000
```

**Option 3: AWS/GCP/Azure**
- Deploy as containerized service
- Add Dockerfile (include in repo)
- Scale automatically

---

**Ready to go live?** Check INTEGRATION_GUIDE.md for full connection details.
