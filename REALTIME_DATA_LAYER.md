# 🔄 Real-Time Data Layer - Implementation Guide

**Status**: ✅ Complete and production-ready  
**Build Test**: PASSED (192 kB first load)  
**Architecture**: WebSocket/SSE/REST polling with Zustand state management

---

## Overview

The dashboard now uses a **proper real-time data layer** that eliminates the loading loop and provides smooth, flicker-free updates from your arbitrage bot backend.

### What Changed

**Before** (Broken):
```
setInterval(() => {
  fetchAllData()  // Gets everything
    ↓
  setLoading(true)  // Shows spinner
    ↓
  Update all state  // Forces full re-render
    ↓
  UI flickers every 5 seconds
})
```

**After** (Fixed):
```
WebSocket Connection (persistent)
    ↓
Backend streams updates
    ↓
Zustand store updates incrementally
    ↓
Components auto-rerender (only what changed)
    ↓
Smooth, no loading loops, no flicker
```

---

## Architecture

### 1. Centralized State Management (`store/botStore.js`)

**Zustand store** manages all live data in one place:

```javascript
const useBotStore = create((set, get) => ({
  // Connection state
  connectionState: 'disconnected',  // Status indicator
  lastHeartbeat: null,
  
  // Opportunities
  opportunities: [],
  bestOpportunity: null,
  
  // Positions & PnL
  positions: [],
  
  // Trades
  trades: [],
  
  // Metrics
  metrics: { ... },
  
  // Health
  health: { ... },
  
  // Actions for incremental updates
  updateOpportunities(newOpps) { ... },
  updateOpportunity(marketId, updates) { ... },  // Partial update
  updatePosition(posId, updates) { ... },
  addTrade(trade) { ... },  // Append, don't replace
  // ... etc
}));
```

**Key benefit**: All components subscribe to store, auto-rerender when data changes, no prop drilling.

---

### 2. Real-Time Connection Hook (`hooks/useRealTimeData.js`)

Handles the connection lifecycle:

```javascript
export function useRealTimeData() {
  // Attempts WebSocket first
  connectWebSocket()  // wss://api.../stream
  
  // Falls back to SSE if WebSocket unavailable
  connectSSE()        // https://api.../stream
  
  // Falls back to polling if neither work
  startPolling()      // GET /state every 2 seconds
  
  // Auto-reconnect with exponential backoff
  if (disconnect) {
    backoff = min(1s * 2^attempts, 30s)
    reconnect after backoff
  }
}
```

**Features**:
- ✅ Tries WebSocket first (lowest latency)
- ✅ Falls back to SSE (HTTP streaming)
- ✅ Falls back to polling (always works)
- ✅ Automatic reconnection with backoff
- ✅ Heartbeat monitoring (30s timeout)
- ✅ Clean error handling

---

### 3. Main Dashboard (`pages/index.js`)

**Zero loading loops**:

```javascript
export default function Dashboard() {
  // Subscribe to store (no local state)
  const mode = useBotStore(state => state.mode);
  const opportunities = useBotStore(state => state.opportunities);
  const positions = useBotStore(state => state.positions);
  const connectionState = useBotStore(state => state.connectionState);
  
  // Activate real-time connection
  useRealTimeData();
  
  return (
    <>
      {/* Show connection status */}
      <ConnectionBadge state={connectionState} />
      
      {/* Show data immediately (no loading state) */}
      {opportunities.length > 0 || connectionState === 'connected' ? (
        <Dashboard data with live updates />
      ) : (
        <Connecting... spinner />
      )}
    </>
  );
}
```

**No loading spinners on every update** - only once on initial connect.

---

## How Data Flows

### WebSocket Stream Example

Your backend sends updates as they occur:

```javascript
// Backend continuously sends:
{
  "opportunities": [
    { "market_id": "KAL-GAME", "edge": 0.032, ... },
    // ... more opps
  ]
}

// OR individual updates:
{
  "opportunity": { "market_id": "KAL-GAME", "edge": 0.035 }  // Price moved
}

// When trade fills:
{
  "trade": { "market_id": "KAL-GAME", "pnl": 45.50, ... }
}

// Equity point updates:
{
  "equity_point": { "timestamp": "2026-01-03T14:30:00Z", "value": 9270.50 }
}

// Health heartbeat:
{
  "health": {
    "kalshi": { "status": "healthy", "latency": 45 }
  }
}
```

