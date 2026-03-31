import { Activity, Zap, Radio } from 'lucide-react';

export default function Header({ isHealthy, stats }) {
  return (
    <header className="sticky top-0 z-40 border-b border-cyan-500/10 bg-[#0a0e1a]/90 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="relative p-2.5 rounded-xl bg-gradient-to-br from-cyan-500/20 to-purple-500/20 border border-cyan-500/20">
              <Activity className="w-6 h-6 text-cyan-400" />
              <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-cyan-400 rounded-full animate-pulse" />
            </div>
            <div>
              <h1 className="text-lg font-bold gradient-text tracking-tight">ARB SCANNER</h1>
              <p className="text-[10px] text-cyan-500/60 uppercase tracking-[0.2em] font-mono">Cross-Platform Edge Detection</p>
            </div>
          </div>

          {/* Center Stats */}
          <div className="hidden md:flex items-center gap-1">
            {[
              { label: 'OPPORTUNITIES', value: stats?.opportunities || 0, color: 'text-cyan-400' },
              { label: 'AVG EDGE', value: `${(stats?.avg_edge || 0).toFixed(1)}%`, color: 'text-green-400' },
              { label: 'MARKETS', value: stats?.total_markets || 0, color: 'text-purple-400' },
            ].map((stat) => (
              <div key={stat.label} className="px-4 py-1 text-center border-r border-cyan-900/30 last:border-0">
                <p className="text-[9px] text-gray-500 uppercase tracking-wider font-mono">{stat.label}</p>
                <p className={`text-sm font-bold font-mono ${stat.color}`}>{stat.value}</p>
              </div>
            ))}
          </div>

          {/* Status */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#0d1224] border border-cyan-500/20">
              {isHealthy ? (
                <>
                  <Radio className="w-3.5 h-3.5 text-green-400 animate-pulse" />
                  <span className="text-xs font-mono text-green-400">SCANNING</span>
                </>
              ) : (
                <>
                  <Radio className="w-3.5 h-3.5 text-red-400" />
                  <span className="text-xs font-mono text-red-400">OFFLINE</span>
                </>
              )}
            </div>
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
              <Zap className="w-4 h-4 text-cyan-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Animated bottom border */}
      <div className="h-[1px] w-full data-flow-line" />
    </header>
  );
}
