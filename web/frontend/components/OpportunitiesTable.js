import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { useState } from 'react';

export default function OpportunitiesTable({ opportunities = [], onTrade, sortBy = 'edge', filterEdge = 0 }) {
  const [expandedId, setExpandedId] = useState(null);
  const [sort, setSort] = useState(sortBy);
  const [minEdge, setMinEdge] = useState(filterEdge);

  const filtered = opportunities.filter(opp => opp.edge >= minEdge);
  
  const sorted = [...filtered].sort((a, b) => {
    switch (sort) {
      case 'edge':
        return b.edge - a.edge;
      case 'time':
        return new Date(b.time) - new Date(a.time);
      case 'liquidity':
        return (b.liquidity || 0) - (a.liquidity || 0);
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
                <th className="px-4 py-3 text-left text-gray-400 font-semibold">Event</th>
                <th className="px-4 py-3 text-left text-gray-400 font-semibold">Venues</th>
                <th className="px-4 py-3 text-right text-gray-400 font-semibold">Edge</th>
                <th className="px-4 py-3 text-right text-gray-400 font-semibold">Liquidity</th>
                <th className="px-4 py-3 text-center text-gray-400 font-semibold">Status</th>
                <th className="px-4 py-3 text-center text-gray-400 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((opp, idx) => (
                <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-white">{opp.event || 'Market'}</p>
                      <p className="text-xs text-gray-400">{opp.market || 'Market Type'}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-300">
                    {opp.venues || 'Kalshi, Draftkings'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-bold text-green-400">{(opp.edge || 0).toFixed(2)}%</span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    ${(opp.liquidity || 0).toFixed(0)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={getStatusColor(opp.status || 'new')}>
                      {opp.status || 'new'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => onTrade(opp)}
                      className="button-primary text-xs py-1 px-3"
                    >
                      Trade
                    </button>
                  </td>
                </tr>
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