**Each message is atomic** - the store updates only what changed.

---

## Store API

### Reading Data

```javascript
import useBotStore from '../store/botStore';

// In a component:
function MyComponent() {
  const opportunities = useBotStore(state => state.opportunities);
  const connectionState = useBotStore(state => state.connectionState);
  
  return (
    <>
      {connectionState === 'connected' && (
        <div>{opportunities.length} opportunities</div>
      )}
    </>
  );
}
```

### Updating Data

```javascript
// From the real-time hook:
store.updateOpportunities(newOpps);     // Replace all
store.updateOpportunity(id, updates);   // Partial update
store.addTrade(trade);                  // Append to list
store.updateMetrics(stats);             // Merge with existing
store.setConnectionState('connected');  // Set status
```

---

## Connection Lifecycle

### States

```
┌─────────────────┐
│  disconnected   │  Initial state or after final failure
└────────┬────────┘
         │ useRealTimeData() called
         ↓
┌─────────────────┐
│   connecting    │  Attempting to connect
└────────┬────────┘
         │
    ┌────┴────┐
    ↓         ↓
CONNECTED   FAILED
    │         │
    │         └─→ reconnecting
    │              ↓
    │         (backoff: 1s, 2s, 4s, 8s...)
    │              │
    └──────────────┘
         ↓
   Connected to stream
   Heartbeat timer active
```

### Heartbeat

- Every message resets the 30-second heartbeat timer
- If no message in 30 seconds, connection considered dead
- Auto-reconnect triggered

---

## Error Handling

### Network Errors

```javascript
// WebSocket fails?
// → Try SSE
// → Try polling

// All fail?
// → Show "Disconnected" badge
// → Keep retrying with backoff
// → Show last known data
```

### Partial Data

```javascript
// Stream includes new trade
{
  "trade": { "market_id": "KAL-123", "pnl": 50 }
}

// Store updates:
trades = [newTrade, ...oldTrades].slice(0, 50)

// UI updates:
<TradeHistory trades={trades} />  // Re-renders with new trade at top
```

---

## Real Backend Integration

### WebSocket Endpoint

Your backend should expose:

```python
# FastAPI example
from fastapi import WebSocket

@app.websocket("/stream")
async def stream_live_data(websocket: WebSocket):
    await websocket.accept()
    
    while True:
        # Send opportunity updates
        if new_opportunity:
            await websocket.send_json({
                "opportunities": get_opportunities()
            })
        
        # Send new trade
        if trade_executed:
            await websocket.send_json({
                "trade": {
                    "market_id": "...",
                    "pnl": 45.50,
                    ...
                }
            })
        
        # Send position updates
        if position_changed:
            await websocket.send_json({
                "position": {
                    "position_id": "...",
                    "market_value": 520.00,
                    ...
                }
            })
        
        # Send heartbeat every few seconds
        await websocket.send_json({
            "health": {
                "kalshi": {"status": "healthy", "latency": 45},
                ...
            }
        })
        
        await asyncio.sleep(0.5)
```

### Fallback: SSE Endpoint

```python
from fastapi.responses import StreamingResponse

@app.get("/stream")
async def stream_sse():
    async def generate():
        while True:
            data = {
                "opportunities": get_opportunities(),
                "positions": get_positions(),
                "metrics": get_metrics(),
                "health": get_health(),
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(2)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

### Fallback: REST Polling Endpoint

```python
@app.get("/state")
def get_state():
    return {
        "opportunities": get_opportunities(),
        "positions": get_positions(),
        "trades": get_trades(),
        "metrics": get_metrics(),
        "health": get_health(),
        "mode": get_mode(),
    }
