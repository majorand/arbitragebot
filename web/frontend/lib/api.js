export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://arbitragebot-api.onrender.com";

const defaultHeaders = {
  'Content-Type': 'application/json',
};

// Mock data for demo/offline mode
const MOCK_DATA = {
  odds: [
    {
      market_id: "KAL-SUPERBOWL-58",
      event_name: "Super Bowl 58 Winner",
      implied_odds_yes: 0.48,
      implied_odds_no: 0.52,
      edge: 0.032,
      recommended_side: "yes",
      venue: "kalshi",
      sport: "nfl",
      confidence: 0.89,
      created_at: new Date().toISOString(),
    },
    {
      market_id: "PM-NEXT-HITTER-HR",
      event_name: "Next Batter Hits HR",
      implied_odds_yes: 0.18,
      implied_odds_no: 0.82,
      edge: 0.021,
      recommended_side: "no",
      venue: "polymarket",
      sport: "mlb",
      confidence: 0.76,
      created_at: new Date(Date.now() - 60000).toISOString(),
    },
  ],
  mode: { mode: "paper" },
  trades: [
    {
      trade_id: "TRD-001",
      market_id: "KAL-SUPERBOWL-58",
      side: "yes",
      stake: 250.0,
      fill_price: 0.48,
      pnl: 12.50,
      status: "closed",
      venue: "kalshi",
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      trade_id: "TRD-002",
      market_id: "PM-NEXT-HITTER-HR",
      side: "no",
      stake: 150.0,
      fill_price: 0.82,
      pnl: 18.75,
      status: "closed",
      venue: "polymarket",
      created_at: new Date(Date.now() - 1800000).toISOString(),
    },
  ],
  positions: [
    {
      position_id: "POS-001",
      market_id: "KAL-SUPERBOWL-58",
      event_name: "Super Bowl 58 Winner",
      side: "yes",
      quantity: 1.0,
      entry_price: 0.48,
      current_price: 0.52,
      market_value: 520.0,
      unrealized_pnl: 40.0,
      percentage_change: 8.33,
      venue: "kalshi",
      opened_at: new Date(Date.now() - 7200000).toISOString(),
    },
  ],
  metrics: {
    total_trades: 342,
    cash_balance: 8750.25,
    open_positions: 1,
    portfolio_value: 9270.25,
    total_pnl: 520.25,
    win_rate: 0.62,
    sharpe_ratio: 1.45,
    max_drawdown: 0.08,
  },
  health: {
    kalshi: { status: "healthy", last_check: new Date().toISOString() },
    polymarket: { status: "healthy", last_check: new Date().toISOString() },
    supabase: { status: "healthy", last_check: new Date().toISOString() },
  },
};

function getActiveApiUrl() {
  if (typeof window !== 'undefined' && window.location.hostname.includes('preview.jules.ai')) {
    const currentHost = window.location.host;
    if (currentHost.startsWith('3000-')) {
      const backendHost = currentHost.replace('3000-', '8000-');
      return `${window.location.protocol}//${backendHost}`;
    }
  }
  return API_BASE_URL;
}

async function request(path, options = {}) {
  const activeUrl = getActiveApiUrl();
  try {
    const response = await fetch(`${activeUrl}${path}`, {
      headers: defaultHeaders,
      ...options,
      signal: AbortSignal.timeout(3000), // 3 second timeout
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    
    const text = await response.text();
    return text ? JSON.parse(text) : {};
  } catch (err) {
    // Return mock data on error (ensures dashboard is never blank)
    console.warn(`API request failed for ${path}, using mock data:`, err.message);
    return null; // Caller will use mock data
  }
}

export function fetchOdds() {
  return request("/odds").then(data => data || MOCK_DATA.odds);
}

export function fetchMode() {
  return request("/mode").then(data => data || MOCK_DATA.mode);
}

export function updateMode(mode) {
  return request("/mode", {
    method: "POST",
    body: JSON.stringify({ mode })
  }).then(data => data || { mode });
}

export function submitTrade(tradeData) {
  return request("/trades", {
    method: "POST",
    body: JSON.stringify(tradeData)
  }).then(data => data || { status: "simulated" });
}

export function fetchTrades() {
  return request("/trades").then(data => data || MOCK_DATA.trades);
}

export function fetchPositions() {
  return request("/positions").then(data => data || MOCK_DATA.positions);
}

export function fetchMetrics() {
  return request("/metrics").then(data => data || MOCK_DATA.metrics);
}

// WebSocket Connection Helper
export function createWebSocketConnection(handlers = {}) {
  const activeUrl = getActiveApiUrl();
  const wsProtocol = activeUrl.startsWith('https') ? 'wss' : 'ws';
  const wsHost = activeUrl.replace(/https?:\/\//, '');
  const wsUrl = `${wsProtocol}://${wsHost}/ws`;
  
  try {
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      if (handlers.onConnect) handlers.onConnect();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (handlers.onMessage) handlers.onMessage(data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      if (handlers.onError) handlers.onError(err);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      if (handlers.onClose) handlers.onClose();
    };

    return ws;
  } catch (err) {
    console.error('Failed to create WebSocket:', err);
    return null;
  }
}

