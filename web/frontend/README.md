# Arbitrage Bot Dashboard

A production-ready sports arbitrage bot dashboard built with Next.js, React, and Tailwind CSS.

## Features

### 1. **Trading Mode Controls**
- Toggle between **Paper Trading** (simulated) and **Live Trading** (real orders)
- Visual indicators (blue for paper, red for live)
- Confirmation dialogs for switching to live mode
- Kill switch for emergency order cancellation

### 2. **Best Opportunity Panel**
- Real-time detection of the best arbitrage opportunity
- Shows market/event details, implied probabilities, calculated edge, and EV
- One-click execution, skip, or ignore buttons
- Confidence scores and detailed explanations

### 3. **Opportunity List & Filters**
- Sortable, filterable table of all current opportunities
- Columns: Event, Venues, Edge %, Liquidity, Bet Size, Status
- Filters for minimum edge, liquidity threshold, and more
- Expandable rows for detailed price ladders and history

### 4. **Positions, Orders & PnL**
- **Open Positions**: Instrument, direction, size, entry/current prices, unrealized PnL
- **Trade History**: Realized PnL, entry edge, timestamp, execution mode
- **Equity Curve**: 7-day equity graph visualization
- Summary stats: Win rate, average edge, max drawdown

### 5. **Bot Health & Monitoring**
- Real-time status for: Kalshi, ESPN, DraftKings, Supabase
- Latency metrics for each data feed
- Recent events log with timestamps
- Alert system for critical errors and missed trades

### 6. **Strategy Configuration**
- **Risk Controls**: Max exposure, stake per trade, min edge %, min liquidity
- **Venue Selection**: Toggle Kalshi, DraftKings, FanDuel, ESPN
- **Sport Selection**: Filter by NFL, NBA, MLB, NHL
- **Preset Configs**: Save/load named configurations

### 7. **UX & Design**
- Dark mode by default (professional, low-stress interface)
- Semantic colors: Green for profit, Amber for warnings, Red for danger
- Real-time updates via WebSocket
- Responsive design (desktop & mobile)
- Smooth animations and transitions

## Tech Stack

- **Frontend**: Next.js 14 + React 18
- **Styling**: Tailwind CSS 3 with custom dark theme
- **Charts**: Recharts for equity curves and performance visualization
- **Icons**: Lucide React for professional UI icons
- **State**: React Hooks + Zustand (optional for advanced state)
- **API**: Fetch API + WebSocket for real-time updates

## Installation

```bash
# Install dependencies
npm install

# Create .env.local for API connection
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local

# Development mode (with hot reload)
npm run dev

# Production build
npm run build
npm start
```

## API Integration

### Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/odds` | Fetch current opportunities |
| GET | `/mode` | Get current trading mode (paper/live) |
| POST | `/mode` | Switch trading mode |
| POST | `/trades` | Submit a new trade |
| GET | `/trades` | Fetch trade history |
| GET | `/positions` | Get open positions |
| GET | `/metrics` | Get performance metrics |
| WS | `/ws` | WebSocket for real-time updates |

### Environment Variables

```env
# Backend API URL (default: http://localhost:8000)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Usage

### Starting the Dashboard

```bash
npm run dev     # Development with hot reload on http://localhost:3000
npm start       # Production mode
```

### Main Navigation

1. **Header**: Mode toggle, health status, quick stats
2. **Tab Navigation**: Switch between Opportunities, Positions, Health, Config
3. **Best Opportunity Card**: Featured top-ranked arbitrage opportunity
4. **Dynamic Content**: Load relevant view based on selected tab
5. **Trade History**: Always visible at bottom for quick reference

### Operating the Bot

1. **Paper Mode** (Learning/Testing)
   - Click the blue "PAPER" button
   - Execute trades with simulated fills
   - Test strategies without risk

2. **Live Mode** (Real Trading)
   - Click the red "LIVE" button (confirmation required)
   - Watch for visual red indicators
   - Trades execute on real exchanges
   - Can switch back to paper anytime (be cautious mid-trade)

3. **Placing Trades**
   - Click "Execute Trade" on best opportunity card or table
   - Enter desired stake amount
   - Monitor in Trade History and Positions views

4. **Risk Management**
   - Set risk parameters in Configuration tab
   - Monitor equity curve and PnL
   - Use Kill Switch in emergency situations

## Component Structure

```
pages/
├── index.js              # Main dashboard page

components/
├── Header.js             # Top navigation & mode toggle
├── BestOpportunity.js    # Featured opportunity card
├── OpportunitiesTable.js # Full opportunities list
├── PositionsView.js      # Positions, orders, PnL
├── TradeHistory.js       # Trade history table
├── HealthMonitor.js      # Data feeds & event log
└── ConfigPanel.js        # Strategy settings

lib/
├── api.js                # API client & WebSocket helper

styles/
└── globals.css           # Tailwind setup + custom theme
```

## Styling & Customization

### Color Scheme
- **Primary**: Blue (#3b82f6) - Actions, info
- **Success**: Green (#10b981) - Profit, healthy
- **Danger**: Red (#dc2626) - Errors, live mode
- **Warning**: Amber (#f59e0b) - Cautions, pending
- **Background**: Charcoal (#0f172a) - Dark, professional

### Custom Classes
- `.card-dark` - Standard card component
- `.button-primary` - Primary action button
- `.button-danger` - Destructive action button
- `.status-badge` - Status indicator
- `.border-glow` - Subtle blue glow effect

## Troubleshooting

### Dashboard shows "Failed to load dashboard data"
1. Verify backend is running on `http://localhost:8000`
2. Check `.env.local` for correct `NEXT_PUBLIC_API_BASE_URL`
3. Look at browser console for specific API errors
4. Ensure CORS is configured on backend

### WebSocket connection failing
1. Verify `/ws` endpoint is available on backend
2. Check firewall/network rules
3. Look for CORS headers in backend response
4. Try refreshing page

### Components not rendering
1. Clear Next.js cache: `rm -rf .next && npm run build`
2. Verify all dependencies installed: `npm install`
3. Check for missing prop values passed to components

## Performance Tips

- Dashboard auto-refreshes every 5 seconds (configurable)
- WebSocket provides real-time updates without polling
- Lazy-load heavy components if needed
- Charts re-render only when data changes
- Use React.memo for expensive components

## Future Enhancements

- [ ] Animated opportunity alerts/notifications
- [ ] Advanced charting (Pine Script integration)
- [ ] Custom alert thresholds
- [ ] Email/SMS/Telegram notifications
- [ ] Trade simulation/backtesting
- [ ] Mobile app (React Native)
- [ ] Dark/light mode toggle
- [ ] Export data to CSV
- [ ] API key management UI
- [ ] Strategy builder interface

## License

Proprietary - Sports Arbitrage Bot
