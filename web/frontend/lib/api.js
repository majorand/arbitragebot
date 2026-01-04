export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const defaultHeaders = {
  'Content-Type': 'application/json',
};

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: defaultHeaders,
    ...options,
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API Error: ${response.status} - ${error}`);
  }
  
  const text = await response.text();
  return text ? JSON.parse(text) : {};
}

export function fetchOdds() {
  return request("/odds");
}

export function fetchMode() {
  return request("/mode");
}

export function updateMode(mode) {
  return request("/mode", {
    method: "POST",
    body: JSON.stringify({ mode })
  });
}

export function submitTrade(tradeData) {
  return request("/trades", {
    method: "POST",
    body: JSON.stringify(tradeData)
  });
}

export function fetchTrades() {
  return request("/trades");
}

export function fetchPositions() {
  return request("/positions");
}

export function fetchMetrics() {
  return request("/metrics");
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

