import { useState, useEffect } from 'react';
import { Wifi, WifiOff, Activity, Server } from 'lucide-react';
import { API_BASE_URL } from '../lib/api';

export default function HealthMonitor() {
  const [health, setHealth] = useState({
    kalshi: { status: 'connecting', latency: 0 },
    polymarket: { status: 'connecting', latency: 0 },
    supabase: { status: 'connecting', latency: 0 },
  });

  const [events, setEvents] = useState([]);

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
      } catch (error) {
        console.error('Failed to fetch health/events:', error);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  const feeds = [
    { name: 'Kalshi API', key: 'kalshi', health: health.kalshi, icon: Server, color: 'cyan' },
    { name: 'Polymarket CLOB', key: 'polymarket', health: health.polymarket, icon: Activity, color: 'purple' },
    { name: 'Supabase DB', key: 'supabase', health: health.supabase, icon: Server, color: 'amber' },
  ];

  const formatTime = (isoString) => {
    if (!isoString) return '--:--:--';
    try {
      return new Date(isoString).toLocaleTimeString();
    } catch {
      return '--:--:--';
    }
  };

  return (
    <div className="grid md:grid-cols-2 gap-6 animate-fadeInUp">
      {/* Data Feeds */}
      <div className="card-dark p-6">
        <div className="flex items-center gap-2 mb-5">
          <Activity className="w-4 h-4 text-cyan-500" />
          <h2 className="text-lg font-bold text-white">Data Feeds</h2>
        </div>
        <div className="space-y-3">
          {feeds.map((feed) => {
            const isConnected = feed.health?.status === 'connected';
            const latency = feed.health?.latency ?? 0;
            const lastCheck = feed.health?.last_check;

            return (
              <div
                key={feed.key}
                className={`flex items-center justify-between p-4 rounded-xl border transition-all ${
                  isConnected
                    ? `bg-${feed.color === 'cyan' ? 'cyan' : feed.color === 'purple' ? 'purple' : 'amber'}-500/5 border-${feed.color === 'cyan' ? 'cyan' : feed.color === 'purple' ? 'purple' : 'amber'}-500/20`
                    : 'bg-red-500/5 border-red-500/20'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    isConnected ? 'bg-green-500/10' : 'bg-red-500/10'
                  }`}>
                    {isConnected ? (
                      <Wifi className="w-4 h-4 text-green-400" />
                    ) : (
                      <WifiOff className="w-4 h-4 text-red-400" />
                    )}
                  </div>
                  <div>
                    <p className="font-semibold text-white text-sm">{feed.name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={`text-[10px] font-mono font-bold ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                        {isConnected ? 'ONLINE' : 'OFFLINE'}
                      </span>
                      <span className="text-[10px] font-mono text-gray-600">
                        {lastCheck ? formatTime(lastCheck) : ''}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold font-mono text-white">{latency || '--'}<span className="text-xs text-gray-500">ms</span></p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Events Log */}
      <div className="card-dark p-6">
        <div className="flex items-center gap-2 mb-5">
          <Activity className="w-4 h-4 text-cyan-500" />
          <h2 className="text-lg font-bold text-white">System Events</h2>
        </div>
        <div className="space-y-2 max-h-72 overflow-y-auto">
          {events.length > 0 ? (
            events.map((event, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-lg border text-sm font-mono ${
                  event.type === 'success'
                    ? 'bg-green-500/5 border-green-500/15 text-green-300'
                    : event.type === 'warning'
                    ? 'bg-amber-500/5 border-amber-500/15 text-amber-300'
                    : event.type === 'error'
                    ? 'bg-red-500/5 border-red-500/15 text-red-300'
                    : 'bg-cyan-500/5 border-cyan-500/15 text-cyan-300'
                }`}
              >
                <div className="flex gap-2">
                  <span className="text-[10px] opacity-50 shrink-0">
                    {formatTime(event.timestamp)}
                  </span>
                  <span className="text-xs flex-1">{event.message}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="p-4 rounded-lg border bg-[#0d1224]/60 border-cyan-900/20 text-center">
              <p className="text-gray-600 font-mono text-xs">No events recorded</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
