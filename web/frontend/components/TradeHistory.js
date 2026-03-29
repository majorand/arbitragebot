import { Clock, ExternalLink, ArrowUpRight } from 'lucide-react';

export default function TradeHistory({ opportunities = [] }) {
  // Show recently detected opportunities as a log
  const recentOpps = opportunities
    .filter(o => o.edge > 0)
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    .slice(0, 20);

  return (
    <div className="card-dark p-6 animate-fadeInUp">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-white">Detection Log</h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            LIVE
          </span>
        </div>
        <p className="text-[10px] font-mono text-gray-600">Recent detections</p>
      </div>

      {recentOpps.length === 0 ? (
        <div className="text-center py-16">
          <Clock className="w-10 h-10 text-cyan-900/40 mx-auto mb-3" />
          <p className="text-gray-500 font-mono text-sm">No detections yet</p>
          <p className="text-gray-600 text-xs mt-1">Opportunities will appear here as they are detected</p>
        </div>
      ) : (
        <div className="space-y-2">
          {recentOpps.map((opp, idx) => {
            const isHighEdge = (opp.edge || 0) >= 3;
            const eventLabel = opp.event_name || opp.event || 'Market';
            const timeStr = opp.created_at
              ? new Date(opp.created_at).toLocaleTimeString()
              : '--:--:--';

            return (
              <div
                key={idx}
                className={`flex items-center gap-4 p-3 rounded-lg border transition-all ${
                  isHighEdge
                    ? 'bg-green-500/5 border-green-500/15'
                    : 'bg-[#0d1224]/60 border-cyan-900/15'
                }`}
              >
                {/* Time */}
                <span className="text-[10px] font-mono text-gray-500 w-16 shrink-0">{timeStr}</span>

                {/* Edge badge */}
                <span className={`text-xs font-mono font-bold w-14 text-center shrink-0 ${
                  isHighEdge ? 'text-green-400' : 'text-cyan-400'
                }`}>
                  {(opp.edge || 0).toFixed(2)}%
                </span>

                {/* Event */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white truncate">{eventLabel}</p>
                  <p className="text-[10px] font-mono text-gray-500">
                    {(opp.providers || []).map(p => p?.toUpperCase()).join(' ↔ ')}
                  </p>
                </div>

                {/* Links */}
                <div className="flex gap-1.5 shrink-0">
                  <a
                    href={opp.links?.kalshi || 'https://kalshi.com'}
                    target="_blank"
                    rel="noreferrer"
                    className="p-1.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 hover:bg-cyan-500/20 transition-all"
                    title="Open on Kalshi"
                  >
                    <ExternalLink className="w-3 h-3" />
                  </a>
                  <a
                    href={opp.links?.polymarket || 'https://polymarket.com'}
                    target="_blank"
                    rel="noreferrer"
                    className="p-1.5 rounded bg-purple-500/10 border border-purple-500/20 text-purple-400 hover:bg-purple-500/20 transition-all"
                    title="Open on Polymarket"
                  >
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
