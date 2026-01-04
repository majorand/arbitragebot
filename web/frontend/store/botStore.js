import { create } from 'zustand';

/**
 * Central state management for live bot data
 * Uses Zustand for simple, performant state updates
 * All components read from this store for real-time data
 */
export const useBotStore = create((set, get) => ({
  // Connection state
  connectionState: 'disconnected', // 'disconnected', 'connecting', 'connected', 'reconnecting'
  lastConnectionError: null,
  lastHeartbeat: null,

  // Mode (paper vs live)
  mode: 'paper',

  // Opportunities
  opportunities: [],
  bestOpportunity: null,

  // Positions
  positions: [],
  openPositionsCount: 0,

  // Trades
  trades: [],
  recentTrade: null,

  // Metrics
  metrics: {
    total_trades: 0,
    cash_balance: 0,
    portfolio_value: 0,
    total_pnl: 0,
    win_rate: 0,
    sharpe_ratio: 0,
    max_drawdown: 0,
    open_positions: 0,
  },

  // Health status
  health: {
    kalshi: { status: 'unknown', latency: null, last_check: null },
    polymarket: { status: 'unknown', latency: null, last_check: null },
    draftkings: { status: 'unknown', latency: null, last_check: null },
    supabase: { status: 'unknown', latency: null, last_check: null },
  },

  // Equity curve data (for charts)
  equityCurve: [],

  // Actions
  setConnectionState: (state) => set({ connectionState: state }),
  setConnectionError: (error) => set({ lastConnectionError: error }),
  setLastHeartbeat: (timestamp) => set({ lastHeartbeat: timestamp }),

  setMode: (mode) => set({ mode }),

  // Update opportunities (merge with existing to prevent flicker)
  updateOpportunities: (newOpps) => {
    set((state) => {
      // Find best opportunity by edge
      const best = newOpps.reduce(
        (prev, curr) => ((curr.edge || 0) > (prev.edge || 0) ? curr : prev),
        newOpps[0] || null
      );

      return {
        opportunities: newOpps,
        bestOpportunity: best && best.edge > 0 ? best : null,
      };
    });
  },

  // Update single opportunity (partial update, no flicker)
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

  // Update positions (merge with existing)
  updatePositions: (newPositions) => {
    set({
      positions: newPositions,
      openPositionsCount: newPositions.length,
    });
  },

  // Update single position (partial update)
  updatePosition: (positionId, updates) => {
    set((state) => ({
      positions: state.positions.map((pos) =>
        pos.position_id === positionId ? { ...pos, ...updates } : pos
      ),
    }));
  },

  // Add trade to history (don't replace, just prepend)
  addTrade: (trade) => {
    set((state) => ({
      trades: [trade, ...state.trades].slice(0, 50), // Keep last 50
      recentTrade: trade,
    }));
  },

  // Update trades list
  updateTrades: (newTrades) => {
    set({
      trades: newTrades,
      recentTrade: newTrades[0] || null,
    });
  },

  // Update metrics (deep merge to preserve structure)
  updateMetrics: (updates) => {
    set((state) => ({
      metrics: { ...state.metrics, ...updates },
    }));
  },

  // Update health status
  updateHealth: (source, status) => {
    set((state) => ({
      health: {
        ...state.health,
        [source]: {
          ...state.health[source],
          ...status,
          last_check: new Date().toISOString(),
        },
      },
    }));
  },

  // Update equity curve
  updateEquityCurve: (points) => {
    set({ equityCurve: points });
  },

  // Add single point to equity curve (for streaming updates)
  addEquityPoint: (point) => {
    set((state) => ({
      equityCurve: [...state.equityCurve.slice(-89), point], // Keep last 90 points
    }));
  },

  // Reset all data (e.g., on disconnect)
  reset: () => {
    set({
      connectionState: 'disconnected',
      opportunities: [],
      bestOpportunity: null,
      positions: [],
      trades: [],
      metrics: {
        total_trades: 0,
        cash_balance: 0,
        portfolio_value: 0,
        total_pnl: 0,
        win_rate: 0,
        sharpe_ratio: 0,
        max_drawdown: 0,
        open_positions: 0,
      },
      equityCurve: [],
    });
  },

  // Get full state snapshot (for debugging)
  getSnapshot: () => get(),
}));

export default useBotStore;
