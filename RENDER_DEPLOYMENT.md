# Render Backend Deployment Guide

## Prerequisites

1. **Render Account**: https://render.com
2. **Supabase Account**: https://supabase.com (free tier available)
3. **GitHub Repository**: Push your code to GitHub first

## Step 1: Create Supabase Database

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Create a new project (or use existing)
3. Navigate to **SQL Editor**
4. Create a new query and paste the contents of `SUPABASE_SCHEMA.sql`
5. Execute the SQL to create tables
6. Get your credentials:
   - Go to **Settings > API** 
   - Copy **Project URL** (SUPABASE_URL)
   - Copy **anon public** key (SUPABASE_KEY)

## Step 2: Create Render Web Service

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** > **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `arbitragebot-backend`
   - **Environment**: `Python 3.11`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn web.backend.app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free` (or paid for reliability)

## Step 3: Set Environment Variables

In the Render dashboard, add these environment variables:

| Variable | Value | Notes |
|----------|-------|-------|
| `SUPABASE_URL` | Your Supabase project URL | From Supabase Settings > API |
| `SUPABASE_KEY` | Your anon public API key | From Supabase Settings > API |
| `KALSHI_API_KEY` | Your Kalshi API key | Optional - API still works without |
| `TRADING_MODE` | `paper` | Always use paper trading |
| `PYTHONPATH` | `/app/src` | For module imports |

### Optional API Keys

- **Kalshi**: Get from https://kalshi.com (prediction market platform)
- **Other sources** (FanDuel, DraftKings, ESPN) use public APIs - no key needed

## Step 4: Monitor Deployment

1. After pushing changes, Render will automatically build and deploy
2. Check **Logs** tab for errors
3. Use **Health Check** endpoint: `https://your-service.onrender.com/health`

## Step 5: Frontend Configuration (Vercel)

Update your Next.js frontend environment:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-service.onrender.com
```

## Common Issues

### "Could not find the table 'public.positions'"
- The positions table doesn't exist yet
- **Fix**: Run `SUPABASE_SCHEMA.sql` in Supabase SQL Editor

### "Name or service not known" for Kalshi/other APIs
- **Fix**: Either set `KALSHI_API_KEY` or the system will use mock data
- The backend gracefully handles missing external APIs

### WebSocket connection fails
- Ensure Render URL is correctly set in frontend
- Check browser DevTools Network tab for WebSocket path
- URL should be: `wss://your-service.onrender.com/stream`

## Troubleshooting

### Check Health Status
```bash
curl https://your-service.onrender.com/health
```

Response shows:
- `supabase`: Connected/Disconnected
- `kalshi`: Connected/Disconnected (if key set)
- `espn`: Connected/Disconnected
- `draftkings`: Connected/Disconnected
- `fanduel`: Connected/Disconnected

### View Logs
1. Go to Render Dashboard > Your Service
2. Click **Logs** tab
3. Filter by severity

### Enable Debug Mode
Add to environment variables:
```
LOG_LEVEL=DEBUG
```

## Scaling & Production

For production use:
1. **Paid Render instance** instead of Free (more reliable)
2. **Supabase Pro** for better uptime SLA
3. **Environment-specific vars** for staging vs production
4. **Database backups** enabled in Supabase
5. **Rate limiting** on API endpoints (already implemented for ESPN, FanDuel)

## Cost Estimates

- **Render**: Free tier available; paid starts at $7/month
- **Supabase**: Free tier (1GB); pro at $25/month
- **Vercel**: Free tier available
- **Total free tier**: $0/month ✅
