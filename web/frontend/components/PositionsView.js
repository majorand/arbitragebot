import { BarChart3, TrendingUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';

export default function PositionsView({ opportunities = [] }) {
  // Generate edge history from opportunities
  const edgeData = opportunities
    .filter(o => o.edge > 0)
    .slice(0, 10)
    .map((opp, i) => ({
      name: (opp.event_name || opp.event || 'Market').substring(0, 15) + '...',
      edge: opp.edge || 0,
    }));

  const avgEdge = edgeData.length > 0
    ? edgeData.reduce((sum, d) => sum + d.edge, 0) / edgeData.length
    : 0;

  const maxEdge = edgeData.length > 0
    ? Math.max(...edgeData.map(d => d.edge))
    : 0;

  const arbCount = opportunities.filter(o => o.is_arbitrage || (o.edge || 0) >= 1.5).length;

  return (
    <div className="grid md:grid-cols-2 gap-6 animate-fadeInUp">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card-dark p-4 glow-cyan">
          <p className="text-[9px] font-mono text-gray-500 uppercase tracking-wider">Active Arb Opps</p>
          <p className="text-3xl font-black font-mono text-cyan-400 mt-2">{arbCount}</p>
          <p className="text-[10px] font-mono text-gray-600 mt-1">Cross-platform</p>
        </div>

        <div className="card-dark p-4 glow-green">
          <p className="text-[9px] font-mono text-gray-500 uppercase tracking-wider">Avg Edge</p>
          <p className="text-3xl font-black font-mono text-green-400 mt-2">{avgEdge.toFixed(2)}%</p>
          <p className="text-[10px] font-mono text-gray-600 mt-1">Across opps</p>
        </div>

        <div className="card-dark p-4 glow-purple">
          <p className="text-[9px] font-mono text-gray-500 uppercase tracking-wider">Max Edge</p>
          <p className="text-3xl font-black font-mono text-purple-400 mt-2">{maxEdge.toFixed(2)}%</p>
          <p className="text-[10px] font-mono text-gray-600 mt-1">Best available</p>
        </div>

        <div className="card-dark p-4 glow-amber">
          <p className="text-[9px] font-mono text-gray-500 uppercase tracking-wider">Markets</p>
          <p className="text-3xl font-black font-mono text-amber-400 mt-2">{opportunities.length}</p>
          <p className="text-[10px] font-mono text-gray-600 mt-1">Total scanned</p>
        </div>
      </div>

      {/* Edge Chart */}
      <div className="card-dark p-4">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-4 h-4 text-cyan-500" />
          <h3 className="text-sm font-bold text-white font-mono">Edge Distribution</h3>
        </div>
        {edgeData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={edgeData}>
              <defs>
                <linearGradient id="edgeGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(56, 189, 248, 0.08)" />
              <XAxis dataKey="name" stroke="#4b5563" style={{ fontSize: '9px', fontFamily: 'monospace' }} />
              <YAxis stroke="#4b5563" style={{ fontSize: '10px', fontFamily: 'monospace' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0d1224',
                  border: '1px solid rgba(6, 182, 212, 0.3)',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                }}
                labelStyle={{ color: '#06b6d4' }}
              />
              <Area
                type="monotone"
                dataKey="edge"
                stroke="#06b6d4"
                strokeWidth={2}
                fill="url(#edgeGradient)"
                dot={{ fill: '#06b6d4', r: 3, strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-[200px] text-gray-600 font-mono text-xs">
            No edge data available
          </div>
        )}
      </div>

      {/* Info banner */}
      <div className="md:col-span-2 card-dark p-5">
        <div className="flex items-start gap-3">
          <TrendingUp className="w-5 h-5 text-cyan-500 mt-0.5 shrink-0" />
          <div>
            <h3 className="text-sm font-bold text-white mb-1">Display-Only Mode</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              This scanner detects real arbitrage opportunities across Kalshi and Polymarket.
              Click the exchange links on any opportunity to manually place your trades.
              The scanner updates in real-time as prices change across platforms.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
