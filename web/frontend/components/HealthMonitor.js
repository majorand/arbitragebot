import { AlertCircle, Wifi, WifiOff } from 'lucide-react';

export default function HealthMonitor({ health = {} }) {
  const feeds = [
    { name: 'Kalshi API', status: health.kalshi || 'connected', latency: 45 },
    { name: 'ESPN Feed', status: health.espn || 'connected', latency: 120 },
    { name: 'DraftKings API', status: health.draftkings || 'connected', latency: 85 },
    { name: 'Supabase DB', status: health.supabase || 'connected', latency: 25 },
  ];

  const recentEvents = [
    { time: '14:32:15', message: 'Fetched odds for 245 markets', type: 'info' },
    { time: '14:31:45', message: 'Placed order on Kalshi: $50 YES', type: 'success' },
    { time: '14:31:20', message: 'Detected arbitrage opportunity: 3.2% edge', type: 'info' },
    { time: '14:30:50', message: 'DraftKings request delayed (2.1s)', type: 'warning' },
    { time: '14:30:15', message: 'Paper mode: Simulated fill at $0.48', type: 'info' },
  ];

  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Data Feeds Status */}
      <div className="card-dark p-6">
        <h2 className="text-xl font-bold text-white mb-4">Data Feeds</h2>
        <div className="space-y-3">
          {feeds.map((feed, idx) => (
            <div key={idx} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg border border-gray-700">
              <div className="flex items-center gap-3">
                {feed.status === 'connected' ? (
                  <Wifi className="w-5 h-5 text-green-400" />
                ) : (
                  <WifiOff className="w-5 h-5 text-red-400" />
                )}
                <div>
                  <p className="font-medium text-white">{feed.name}</p>
                  <p className={`text-xs ${feed.status === 'connected' ? 'text-green-400' : 'text-red-400'}`}>
                    {feed.status === 'connected' ? 'Connected' : 'Disconnected'}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-mono text-gray-300">{feed.latency}ms</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Events */}
      <div className="card-dark p-6">
        <h2 className="text-xl font-bold text-white mb-4">Recent Events</h2>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {recentEvents.map((event, idx) => (
            <div key={idx} className={`p-3 rounded-lg border text-sm ${
              event.type === 'success' ? 'bg-green-500/10 border-green-500/30 text-green-300' :
              event.type === 'warning' ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-300' :
              event.type === 'error' ? 'bg-red-500/10 border-red-500/30 text-red-300' :
              'bg-blue-500/10 border-blue-500/30 text-blue-300'
            }`}>
              <div className="flex gap-2">
                <span className="font-mono text-xs opacity-70">{event.time}</span>
                <span className="flex-1">{event.message}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
