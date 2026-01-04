import { useEffect, useRef, useCallback } from 'react';
import useBotStore from '../store/botStore';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

/**
 * Real-time data hook with WebSocket/SSE/REST polling support
 * Automatically reconnects on disconnect with exponential backoff
 * Updates store incrementally (no full-page reloads)
 */
export function useRealTimeData() {
  const storeRef = useRef(useBotStore.getState());
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const heartbeatTimeoutRef = useRef(null);

  const MAX_RECONNECT_ATTEMPTS = 10;
  const BASE_RECONNECT_DELAY = 1000; // 1 second
  const HEARTBEAT_TIMEOUT = 30000; // 30 seconds

  // Calculate exponential backoff
  const getReconnectDelay = useCallback(() => {
    return Math.min(
      BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current),
      30000 // Cap at 30 seconds
    );
  }, []);

  // Handle incoming stream messages
  const handleStreamMessage = useCallback((data) => {
    if (!data) return;

    const store = useBotStore.getState();

    // Update connection state
    store.setLastHeartbeat(new Date().toISOString());

    // Update opportunities
    if (data.opportunities && Array.isArray(data.opportunities)) {
      store.updateOpportunities(data.opportunities);
    }

    // Update single opportunity (for partial updates)
    if (data.opportunity) {
      store.updateOpportunity(data.opportunity.market_id, data.opportunity);
    }

    // Update positions
    if (data.positions && Array.isArray(data.positions)) {
      store.updatePositions(data.positions);
    }

    // Update single position
    if (data.position) {
      store.updatePosition(data.position.position_id, data.position);
    }

    // Add new trade
    if (data.trade) {
      store.addTrade(data.trade);
    }

    // Update trades list
    if (data.trades && Array.isArray(data.trades)) {
      store.updateTrades(data.trades);
    }

    // Update metrics
    if (data.metrics) {
      store.updateMetrics(data.metrics);
    }

    // Update health
    if (data.health) {
      Object.entries(data.health).forEach(([source, status]) => {
        store.updateHealth(source, status);
      });
    }

    // Update equity curve
    if (data.equity_curve && Array.isArray(data.equity_curve)) {
      store.updateEquityCurve(data.equity_curve);
    }

    // Add single equity point
    if (data.equity_point) {
      store.addEquityPoint(data.equity_point);
    }

    // Update mode
    if (data.mode) {
      store.setMode(data.mode);
    }
  }, []);

  // Reset heartbeat timeout
  const resetHeartbeatTimeout = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }

    heartbeatTimeoutRef.current = setTimeout(() => {
      console.warn('Heartbeat timeout - reconnecting');
      connectWebSocket();
    }, HEARTBEAT_TIMEOUT);
  }, []);

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    const store = useBotStore.getState();
    store.setConnectionState('connecting');
    store.setConnectionError(null);

    const protocol = API_BASE_URL.startsWith('https') ? 'wss' : 'ws';
    const wsHost = API_BASE_URL.replace(/https?:\/\//, '');
    const wsUrl = `${protocol}://${wsHost}/stream`;

    console.log('Connecting to:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        reconnectAttemptsRef.current = 0;
        const st = useBotStore.getState();
        st.setConnectionState('connected');
        st.setConnectionError(null);
        resetHeartbeatTimeout();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleStreamMessage(data);
          resetHeartbeatTimeout();
        } catch (err) {
          console.error('Failed to parse stream message:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        const st = useBotStore.getState();
        st.setConnectionError('WebSocket connection failed');
      };

      ws.onclose = () => {
        console.log('WebSocket closed, attempting reconnect...');
        if (heartbeatTimeoutRef.current) {
          clearTimeout(heartbeatTimeoutRef.current);
        }
        attemptReconnect();
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      const st = useBotStore.getState();
      st.setConnectionError(err.message);
      attemptReconnect();
    }
  }, [handleStreamMessage, resetHeartbeatTimeout, attemptReconnect]);

  // Try Server-Sent Events as fallback
  const connectSSE = useCallback(() => {
    const store = useBotStore.getState();
    store.setConnectionState('connecting');
    store.setConnectionError(null);

    console.log('Connecting to SSE:', `${API_BASE_URL}/stream`);

    const eventSource = new EventSource(`${API_BASE_URL}/stream`);

    eventSource.onopen = () => {
      console.log('SSE connected');
      reconnectAttemptsRef.current = 0;
      const st = useBotStore.getState();
      st.setConnectionState('connected');
      st.setConnectionError(null);
      resetHeartbeatTimeout();
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleStreamMessage(data);
        resetHeartbeatTimeout();
      } catch (err) {
        console.error('Failed to parse SSE message:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      eventSource.close();
      const st = useBotStore.getState();
      st.setConnectionError('SSE connection failed');
      attemptReconnect();
    };

    wsRef.current = eventSource;
  }, [handleStreamMessage, resetHeartbeatTimeout, attemptReconnect]);

  // Fallback to polling REST API
  const startPolling = useCallback(() => {
    const store = useBotStore.getState();
    store.setConnectionState('connected');
    console.log('Starting REST polling fallback');

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/state`, {
          signal: AbortSignal.timeout(5000),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        handleStreamMessage(data);
        const st = useBotStore.getState();
        st.setConnectionError(null);
      } catch (err) {
        console.error('Polling error:', err);
        const st = useBotStore.getState();
        st.setConnectionError(err.message);
      }
    }, 2000); // Poll every 2 seconds

    // Store interval ID for cleanup
    wsRef.current = { pollInterval, type: 'polling' };
  }, [handleStreamMessage]);

  // Attempt reconnection with backoff
  const attemptReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      console.error('Max reconnection attempts reached');
      const store = useBotStore.getState();
      store.setConnectionState('disconnected');
      store.setConnectionError('Max reconnection attempts reached');
      return;
    }

    const delay = getReconnectDelay();
    reconnectAttemptsRef.current += 1;

    console.log(
      `Reconnect attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS} in ${delay}ms`
    );

    const store = useBotStore.getState();
    store.setConnectionState('reconnecting');

    reconnectTimeoutRef.current = setTimeout(() => {
      connectWebSocket();
    }, delay);
  }, [getReconnectDelay, connectWebSocket]);

  // Initialize connection
  useEffect(() => {
    connectWebSocket();

    return () => {
      // Cleanup
      if (wsRef.current) {
        if (wsRef.current.type === 'polling') {
          clearInterval(wsRef.current.pollInterval);
        } else if (wsRef.current.close) {
          wsRef.current.close();
        }
      }

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      if (heartbeatTimeoutRef.current) {
        clearTimeout(heartbeatTimeoutRef.current);
      }
    };
  }, []);

  // Return connection state using hook instead of ref
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
