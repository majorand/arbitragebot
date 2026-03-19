import { ChevronDown, ChevronUp, ExternalLink, X } from 'lucide-react';
import { useState } from 'react';

/**
 * @typedef {import('../lib/opportunityTypes').BinaryOpportunity} BinaryOpportunity
 */

const REQUIRED_PROVIDERS = ['kalshi', 'polymarket'];

const isStrictBinaryOpportunity = (opp) => {
  const providers = opp?.providers || opp?.sources || [];
  if (!Array.isArray(providers)) return false;
  return REQUIRED_PROVIDERS.every((provider) =>
    providers.map((p) => (p || '').toLowerCase()).includes(provider)
  );
};

export default function OpportunitiesTable({ opportunities = [], onTrade, sortBy = 'volume', filterEdge = 0 }) {
  const [expandedId, setExpandedId] = useState(null);
  const [sort, setSort] = useState(sortBy);
  const [minEdge, setMinEdge] = useState(filterEdge);

  const filtered = opportunities.filter(
    (opp) => (opp.edge || 0) >= minEdge && isStrictBinaryOpportunity(opp)
  );
  
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
              {sorted.map((opp, idx) => {
                const isArb = opp.is_arbitrage || opp.edge >= 1.5;
                const eventLabel = opp.event_name || opp.event || 'Market';
                const selectionLabel = (opp.selection || opp.market_type || 'Selection')
                  .toString()
                  .replace(/_/g, ' ')
                  .replace(/\s+/g, ' ')
                  .trim()
                  .replace(/\b\w/g, (c) => c.toUpperCase());

                const providerSources = opp.providers || opp.sources || [];
                  const normalizedProviders = Array.isArray(providerSources)
                    ? providerSources.map((p) => (p || '').toUpperCase())
                    : [];
                  const sourcesLabel = normalizedProviders.length
                    ? normalizedProviders.join(' ↔ ')
                    : null;
                const marketLabel = (opp.market || selectionLabel || 'WIN')
                  .toString()
                  .replace(/_/g, ' ')
                  .replace(/\s+/g, ' ')
                  .trim()
                  .toUpperCase();
                const bestYes = opp.best_yes || null;
                const bestNo = opp.best_no || null;
                const hasBestSides = !!(bestYes && bestYes.provider && typeof bestYes.price === 'number') ||
                  !!(bestNo && bestNo.provider && typeof bestNo.price === 'number');

                return (
                  <tr key={idx} className={`border-b border-gray-800 hover:bg-gray-800/50 transition-colors ${isArb ? 'bg-green-500/5' : ''}`}>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-white">{eventLabel}</p>
                        <p className="text-xs text-gray-300">Market: {marketLabel}</p>
                        <p className="text-xs text-blue-400 mt-1">{(opp.sport || 'SPORTS').toUpperCase()} · {opp.venue || 'Exchange'}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {hasBestSides ? (
                        <div className="space-y-1">
                          {sourcesLabel && (
                            <p className="text-xs text-gray-300">Sources: {sourcesLabel}</p>
                          )}
                          {bestYes?.provider && typeof bestYes.price === 'number' && (
                            <p className="text-xs text-white">
                              Best YES: <span className="font-semibold">{bestYes.provider}</span> @ <span className="font-bold">{bestYes.price.toFixed(3)}</span>
                            </p>
                          )}
                          {opp.links && (opp.links.kalshi || opp.links.polymarket) && (
                            <div className="flex flex-wrap items-center gap-2 mt-2">
                              {opp.links.kalshi && (
                                <a
                                  href={opp.links.kalshi}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-[11px] text-blue-300 font-semibold flex items-center gap-1"
                                >
                                  Kalshi <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                              {opp.links.polymarket && (
                                <a
                                  href={opp.links.polymarket}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-[11px] text-purple-300 font-semibold flex items-center gap-1"
                                >
                                  Polymarket <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                            </div>
                          )}
                          {bestNo?.provider && typeof bestNo.price === 'number' && (
                            <p className="text-xs text-white">
                              Best NO: <span className="font-semibold">{bestNo.provider}</span> @ <span className="font-bold">{bestNo.price.toFixed(3)}</span>
                            </p>
                          )}
                        </div>
                      ) : isArb && opp.vs_source ? (
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