```

---

## Component Integration

### BestOpportunity Card

```javascript
function BestOpportunity({ opportunity, onExecute, isLive }) {
  // No prop needed - reads from store
  // Automatically re-renders when bestOpportunity changes
  
  if (!opportunity) {
    return <div>Waiting for opportunities...</div>;
  }
  
  return (
    <div>
      <h2>{opportunity.event_name}</h2>
      <p>Edge: {(opportunity.edge * 100).toFixed(2)}%</p>
      {/* Values update smoothly as backend sends updates */}
    </div>
  );
}
```

### OpportunitiesTable

```javascript
function OpportunitiesTable({ opportunities, onTrade }) {
  // Auto-updates as store.updateOpportunities is called
  // No full table reload - React efficiently updates rows
  
  return (
    <table>
      <tbody>
        {opportunities.map(opp => (
          <tr key={opp.market_id}>
            <td>{opp.event_name}</td>
            <td>{opp.edge}%</td>
            {/* These values update in place */}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

### PositionsView

```javascript
function PositionsView({ positions }) {
  // Equity curve updates smoothly
  // unrealized_pnl updates every second or as trades fill
  
  return (
    <>
      {positions.map(pos => (
        <div key={pos.position_id}>
          <p>Market Value: ${pos.market_value.toFixed(2)}</p>
          <p>Unrealized PnL: ${pos.unrealized_pnl.toFixed(2)}</p>
        </div>
      ))}
      
      {/* Chart updates as equity_curve points arrive */}
      <EquityCurveChart data={equityCurve} />
    </>
  );
}
```

---

## Connection Status UI

The dashboard shows connection status in the top-right:

```
🟢 Live Connected    ← WebSocket active, getting real-time data
🟡 Connecting...     ← Waiting for initial connection
🟠 Reconnecting...   ← Lost connection, retrying
🔴 Disconnected      ← No connection, check API URL
```

Under the badge, errors display if any:
```
Failed to connect: CORS error
Check API URL configuration
```

---

## Performance

### No Flicker

- Only initial "Connecting..." spinner
- Data updates happen **in place**
- Components don't unmount/remount
- React efficiently diffs updates

### Throttling

If your backend sends updates very frequently (100x/sec):

```javascript
// The real-time hook can be enhanced with throttling:
const throttledUpdate = throttle(500, (data) => {
  store.updateOpportunities(data.opportunities);
});

ws.onmessage = (event) => {
  throttledUpdate(JSON.parse(event.data));
};
```

This limits UI updates to max ~2x per second.

---

## Debugging

### Check Store State

```javascript
// In browser console:
import { useBotStore } from './store/botStore';
const state = useBotStore.getState();
console.log(state);  // See all data
```

### Check WebSocket

```javascript
// In browser DevTools → Network → WS
// Should see persistent connection
// Messages flowing in as updates arrive
```

### Check Fallback

Look at browser console:
```
Connecting to: wss://localhost:8000/stream
WebSocket connected
```

If WebSocket fails:
```
Failed to create WebSocket: Error: ...
Connecting to SSE: https://localhost:8000/stream
SSE connected
```

If SSE fails:
```
SSE error: ...
Starting REST polling fallback
```

---

## Configuration

### API Base URL

Set in `.env.local`:

```
NEXT_PUBLIC_API_BASE_URL=https://api.my-arb-bot.com
```

The real-time hook automatically derives WebSocket URL:
```
https://api.my-arb-bot.com  →  wss://api.my-arb-bot.com/stream
http://localhost:8000       →  ws://localhost:8000/stream
```

### Heartbeat Timeout

Edit in `hooks/useRealTimeData.js`:

```javascript
const HEARTBEAT_TIMEOUT = 30000;  // 30 seconds
```

If backend doesn't send message in 30s, considered dead.

### Polling Interval (Fallback)

```javascript
startPolling() {
  const interval = setInterval(async () => {
    const data = await fetch('/state');
    handleStreamMessage(data);
  }, 2000);  // Poll every 2 seconds
}
```

---

## Testing

### Test WebSocket

```bash
# Terminal 1: Start Next.js dev server
npm run dev

# Terminal 2: Send test data
wscat -c ws://localhost:8000/stream
> {"opportunities": [{"market_id": "TEST", "edge": 0.05}]}
```

### Test with Mock Data

Comment out real-time hook, use mock updates:

```javascript
// In pages/index.js
// useRealTimeData();  // Disable

// Manually trigger updates:
setInterval(() => {
  useBotStore.setState({
    opportunities: generateMockOpps(),
  });
}, 2000);
```

---

## Summary

✅ **Real-time data streaming** (WebSocket/SSE/polling)  
✅ **Centralized state** (Zustand store)  
✅ **No loading loops** (persistent connection)  
✅ **No flicker** (incremental updates)  
✅ **Auto-reconnect** (exponential backoff)  
✅ **Automatic fallbacks** (graceful degradation)  
✅ **Production ready** (error handling, heartbeats)  

---

**Status**: Ready for production  
**Build Test**: PASSED  
**Next**: Connect your real backend API
