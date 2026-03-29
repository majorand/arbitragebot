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
      links: {
        kalshi: "https://kalshi.com/markets/democratic-senate",
        polymarket: "https://polymarket.com/search?query=democratic+senate",
      },
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
      links: {
        kalshi: "https://kalshi.com/markets/lakers-celtics",
        polymarket: "https://polymarket.com/search?query=lakers+celtics",
      },
    },
    {
      market_id: "MOCK-CRYPTO-003",
      event_name: "Will Bitcoin exceed $150K by end of 2026?",
      edge: 3.91,
      recommended_side: "no",
      venue: "polymarket",
      sport: "CRYPTO",
      league: "Markets",
      providers: ["kalshi", "polymarket"],
      sources: ["kalshi", "polymarket"],
      is_arbitrage: true,
      best_yes: { provider: "polymarket", price: 0.52, decimal_odds: 1.923, stake: 51.20 },
      best_no: { provider: "kalshi", price: 0.44, decimal_odds: 2.273, stake: 48.80 },
      roi_percentage: 3.91,
      created_at: new Date(Date.now() - 120000).toISOString(),
      links: {
        kalshi: "https://kalshi.com/markets/bitcoin-150k",
        polymarket: "https://polymarket.com/search?query=bitcoin+150k",
      },
    },
  ],
  health: {
    kalshi: { status: "connected", last_check: new Date().toISOString(), latency: 45 },
    polymarket: { status: "connected", last_check: new Date().toISOString(), latency: 62 },
    supabase: { status: "disconnected", last_check: new Date().toISOString(), latency: 0 },
  },
};

async function request(path, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: defaultHeaders,
      ...options,
      signal: AbortSignal.timeout(3000),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    const text = await response.text();
    return text ? JSON.parse(text) : {};
  } catch (err) {
    console.warn(`API request failed for ${path}, using mock data:`, err.message);
    return null;
  }
}

export function fetchOdds() {
  return request("/odds").then(data => data || MOCK_DATA.odds);
}

export function fetchHealth() {
  return request("/health").then(data => data || MOCK_DATA.health);
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
