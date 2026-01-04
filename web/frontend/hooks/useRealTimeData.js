import { useEffect, useRef, useCallback } from 'react';
import useBotStore from '../store/botStore';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export function useRealTimeData() {
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const heartbeatTimeoutRef = useRef(null);
  const mountedRef = useRef(true);

  const MAX_RECONNECT_ATTEMPTS = 50; // Increased from 10 to 50
  const BASE_RECONNECT_DELAY = 2000; // Increased from 1000 to 2000ms
  const HEARTBEAT_TIMEOUT = 30000;

  // Handle incoming stream messages
  const handleStreamMessage = useCallback((data) => {
    if (!data || !mountedRef.current) return;

    const store = useBotStore.getState();
    store.setLastHeartbeat(new Date().toISOString());

    if (data.opportunities && Array.isArray(data.opportunities)) {
      store.updateOpportunities(data.opportunities);
    }
    if (data.opportunity) {
      store.updateOpportunity(data.opportunity.market_id, data.opportunity);
    }
    if (data.positions && Array.isArray(data.positions)) {
      store.updatePositions(data.positions);
    }
    if (data.position) {
      store.updatePosition(data.position.position_id, data.position);
    }
    if (data.trade) {
      store.addTrade(data.trade);
    }
    if (data.trades && Array.isArray(data.trades)) {
      store.updateTrades(data.trades);
    }
    if (data.metrics) {
      store.updateMetrics(data.metrics);
    }
    if (data.health) {
      Object.entries(data.health).forEach(([source, status]) => {
        store.updateHealth(source, status);
      });
    }
    if (data.equity_curve && Array.isArray(data.equity_curve)) {
      store.updateEquityCurve(data.equity_curve);
    }
    if (data.equity_point) {
      store.addEquityPoint(data.equity_point);
    }
    if (data.mode) {
      store.setMode(data.mode);
    }
  }, []);

  const scheduleReconnect = useCallback((delay) => {
    if (!mountedRef.current) return;

    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      const store = useBotStore.getState();
      store.setConnectionState('disconnected');
      store.setConnectionError('Max reconnection attempts reached');
      return;
    }

    reconnectAttemptsRef.current += 1;
    const store = useBotStore.getState();
    store.setConnectionState('reconnecting');

    console.log(
      `Reconnect attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS} in ${delay}ms`
    );

    reconnectTimeoutRef.current = setTimeout(() => {
      if (mountedRef.current) {
        // Signal to connect from useEffect
        wsRef.current = { needsConnect: true };
      }
    }, delay);
  }, []);

  const resetHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }

    heartbeatTimeoutRef.current = setTimeout(() => {
      if (mountedRef.current) {
        console.warn('Heartbeat timeout');
        scheduleReconnect(BASE_RECONNECT_DELAY);
      }
    }, HEARTBEAT_TIMEOUT);
  }, [scheduleReconnect]);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const store = useBotStore.getState();
    store.setConnectionState('connecting');
    store.setConnectionError(null);

    const protocol = API_BASE_URL.startsWith('https') ? 'wss' : 'ws';
    const wsHost = API_BASE_URL.replace(/https?:\/\//, '');
    const wsUrl = `${protocol}://${wsHost}/stream`;

    console.log('Connecting to:', wsUrl);

    // First check if API is healthy
    fetch(`${API_BASE_URL}/health`)
      .then(res => {
        if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
        return res.json();
      })
      .then(health => {
        if (!mountedRef.current) return;
        
        // Update health in store
        const st = useBotStore.getState();
        Object.entries(health).forEach(([source, status]) => {
          st.updateHealth(source, status);
        });

        // Now connect WebSocket
        try {
          const ws = new WebSocket(wsUrl);

          ws.onopen = () => {
            if (!mountedRef.current) return;
            console.log('WebSocket connected');
            reconnectAttemptsRef.current = 0;
            const st = useBotStore.getState();
            st.setConnectionState('connected');
            st.setConnectionError(null);
            resetHeartbeat();
          };

          ws.onmessage = (event) => {
            if (!mountedRef.current) return;
            try {
              const data = JSON.parse(event.data);
              handleStreamMessage(data);
              resetHeartbeat();
            } catch (err) {
              console.error('Failed to parse message:', err);
            }
          };

          ws.onerror = (err) => {
            console.error('WebSocket error:', err);
            const st = useBotStore.getState();
            st.setConnectionError('WebSocket connection failed');
          };

          ws.onclose = () => {
            if (mountedRef.current) {
              console.log('WebSocket closed');
              const delay = Math.min(
                BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current),
                30000
              );
              scheduleReconnect(delay);
            }
          };

          wsRef.current = ws;
        } catch (err) {
          console.error('Failed to create WebSocket:', err);
          const st = useBotStore.getState();
          st.setConnectionError(err.message);
          const delay = Math.min(
            BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current),
            30000
          );
          scheduleReconnect(delay);
        }
      })
      .catch(err => {
        if (!mountedRef.current) return;
        console.error('Health check failed:', err);
        const st = useBotStore.getState();
        st.setConnectionError('API server not responding');
        const delay = Math.min(
          BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current),
          30000
        );
        scheduleReconnect(delay);
      });
  }, [handleStreamMessage, resetHeartbeat, scheduleReconnect]);

  // Main effect for connection management
  useEffect(() => {
    mountedRef.current = true;
    connect();

    const checkInterval = setInterval(() => {
      if (wsRef.current?.needsConnect) {
        wsRef.current = null;
        connect();
      }
    }, 500);

    return () => {
      mountedRef.current = false;
      clearInterval(checkInterval);

      if (wsRef.current?.close) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (heartbeatTimeoutRef.current) {
        clearTimeout(heartbeatTimeoutRef.current);
      }
    };
  }, [connect]);

  const connectionState = useBotStore((state) => state.connectionState);
  const lastHeartbeat = useBotStore((state) => state.lastHeartbeat);
  const connectionError = useBotStore((state) => state.lastConnectionError);

  return {
    connectionState,
    lastHeartbeat,
    connectionError,
  };
}

export default useRealTimeData;
