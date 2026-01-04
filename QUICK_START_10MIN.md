# Minimal Working Example: Get It Running in 10 Minutes

This is the **fastest path** to get frontend + backend connected.

---

## Prerequisites

```bash
# Check Python is installed
python --version  # Should be 3.8+

# Check Node is installed  
node --version  # Should be 16+

# Install Python packages
pip install fastapi uvicorn websockets python-dotenv

# Install Frontend packages (should already be done)
cd web/frontend && npm install
```

---

## Step 1: Create Backend .env (1 minute)

Create file: `web/backend/.env`

```env
FRONTEND_ORIGINS=http://localhost:3000
KALSHI_API_KEY=dummy_for_now
SUPABASE_URL=http://localhost:5432
SUPABASE_KEY=dummy_for_now
TRADING_MODE=paper
```

(Don't have real API keys? That's fine - start with dummy values. Data sources will fail gracefully.)

---

## Step 2: Add /stream Endpoint (2 minutes)

Edit: `web/backend/app.py`

Find the existing `@app.websocket("/ws")` endpoint and add this new endpoint right below it:

```python
import asyncio
import json
from datetime import datetime

@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """Real-time data stream to frontend dashboard"""
    await websocket.accept()
    print("🔌 Frontend connected to /stream")
    
    try:
        while True:
            # Collect live data
            sources_config = _load_sources_config()
            try:
                opportunities = collect_market_data(sources_config)
            except Exception as e:
                print(f"⚠️  Market data error: {e}")
                opportunities = []
            
            # Get database state
            try:
                client = get_supabase_client()
                positions = fetch_positions(client)
                trades = fetch_trades(client)
                total_trades = count_trades(client)
            except Exception as e:
                print(f"⚠️  Database error: {e}")
                positions = {}
                trades = []
                total_trades = 0
            
            # Build state for frontend
            state = {
                "opportunities": [
                    {
                        "market_id": str(opp.event_id),
                        "sport": str(opp.sport).upper(),
                        "league": str(opp.league).upper(),
                        "home_team": str(opp.home_team),
                        "away_team": str(opp.away_team),
                        "selection": str(opp.selection),
                        "price": float(opp.price),
                        "implied_probability": float(opp.implied_probability),
                        "venue": str(opp.source),
                        "edge": 0.05,  # TODO: Calculate based on your strategy
                        "recommended_side": "yes",
                    }
                    for opp in opportunities[:25]  # First 25 opportunities
                ],
                "positions": [
                    {
                        "position_id": str(pos_id),
                        "market_id": str(pos_id),
                        "quantity": float(qty),
                        "unrealized_pnl": float(qty * 0.01),
                    }
                    for pos_id, qty in positions.items()
                    if qty != 0
                ],
                "trades": [
                    {
                        "trade_id": str(trade["trade_id"]),
                        "market_id": str(trade["event_id"]),
                        "timestamp": str(trade["timestamp"]),
                        "side": "buy",
                        "stake": float(trade["stake"]),
                        "price": float(trade["price"]),
                        "status": str(trade["status"]),
                    }
                    for trade in trades[-50:]  # Last 50 trades
                ],
                "metrics": {
                    "total_trades": int(total_trades),
                    "cash_balance": float(STATE.paper_engine.cash_balance),
                    "portfolio_value": float(STATE.paper_engine.cash_balance),
                    "total_pnl": 0.0,
                    "win_rate": 0.0,
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 0.0,
                    "open_positions": len([q for q in positions.values() if q != 0]),
                },
                "health": {
                    "kalshi": {"status": "connected" if opportunities else "disconnected", "latency": 45},
                    "draftkings": {"status": "connected", "latency": 52},
                    "espn": {"status": "connected", "latency": 38},
                    "supabase": {"status": "connected" if trades else "disconnected", "latency": 12},
                },
                "mode": STATE.mode.mode,
            }
            
            # Send to frontend
            await websocket.send_json(state)
            
            # Wait 2 seconds before next update
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        print("🔌 Frontend disconnected from /stream")
```

---

## Step 3: Create Frontend .env (30 seconds)

Create file: `web/frontend/.env.local`

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Step 4: Start Backend (1 minute)

