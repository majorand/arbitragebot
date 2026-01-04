import { DollarSign, TrendingUp, TrendingDown } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function PositionsView({ positions = [] }) {
  const mockPnLData = [
    { date: 'Mon', value: 1000 },
    { date: 'Tue', value: 1250 },
    { date: 'Wed', value: 1100 },
    { date: 'Thu', value: 1450 },
    { date: 'Fri', value: 1380 },
    { date: 'Sat', value: 1520 },
    { date: 'Sun', value: 1680 },
  ];

  const totalRealizedPnL = positions.reduce((sum, p) => sum + (p.realizedPnL || 0), 0);
  const totalUnrealizedPnL = positions.reduce((sum, p) => sum + (p.unrealizedPnL || 0), 0);

  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card-dark p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-400 uppercase">Realized PnL</p>
              <p className={`text-2xl font-bold mt-2 ${totalRealizedPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                ${totalRealizedPnL.toFixed(2)}
              </p>
            </div>
            <TrendingUp className={`w-8 h-8 ${totalRealizedPnL >= 0 ? 'text-green-500' : 'text-red-500'}`} />
          </div>
        </div>

        <div className="card-dark p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-400 uppercase">Unrealized PnL</p>
              <p className={`text-2xl font-bold mt-2 ${totalUnrealizedPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                ${totalUnrealizedPnL.toFixed(2)}
              </p>
            </div>
            <DollarSign className={`w-8 h-8 ${totalUnrealizedPnL >= 0 ? 'text-green-500' : 'text-red-500'}`} />
          </div>
        </div>

        <div className="card-dark p-4">
          <p className="text-xs text-gray-400 uppercase">Open Positions</p>
          <p className="text-2xl font-bold mt-2 text-blue-400">{positions.length}</p>
        </div>

        <div className="card-dark p-4">
          <p className="text-xs text-gray-400 uppercase">Win Rate</p>
          <p className="text-2xl font-bold mt-2 text-blue-400">68%</p>
        </div>
      </div>

      {/* Chart */}
      <div className="card-dark p-4">
        <h3 className="text-sm font-semibold text-white mb-4">Equity Curve (7 days)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={mockPnLData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9ca3af" style={{ fontSize: '12px' }} />
            <YAxis stroke="#9ca3af" style={{ fontSize: '12px' }} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
              labelStyle={{ color: '#fff' }}
            />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke="#3b82f6" 
              strokeWidth={2} 
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Positions Table */}
      <div className="md:col-span-2 card-dark p-6">
        <h3 className="text-lg font-bold text-white mb-4">Open Positions</h3>
        {positions.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-400">No open positions</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="px-4 py-3 text-left text-gray-400 font-semibold">Instrument</th>
                  <th className="px-4 py-3 text-left text-gray-400 font-semibold">Direction</th>
                  <th className="px-4 py-3 text-right text-gray-400 font-semibold">Size</th>
                  <th className="px-4 py-3 text-right text-gray-400 font-semibold">Entry</th>
                  <th className="px-4 py-3 text-right text-gray-400 font-semibold">Current</th>
                  <th className="px-4 py-3 text-right text-gray-400 font-semibold">Unrealized PnL</th>
                  <th className="px-4 py-3 text-center text-gray-400 font-semibold">Mode</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, idx) => (
                  <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/50">
                    <td className="px-4 py-3 font-medium text-white">{pos.instrument}</td>
                    <td className="px-4 py-3">
                      <span className={`font-semibold ${pos.direction === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                        {pos.direction}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-300">{pos.size}</td>
                    <td className="px-4 py-3 text-right text-gray-300">${(pos.entryPrice || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 text-right text-gray-300">${(pos.currentPrice || 0).toFixed(2)}</td>
                    <td className={`px-4 py-3 text-right font-semibold ${(pos.unrealizedPnL || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      ${(pos.unrealizedPnL || 0).toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs font-semibold px-2 py-1 rounded ${
                        pos.mode === 'live' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'
                      }`}>
                        {pos.mode || 'paper'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
