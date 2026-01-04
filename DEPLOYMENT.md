# Arbitrage Bot - Complete Setup & Deployment Guide

## Quick Start (5 minutes)

### Prerequisites
- Node.js 18+ installed
- Python 3.11+ installed
- Git

### 1. Backend Setup

```bash
cd c:\Users\major\arbitragebot

# Install Python dependencies
pip install -e .

# or via pyproject.toml
pip install -r requirements.txt

# Configure environment variables
# Edit web/backend/backend.env with your credentials:
#   SUPABASE_URL=your_supabase_url
#   SUPABASE_KEY=your_supabase_key
#   KALSHI_API=https://api.kalshi.com
#   KALSHI_API_KEY=your_kalshi_key
#   TRADING_MODE=paper

# Start the backend (FastAPI + Uvicorn)
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Backend should be running at**: `http://localhost:8000`

Verify: Visit `http://localhost:8000/docs` for interactive API docs

### 2. Frontend Setup

```bash
cd web/frontend

# Install dependencies
npm install

# Create environment file
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
```

**Frontend should be running at**: `http://localhost:3000`

### 3. Access the Dashboard

Visit: **`http://localhost:3000`**

You should see:
- ✅ Header with mode toggle (PAPER/LIVE)
- ✅ Best opportunity panel
- ✅ Tab navigation (Opportunities, Positions, Health, Config)
- ✅ Real-time data loading
- ✅ Dark theme with professional styling

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   User Browser                              │
│              (Dashboard @ localhost:3000)                    │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
   HTTP/REST         WebSocket
        │                 │
        ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                            │
│              (localhost:8000)                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • GET /odds           → Market opportunities        │   │
│  │ • POST/GET /mode      → Paper/Live toggle           │   │
│  │ • POST /trades        → Execute trades              │   │
│  │ • GET /trades         → Trade history               │   │
│  │ • GET /positions      → Open positions              │   │
│  │ • GET /metrics        → Performance stats           │   │
│  │ • WS /ws              → Real-time updates           │   │
│  └──────────────────────────────────────────────────────┘   │
└────┬──────────────────┬──────────────────┬──────────────────┘
     │                  │                  │
     ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Kalshi     │  │  DraftKings  │  │  Supabase    │
│   Exchange   │  │   API/ESPN   │  │  Database    │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Production Deployment

### Option 1: Docker (Recommended)

```bash
# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Expose ports
EXPOSE 8000 3000

# Start backend
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Build and run
docker build -t arbitrage-bot .
docker run -p 8000:8000 -p 3000:3000 --env-file web/backend/backend.env arbitrage-bot
```

### Option 2: Traditional Server (Ubuntu/Debian)

```bash
# SSH to your server
ssh user@your-server.com

# Clone repo
git clone https://github.com/your-repo/arbitragebot.git
cd arbitragebot

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Setup Node
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs

cd web/frontend
npm install
npm run build

# Configure environment
cp web/backend/backend.env.example web/backend/backend.env
# Edit with your keys

# Install systemd services
sudo cp systemd/arbitrage-backend.service /etc/systemd/system/
sudo cp systemd/arbitrage-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start services
sudo systemctl start arbitrage-backend
sudo systemctl start arbitrage-frontend
sudo systemctl enable arbitrage-backend arbitrage-frontend

# Monitor
sudo systemctl status arbitrage-backend arbitrage-frontend
```

### Option 3: Cloud (Heroku/Railway/Render)

1. **Backend**: Deploy to Heroku/Railway
   ```bash
   # web/backend/Procfile
   web: uvicorn app:app --host 0.0.0.0 --port $PORT
   
   # Environment variables in dashboard
   SUPABASE_URL=...
   SUPABASE_KEY=...
   KALSHI_API_KEY=...
   TRADING_MODE=paper
   ```

2. **Frontend**: Deploy to Vercel
   ```bash
   npm install -g vercel
   cd web/frontend
   vercel
   # Set NEXT_PUBLIC_API_BASE_URL to your backend URL
   ```

---

## Environment Variables

### Backend (`web/backend/backend.env`)

```env
# Supabase (Database)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...

# Kalshi Exchange API
KALSHI_API=https://api.kalshi.com
KALSHI_API_KEY=your-api-key-here

# Trading Mode
TRADING_MODE=paper          # 'paper' or 'live'

# Frontend Origins (CORS)
FRONTEND_ORIGINS=http://localhost:3000,https://yourfrontend.com
```

### Frontend (`.env.local`)

