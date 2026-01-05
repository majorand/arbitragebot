import { useState, useEffect } from 'react';
import { AlertCircle, Wifi, WifiOff } from 'lucide-react';
import { API_BASE_URL } from '../lib/api';

export default function HealthMonitor() {
  const [health, setHealth] = useState({
    kalshi: { status: 'connecting', latency: 0 },
    espn: { status: 'connecting', latency: 0 },
    supabase: { status: 'connecting', latency: 0 },
  });

  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const [healthRes, eventsRes] = await Promise.all([
          fetch(`${API_BASE_URL}/health`),
          fetch(`${API_BASE_URL}/events?limit=50`)
        ]);

        if (healthRes.ok) {
          const healthData = await healthRes.json();
          setHealth(healthData);
        }

        if (eventsRes.ok) {
          const eventsData = await eventsRes.json();
          setEvents(eventsData);
        }

        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch health/events:', error);
        setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const feeds = [
    { name: 'Kalshi API', key: 'kalshi', health: health.kalshi },
    { name: 'ESPN Feed', key: 'espn', health: health.espn },
    { name: 'Polymarket Feed', key: 'polymarket', health: health.polymarket },
    { name: 'Supabase DB', key: 'supabase', health: health.supabase },
  ];

  const formatTime = (isoString) => {
    if (!isoString) return '--:--:--';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString();
    } catch {
      return '--:--:--';
    }
  };

  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Data Feeds Status */}
      <div className="card-dark p-6">
        <h2 className="text-xl font-bold text-white mb-4">Data Feeds</h2>
        <div className="space-y-3">
          {feeds.map((feed) => {
            const isConnected = feed.health?.status === 'connected';
            const latency = feed.health?.latency || 0;

            return (
              <div key={feed.key} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                <div className="flex items-center gap-3">
                  {isConnected ? (
                    <Wifi className="w-5 h-5 text-green-400" />
                  ) : (
                    <WifiOff className="w-5 h-5 text-red-400" />
                  )}
                  <div>
                    <p className="font-medium text-white">{feed.name}</p>
                    <p className={`text-xs ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                      {isConnected ? 'Connected' : 'Disconnected'}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-mono text-gray-300">{latency}ms</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Events */}
      <div className="card-dark p-6">
        <h2 className="text-xl font-bold text-white mb-4">Recent Events</h2>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {events.length > 0 ? (
            events.map((event, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-lg border text-sm ${
                  event.type === 'success'
                    ? 'bg-green-500/10 border-green-500/30 text-green-300'
                    : event.type === 'warning'
                    ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-300'
                    : event.type === 'error'
                    ? 'bg-red-500/10 border-red-500/30 text-red-300'
                    : 'bg-blue-500/10 border-blue-500/30 text-blue-300'
                }`}
              >
                <div className="flex gap-2">
                  <span className="font-mono text-xs opacity-70">
                    {formatTime(event.timestamp)}
                  </span>
                  <span className="flex-1">{event.message}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="p-3 rounded-lg border bg-gray-800/50 border-gray-700 text-gray-400 text-sm">
              No events recorded yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

