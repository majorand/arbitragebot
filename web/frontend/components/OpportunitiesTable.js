import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { useState } from 'react';

export default function OpportunitiesTable({ opportunities = [], onTrade, sortBy = 'volume', filterEdge = 0 }) {
  const [expandedId, setExpandedId] = useState(null);
  const [sort, setSort] = useState(sortBy);
  const [minEdge, setMinEdge] = useState(filterEdge);

  const filtered = opportunities.filter(opp => opp.edge >= minEdge);
  
  const sorted = [...filtered].sort((a, b) => {
    switch (sort) {
      case 'edge':
        return b.edge - a.edge;
      case 'time':
        return new Date(b.created_at || 0) - new Date(a.created_at || 0);
      case 'liquidity':
        return (b.liquidity || 0) - (a.liquidity || 0);
      case 'volume':
        return (b.volume || b.liquidity || 0) - (a.volume || a.liquidity || 0);
      default:
        return 0;
    }
  });

  const getStatusColor = (status) => {
    switch (status) {
      case 'new':
        return 'status-info';
      case 'filled':
        return 'status-success';
      case 'pending':
        return 'status-warning';
      case 'rejected':
        return 'status-danger';
      default:
        return 'status-info';
    }
  };

  return (
    <div className="card-dark p-6">
      <h2 className="text-xl font-bold text-white mb-4">Opportunities</h2>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1">
          <label className="text-sm text-gray-400">Minimum Edge (%)</label>
          <input
            type="number"
            value={minEdge}
            onChange={(e) => setMinEdge(parseFloat(e.target.value))}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm mt-1"
            placeholder="0"
          />
        </div>
        <div className="flex-1">
          <label className="text-sm text-gray-400">Sort By</label>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm mt-1"
          >
            <option value="volume">Highest Trading Volume</option>
            <option value="edge">Highest Edge</option>
            <option value="time">Newest First</option>
            <option value="liquidity">Best Liquidity</option>
          </select>
        </div>
      </div>

      {/* Table */}
      {sorted.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-400">No opportunities match your filters</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="px-4 py-3 text-left text-gray-400 font-semibold">Event & Market</th>
                <th className="px-4 py-3 text-left text-gray-400 font-semibold">Arbitrage Details</th>
                <th className="px-4 py-3 text-right text-gray-400 font-semibold">ROI %</th>
                <th className="px-4 py-3 text-right text-gray-400 font-semibold">Stake Allocation</th>
                <th className="px-4 py-3 text-center text-gray-400 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((opp, idx) => (
              {sorted.map((opp, idx) => {
                const isArb = opp.is_arbitrage || opp.edge >= 1.5;
                
                return (
                  <tr key={idx} className={`border-b border-gray-800 hover:bg-gray-800/50 transition-colors ${isArb ? 'bg-green-500/5' : ''}`}>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-white">{opp.event_name || opp.event || 'Market'}</p>
                        <p className="text-xs text-gray-400">{opp.selection || opp.market || 'Market Type'}</p>
                        <p className="text-xs text-blue-400 mt-1">{(opp.sport || 'SPORTS').toUpperCase()} · {opp.venue || 'Exchange'}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {isArb && opp.vs_source ? (
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono bg-blue-500/20 text-blue-300 px-2 py-1 rounded">
                              Kalshi: {opp.selection}
                            </span>
                            <span className="text-xs text-gray-500">@</span>
                            <span className="text-xs font-bold text-white">${opp.price?.toFixed(2)}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono bg-purple-500/20 text-purple-300 px-2 py-1 rounded">
                              {opp.vs_source}: {opp.vs_selection}
                            </span>
                            <span className="text-xs text-gray-500">@</span>
                            <span className="text-xs font-bold text-white">
                              {opp.vs_american_odds > 0 ? '+' : ''}{opp.vs_american_odds?.toFixed(0)}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">No arbitrage detected</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`font-bold text-lg ${isArb ? 'text-green-400' : 'text-gray-400'}`}>
                        {(opp.edge || opp.roi_percentage || 0).toFixed(2)}%
                      </span>
                      {isArb && (
                        <p className="text-xs text-green-300 mt-1">✓ Arbitrage</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {isArb && opp.stake_kalshi ? (
                        <div className="space-y-1">
                          <p className="text-sm text-white">
                            Kalshi: <span className="font-bold">${opp.stake_kalshi}</span>
                          </p>
                          <p className="text-sm text-white">
                            {opp.vs_source}: <span className="font-bold">${opp.stake_other}</span>
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            Total: ${(opp.stake_kalshi + opp.stake_other).toFixed(2)}
                          </p>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => onTrade(opp)}
                        className={`text-xs py-1 px-3 rounded ${
                          isArb
                            ? 'bg-green-500 hover:bg-green-600 text-white font-bold'
                            : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                        }`}
                      >
                        {isArb ? '⚡ Execute' : 'View'}
                      </button>
                    </td>
                  </tr>
                );
              })}
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-400">
        Showing {sorted.length} of {opportunities.length} opportunities
      </div>
    </div>
  );
}
