import { create } from 'zustand';

/**
 * Central state management for the arbitrage scanner
 * Display-only mode - no trade execution
 */
export const useBotStore = create((set, get) => ({
  // Connection state
  connectionState: 'disconnected',
  lastConnectionError: null,
  lastHeartbeat: null,

  // Opportunities
  opportunities: [],
  bestOpportunity: null,

  // Health status
  health: {
    kalshi: { status: 'unknown', latency: null, last_check: null },
    polymarket: { status: 'unknown', latency: null, last_check: null },
    supabase: { status: 'unknown', latency: null, last_check: null },
  },

  // Metrics (display-only stats)
  metrics: {
    total_markets: 0,
    active_arbs: 0,
    avg_edge: 0,
  },

  // Equity curve data (for charts)
  equityCurve: [],

  // Actions
  setConnectionState: (state) => set({ connectionState: state }),
  setConnectionError: (error) => set({ lastConnectionError: error }),
  setLastHeartbeat: (timestamp) => set({ lastHeartbeat: timestamp }),

  // Update opportunities
  updateOpportunities: (newOpps) => {
    set(() => {
      const best = newOpps.reduce(
        (prev, curr) => ((curr.edge || 0) > (prev.edge || 0) ? curr : prev),
        newOpps[0] || null
      );

      const arbs = newOpps.filter(o => o.is_arbitrage || (o.edge || 0) >= 1.5);
      const avgEdge = arbs.length > 0
        ? arbs.reduce((sum, o) => sum + (o.edge || 0), 0) / arbs.length
        : 0;

      return {
        opportunities: newOpps,
        bestOpportunity: best && best.edge > 0 ? best : null,
        metrics: {
          total_markets: newOpps.length,
          active_arbs: arbs.length,
          avg_edge: avgEdge,
        },
      };
    });
  },

  // Update single opportunity
  updateOpportunity: (marketId, updates) => {
    set((state) => {
      const updated = state.opportunities.map((opp) =>
        opp.market_id === marketId ? { ...opp, ...updates } : opp
      );

      const best = updated.reduce(
        (prev, curr) => ((curr.edge || 0) > (prev.edge || 0) ? curr : prev),
        updated[0] || null
      );

      return {
        opportunities: updated,
        bestOpportunity: best && best.edge > 0 ? best : null,
      };
    });
  },

  // Update health status
  updateHealth: (source, status) => {
    set((state) => {
      const prev = state.health[source] || {};
      const normalized =
        typeof status === 'string'
          ? { status }
          : status || {};

      return {
        health: {
          ...state.health,
          [source]: {
            ...prev,
            status: normalized.status || prev.status,
            latency: normalized.latency ?? prev.latency,
            last_check: normalized.last_check || prev.last_check || new Date().toISOString(),
          },
        },
      };
    });
  },

  // Update equity curve
  updateEquityCurve: (points) => {
    set({ equityCurve: points });
  },

  addEquityPoint: (point) => {
    set((state) => ({
      equityCurve: [...state.equityCurve.slice(-89), point],
    }));
  },

  // Reset
  reset: () => {
    set({
      connectionState: 'disconnected',
      opportunities: [],
      bestOpportunity: null,
      metrics: { total_markets: 0, active_arbs: 0, avg_edge: 0 },
      equityCurve: [],
    });
  },

  getSnapshot: () => get(),
}));

export default useBotStore;
