export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const defaultHeaders = {
  'Content-Type': 'application/json',
};

// Mock data for demo/offline mode
const MOCK_DATA = {
  odds: [
    {
      market_id: "MOCK-POL-001",
      event_name: "Will the Democratic candidate win the 2026 midterm Senate?",
      edge: 5.32,
      recommended_side: "yes",
      venue: "kalshi",
      sport: "POLITICS",
      league: "US Elections",
      providers: ["kalshi", "polymarket"],
      sources: ["kalshi", "polymarket"],
      is_arbitrage: true,
      best_yes: { provider: "kalshi", price: 0.47, decimal_odds: 2.1277, stake: 46.83 },
      best_no: { provider: "polymarket", price: 0.48, decimal_odds: 2.0833, stake: 53.17 },
      roi_percentage: 5.32,
      created_at: new Date().toISOString(),
    },
    {
      market_id: "MOCK-NBA-002",
      event_name: "Lakers vs Celtics - Lakers to Win",
      edge: 6.82,
      recommended_side: "yes",
      venue: "kalshi",
      sport: "BASKETBALL",
      league: "NBA",
      providers: ["kalshi", "polymarket"],
      sources: ["kalshi", "polymarket"],
      is_arbitrage: true,
      best_yes: { provider: "kalshi", price: 0.44, decimal_odds: 2.2727, stake: 43.40 },
      best_no: { provider: "polymarket", price: 0.50, decimal_odds: 2.0, stake: 56.60 },
      roi_percentage: 6.82,
      created_at: new Date(Date.now() - 60000).toISOString(),
    },
  ],
  mode: { mode: "paper" },
  trades: [],
  positions: [],
  metrics: {
    total_trades: 0,
    cash_balance: 10000.0,
    open_positions: 0,
    portfolio_value: 10000.0,
    total_pnl: 0.0,
    win_rate: 0,
    sharpe_ratio: 0,
    max_drawdown: 0,
  },
  health: {
    kalshi: { status: "connected", last_check: new Date().toISOString() },
    polymarket: { status: "connected", last_check: new Date().toISOString() },
    supabase: { status: "disconnected", last_check: new Date().toISOString() },
  },
};

async function request(path, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
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
  return request("/trade", {
    method: "POST",
    body: JSON.stringify({
      event_id: tradeData.market_id,
      stake: tradeData.stake,
    })
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
  const wsProtocol = API_BASE_URL.startsWith('https') ? 'wss' : 'ws';
  const wsHost = API_BASE_URL.replace(/https?:\/\//, '');
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