```env
# Backend API URL
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## File Structure

```
arbitragebot/
├── app.py                          # FastAPI entrypoint
├── pyproject.toml                  # Python config + scripts
├── requirements.txt                # Python dependencies
├── config/
│   ├── example_sources.yaml        # Data source config
│   └── strategy.yaml               # Strategy config
│
├── src/arbitragebot/
│   ├── __init__.py
│   ├── main.py                     # Bot main logic
│   ├── config.py                   # Core config loader
│   ├── schemas.py                  # Data models
│   ├── data_sources/
│   │   ├── kalshi.py              # Kalshi data fetcher
│   │   ├── draftkings.py          # DraftKings data
│   │   └── espn.py                # ESPN API
│   ├── exchanges/
│   │   ├── kalshi.py              # Kalshi trading client
│   │   └── polymarket.py          # (Removed)
│   ├── strategies/
│   │   ├── base.py                # Base strategy
│   │   └── arbitrage.py           # Arbitrage strategy
│   ├── storage/
│   │   ├── kalshi.py              # Kalshi storage helpers
│   │   ├── supabase.py            # Database helpers
│   │   └── schemas.py             # Storage data models
│   └── utils/
│       ├── http.py                # HTTP utilities
│       └── time.py                # Time utilities
│
└── web/
    ├── backend/
    │   ├── app.py                 # FastAPI app definition
    │   ├── config.py              # Backend config
    │   ├── socket_server.py        # WebSocket manager
    │   ├── trades.py              # Trades router
    │   ├── backend.env            # Environment vars
    │   └── payload/
    │       ├── user.py            # User payloads
    │       └── count.py           # Count payloads
    │
    └── frontend/
        ├── pages/
        │   ├── index.js           # Dashboard page
        │   └── _app.js            # App wrapper
        ├── components/
        │   ├── Header.js          # Top nav
        │   ├── BestOpportunity.js # Opportunity card
        │   ├── OpportunitiesTable.js
        │   ├── PositionsView.js
        │   ├── TradeHistory.js
        │   ├── HealthMonitor.js
        │   └── ConfigPanel.js
        ├── lib/
        │   └── api.js             # API client
        ├── styles/
        │   └── globals.css        # Tailwind config
        ├── .env.local             # Environment vars
        ├── package.json           # Dependencies
        ├── tailwind.config.js     # Tailwind config
        └── next.config.js         # Next.js config
```

---

## Key Commands

### Development

```bash
# Start backend with hot reload
uvicorn app:app --reload

# Start frontend with hot reload
npm run dev

# Run tests
pytest
npm test

# Format code
black src/
prettier --write web/
```

### Production

```bash
# Build backend (if using installer)
python setup.py build

# Build frontend
npm run build
npm start

# View logs
journalctl -u arbitrage-backend -f
```

---

## Troubleshooting

### "Connection refused" when loading dashboard
- ✅ Verify backend running: `curl http://localhost:8000/docs`
- ✅ Verify frontend running: `curl http://localhost:3000`
- ✅ Check `.env.local` has correct `NEXT_PUBLIC_API_BASE_URL`

### "No opportunities found"
- ✅ Verify Kalshi API keys in `backend.env`
- ✅ Check data sources are fetching: `curl http://localhost:8000/odds`
- ✅ Look at backend logs for fetch errors

### WebSocket connection fails
- ✅ Check backend supports `/ws` endpoint
- ✅ Verify CORS headers allow WebSocket upgrades
- ✅ Look at browser Network tab → WS filter

### Backend crashes on startup
- ✅ Check Python version: `python --version` (need 3.11+)
- ✅ Verify all dependencies: `pip list | grep -E 'fastapi|uvicorn|supabase'`
- ✅ Check environment variables set: `echo $SUPABASE_URL`

### Data not updating in real-time
- ✅ Check WebSocket is connected (browser console)
- ✅ Verify REFRESH_INTERVAL in `pages/index.js` (default 5s)
- ✅ Look at backend logs for data fetch errors

---

## Security Checklist

- [ ] Set `TRADING_MODE=paper` in development
- [ ] Use strong, unique Kalshi API keys
- [ ] Rotate Supabase keys regularly
- [ ] Enable HTTPS in production
- [ ] Set `FRONTEND_ORIGINS` to only trusted domains
- [ ] Use environment variables, never hardcode secrets
- [ ] Add rate limiting to API endpoints
- [ ] Implement API key rotation mechanism
- [ ] Monitor logs for suspicious activity
- [ ] Use VPN for accessing backend in production

---

## Performance Tuning

### Frontend
- Use `npm run build` for production (not `npm run dev`)
- Enable GZIP compression on server
- Use CDN for static assets
- Lazy-load charts and tables

### Backend
- Use `uvicorn app:app --workers 4` for multiple processes
- Enable caching for `/odds` endpoint
- Use Supabase connection pooling
- Monitor API rate limits from Kalshi/DraftKings

### Database
- Index `market_id`, `timestamp`, `exchange` columns
- Archive old trades to separate table
- Use row-level security for data isolation

---

## Support & Debugging

### Enable Debug Logging

**Backend**:
```python
# In app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Frontend**:
```javascript
// In .env.local
DEBUG=arbitragebot-*
```

### View Logs

```bash
# Backend logs (if using systemd)
sudo journalctl -u arbitrage-backend -f --no-pager

# Frontend logs (check browser console)
# F12 → Console tab

# All output
tail -f ~/.arbitrage/logs/bot.log
```

---

## Next Steps

1. **Test Paper Trading**: Place a few test trades in paper mode
2. **Monitor Health**: Check all data feeds in Health Monitor tab
3. **Tune Strategy**: Edit `config/strategy.yaml` to adjust edge thresholds
4. **Scale Cautiously**: Start with small stakes in live mode
5. **Setup Alerts**: Configure email/Telegram notifications for errors
6. **Backup Config**: Version control your strategy configs

---

## Contact & Resources

- **API Docs**: `http://localhost:8000/docs`
- **Frontend Dashboard**: `http://localhost:3000`
- **Kalshi API**: https://kalshi.com/developers
- **Supabase Docs**: https://supabase.com/docs

---

**Last Updated**: 2026-01-03  
**Version**: 0.3.0
