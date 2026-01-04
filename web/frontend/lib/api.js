export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function request(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode })
  });
}

export function submitTrade(eventId, stake) {
  return request("/trade", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_id: eventId, stake })
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