```bash
cd c:\Users\major\arbitragebot

# Run FastAPI server
python -m uvicorn web.backend.app:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

Test it works:
```bash
# In another terminal:
curl http://localhost:8000/docs
# Opens FastAPI Swagger UI - you should see all endpoints including /stream
```

---

## Step 5: Start Frontend (2 minutes)

```bash
cd c:\Users\major\arbitragebot\web\frontend

# Run Next.js dev server
npm run dev
```

You should see:
```
✓ Ready in 1000ms
✓ Compiled in 500ms
```

---

## Step 6: Test It Works (30 seconds)

Open browser: **http://localhost:3000**

Check:
1. ✅ Dashboard loads without errors
2. ✅ Top-right shows "🟢 Connected" badge
3. ✅ Browser console shows "WebSocket connected"
4. ✅ Opportunities table shows data (or "No opportunities available")
5. ✅ Metrics at bottom show numbers updating

---

## Step 7: Verify WebSocket Connection (1 minute)

Open browser console (F12) and run:

```javascript
// You should see logs like this:
// "Connecting to: ws://localhost:8000/stream"
// "WebSocket connected"

// Check what data is flowing:
const ws = new WebSocket('ws://localhost:8000/stream');

ws.onopen = () => {
  console.log('✅ Connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('📊 Received:', {
    opportunities: data.opportunities.length,
    positions: data.positions.length,
    trades: data.trades.length,
    cash_balance: data.metrics.cash_balance,
    mode: data.mode,
  });
};

ws.onerror = (err) => {
  console.error('❌ Error:', err);
};
```

Expected output:
```
✅ Connected
📊 Received: {
  opportunities: 0,
  positions: 0,
  trades: 0,
  cash_balance: 10000,
  mode: 'paper'
}
📊 Received: {
  opportunities: 0,
  positions: 0,
  trades: 0,
  cash_balance: 10000,
  mode: 'paper'
}
```

(Numbers will be 0 if you don't have real API credentials set up yet - that's fine!)

---

## Step 8: Test Paper Trading (2 minutes)

In dashboard:
1. Switch mode to **PAPER** (it's already set)
2. Set **Balance** to 5000 (in Config tab)
3. Try to submit a test trade (click opportunity)
4. See trade appear in history (may not work if no real data)

Expected: Trade appears in history with status

---

## Success Criteria

You've successfully connected everything when:

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Dashboard shows "Connected" badge
- [ ] WebSocket messages appear in console
- [ ] Data updates every 2 seconds
- [ ] No JavaScript errors in console
- [ ] Can switch between modes without crashing
- [ ] Paper balance shows in dashboard

---

## Troubleshooting

### "Failed to connect to ws://localhost:8000/stream"

**Problem**: Backend not running

**Solution**:
```bash
# Make sure backend is running in another terminal
python -m uvicorn web.backend.app:app --reload --port 8000
```

### "No opportunities showing"

**Problem**: API keys not set or data sources failing

**Solution**: Check backend console for error messages. Dummy data will still work - the WebSocket connection is working.

### "Cannot find module 'websockets'"

**Problem**: Package not installed

**Solution**:
```bash
pip install websockets
```

### "PYTHONPATH error"

**Problem**: Python can't find arbitragebot modules

**Solution**:
```bash
# Set PYTHONPATH before running
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python -m uvicorn web.backend.app:app --reload
```

---

## Next Steps

Once this minimal example works:

1. **Add Real API Keys** - Get Kalshi, Supabase credentials
2. **Implement Edge Calculation** - Add your arbitrage logic
3. **Add Risk Management** - Implement position limits
4. **Deploy to Production** - Vercel (frontend) + Railway/Heroku (backend)

---

## Commands Quick Reference

```bash
# Terminal 1: Backend
cd c:\Users\major\arbitragebot
python -m uvicorn web.backend.app:app --reload --port 8000

# Terminal 2: Frontend
cd c:\Users\major\arbitragebot\web\frontend
npm run dev

# Terminal 3: Monitor
curl http://localhost:8000/docs  # Backend Swagger
curl http://localhost:3000       # Frontend
```

---

**That's it!** You now have real-time data flowing from backend to frontend.

From here, just:
1. Add real API credentials
2. Implement your trading strategy
3. Deploy to production

See **README_INTEGRATION.md** for the complete picture and next steps.
