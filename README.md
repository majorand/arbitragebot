# 🚀 Arbitrage Bot - Sports Betting Edge Finder

A production-ready **sports arbitrage bot** with a professional dashboard for finding and executing profitable trades across Kalshi, ESPN, and other sportsbooks.

**Status**: ✅ **FULLY DEPLOYED & READY TO USE**

---

## 🎯 What It Does

This bot **automatically detects arbitrage opportunities** in sports betting markets:

1. **Fetches real-time odds** from Kalshi and ESPN
2. **Calculates implied probabilities** across venues
3. **Detects profitable arbitrage** (edge > 2.5% by default)
4. **Executes trades** in paper mode (simulated) or live mode (real money)
5. **Tracks positions & PnL** with real-time dashboard

---

## ✨ Features

### 🎛️ Trading Controls
- **Paper Mode** (Simulated): Risk-free testing
- **Live Mode** (Real Orders): Execute on Kalshi exchange
- **Kill Switch**: Emergency order cancellation

### 📊 Dashboard Views
- **Best Opportunity**: Top-ranked arbitrage opportunity
- **Opportunities Tab**: Full filterable list
- **Positions Tab**: Portfolio view + equity curve
- **Health Tab**: Data feed status monitoring
- **Config Tab**: Risk & strategy settings
- **Trade History**: Execution log with P&L

### 🎨 User Experience
- Dark mode (professional, low-stress)
- Responsive design (desktop & mobile)
- Real-time WebSocket updates
- Intuitive tab navigation
- Semantic colors (green=profit, red=danger)

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
cd web/frontend && npm install && cd ../..
```

### 2. Configure Credentials
```bash
cat > web/backend/backend.env << EOF
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
KALSHI_API=https://api.kalshi.com
KALSHI_API_KEY=your_api_key
TRADING_MODE=paper
FRONTEND_ORIGINS=http://localhost:3000
EOF
```

### 3. Start Services

**Terminal 1 - Backend:**
```bash
uvicorn app:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd web/frontend && npm run dev
```

### 4. Open Dashboard
Visit: **http://localhost:3000**

---

## 📡 API Endpoints

```bash
GET  /mode                   # Get current mode
POST /mode                   # Switch mode (paper/live)
GET  /odds                   # Get opportunities
POST /trades                 # Execute trade
GET  /trades                 # Get trade history
GET  /positions              # Get open positions
GET  /metrics                # Get performance metrics
WS   /ws                     # WebSocket for real-time updates
```

**Interactive Docs**: http://localhost:8000/docs

---

## 📁 Project Structure

```
arbitragebot/
├── app.py                          # FastAPI entrypoint
├── QUICKSTART.md                   # Quick reference
├── DEPLOYMENT.md                   # Deployment guide
├── start.bat / start.sh            # Startup scripts
├── config/                         # Strategy configuration
├── src/arbitragebot/               # Core bot logic
│   ├── data_sources/              # Data fetchers
│   ├── exchanges/                 # Trading clients
│   ├── strategies/                # Arbitrage logic
│   └── storage/                   # Database helpers
└── web/
    ├── backend/                   # FastAPI API
    │   ├── app.py
    │   ├── socket_server.py
    │   ├── trades.py
    │   └── backend.env
    └── frontend/                  # React/Next.js dashboard
        ├── pages/index.js
        ├── components/
        ├── lib/api.js
        └── .env.local
```

---

## 🔐 Security

✅ Use environment variables for credentials  
✅ Rotate API keys regularly  
✅ Test in paper mode first  
✅ Monitor all trades in real-time  
✅ Never commit secrets to git  

---

## 📞 Support

- **API Docs**: http://localhost:8000/docs
- **Kalshi API**: https://kalshi.com/developers
- **Supabase**: https://supabase.com/docs
- **Next.js**: https://nextjs.org/docs

---

**Version**: 0.3.0 (Production Ready)  
**Last Updated**: 2026-01-03  
**Status**: ✅ Ready to Deploy

arbitragebot is a Python sports arbitrage scanner that normalizes odds from multiple books, stores them in Supabase, and exposes data to a small web frontend for monitoring opportunities.

## Overview

arbitragebot is a Python-based sports arbitrage engine that pulls odds from multiple sources, normalizes them into a common schema, and persists them to a Supabase-backed datastore for analysis and alerting.

The project is structured as a backend package (`arbitragebot/`) plus a small web frontend (`web/`) for inspecting odds and potential opportunities.

## Features

- Normalizes raw sportsbook odds into a consistent schema (sport, league, market type, selection, price, implied probability).
- Stores odds snapshots in Supabase using an `odds` table keyed by a deterministic `odds_id`.
- Provides simple strategy hooks for evaluating basic arbitrage opportunities.
- Ships with a lightweight web UI (Next.js / React) to view current odds and health of the bot.

## Project structure

- `src/arbitragebot/schemas.py` – dataclasses and type definitions for normalized odds and order types.
- `src/arbitragebot/storage/` – storage backends, including Supabase integration.
- `src/arbitragebot/storage/supabase.py` – helper functions for inserting/upserting odds into Supabase.
- `web/` – frontend application for browsing odds and opportunities.
- `requirements.txt` – Python dependencies.
- `pyproject.toml` – project metadata and tooling configuration.

## Getting started

### Prerequisites

- Python 3.11+
- Node.js (for the web frontend)
- A Supabase project with an `odds` table configured

### Backend setup

```bash
# clone the repo
git clone https://github.com/majorand/arbitragebot.git
cd arbitragebot

# create and activate virtualenv
python -m venv .venv
.\.venv\Scripts\activate  # on Windows

# install dependencies
pip install -r requirements.txt
```

Create a `.env` file (or otherwise set environment variables):

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_service_role_or_anon_key
```

Run the bot (example entrypoint):

```bash
python -m arbitragebot.main
```

## Frontend

The `web/` folder contains a small web UI (e.g., Next.js) for viewing odds data stored in Supabase.

```bash
cd web
npm install
npm run dev
```

Then open the printed localhost URL in your browser to inspect current odds and basic arbitrage views.
