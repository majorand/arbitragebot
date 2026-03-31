import { ExternalLink, ArrowUpRight, Filter, SortDesc } from 'lucide-react';
import { useState } from 'react';

const REQUIRED_PROVIDERS = ['kalshi', 'polymarket'];

const isStrictBinaryOpportunity = (opp) => {
  const providers = opp?.providers || opp?.sources || [];
  if (!Array.isArray(providers)) return false;
  return REQUIRED_PROVIDERS.every((provider) =>
    providers.map((p) => (p || '').toLowerCase()).includes(provider)
  );
};

export default function OpportunitiesTable({ opportunities = [], sortBy = 'edge', filterEdge = 0 }) {
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

  return (
    <div className="card-dark p-6 animate-fadeInUp">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-white">Live Opportunities</h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            {sorted.length} FOUND
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Filter className="w-3 h-3 text-gray-500" />
            <label className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">Min Edge %</label>
          </div>
          <input
            type="number"
            value={minEdge}
            onChange={(e) => setMinEdge(parseFloat(e.target.value) || 0)}
            className="w-full"
            placeholder="0"
          />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-1.5 mb-1.5">
            <SortDesc className="w-3 h-3 text-gray-500" />
            <label className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">Sort By</label>
          </div>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="w-full"
          >
            <option value="edge">Highest Edge</option>
            <option value="volume">Highest Volume</option>
            <option value="time">Newest First</option>
            <option value="liquidity">Best Liquidity</option>
          </select>
        </div>
      </div>

      {/* Table */}
      {sorted.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-cyan-500/5 border border-cyan-500/20 flex items-center justify-center">
            <Filter className="w-6 h-6 text-cyan-900/60" />
          </div>
          <p className="text-gray-500 font-mono text-sm">No opportunities match filters</p>
          <p className="text-gray-600 text-xs mt-1">Try lowering the minimum edge %</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map((opp, idx) => {
            const isArb = opp.is_arbitrage || opp.edge >= 1.5;
            const eventLabel = opp.event_name || opp.event || 'Market';
            const providerSources = opp.providers || opp.sources || [];
            const normalizedProviders = Array.isArray(providerSources)
              ? providerSources.map((p) => (p || '').toUpperCase())
              : [];
            const sourcesLabel = normalizedProviders.length
              ? normalizedProviders.join(' ↔ ')
              : null;
            const bestYes = opp.best_yes || null;
            const bestNo = opp.best_no || null;
            const isHighEdge = (opp.edge || 0) >= 3;

            return (
              <div
                key={idx}
                className={`rounded-xl p-4 border transition-all duration-300 hover:translate-x-1 ${
                  isHighEdge
                    ? 'bg-green-500/5 border-green-500/20 hover:border-green-500/40'
                    : isArb
                    ? 'bg-cyan-500/5 border-cyan-500/15 hover:border-cyan-500/30'
                    : 'bg-[#0d1224]/60 border-cyan-900/20 hover:border-cyan-900/40'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Left: Event info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {isArb && (
                        <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                          isHighEdge
                            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                            : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                        }`}>
                          ARB
                        </span>
                      )}
                      <span className="text-[9px] font-mono text-gray-500 uppercase">
                        {(opp.sport || 'EVENT').toUpperCase()}
                      </span>
                    </div>
                    <p className="font-semibold text-white text-sm truncate">{eventLabel}</p>
                    {sourcesLabel && (
                      <p className="text-[10px] font-mono text-cyan-500/60 mt-1">{sourcesLabel}</p>
                    )}

                    {/* Best prices */}
                    <div className="flex flex-wrap gap-3 mt-2">
                      {bestYes?.provider && typeof bestYes.price === 'number' && (
                        <div className="text-[11px] font-mono">
                          <span className="text-gray-500">YES</span>{' '}
                          <span className="text-cyan-400">{bestYes.provider}</span>{' '}
                          <span className="text-white font-bold">{bestYes.price.toFixed(3)}</span>
                        </div>
                      )}
                      {bestNo?.provider && typeof bestNo.price === 'number' && (
                        <div className="text-[11px] font-mono">
                          <span className="text-gray-500">NO</span>{' '}
                          <span className="text-purple-400">{bestNo.provider}</span>{' '}
                          <span className="text-white font-bold">{bestNo.price.toFixed(3)}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Center: Edge */}
                  <div className="text-center px-4">
                    <p className={`text-2xl font-black font-mono ${
                      isHighEdge ? 'text-green-400' : isArb ? 'text-cyan-400' : 'text-gray-500'
                    }`}>
                      {(opp.edge || 0).toFixed(2)}%
                    </p>
                    <p className="text-[9px] font-mono text-gray-500 uppercase">Edge</p>
                  </div>

                  {/* Right: Trade links */}
                  <div className="flex flex-col gap-2 shrink-0">
                    {opp.links?.kalshi ? (
                      <a
                        href={opp.links.kalshi}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-mono font-semibold bg-cyan-500/10 border border-cyan-500/25 text-cyan-300 hover:bg-cyan-500/20 hover:border-cyan-500/50 transition-all"
                      >
                        Kalshi <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <a
                        href="https://kalshi.com"
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-mono font-semibold bg-cyan-500/10 border border-cyan-500/25 text-cyan-300 hover:bg-cyan-500/20 transition-all"
                      >
                        Kalshi <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                    {opp.links?.polymarket ? (
                      <a
                        href={opp.links.polymarket}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-mono font-semibold bg-purple-500/10 border border-purple-500/25 text-purple-300 hover:bg-purple-500/20 hover:border-purple-500/50 transition-all"
                      >
                        Polymarket <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <a
                        href="https://polymarket.com"
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-mono font-semibold bg-purple-500/10 border border-purple-500/25 text-purple-300 hover:bg-purple-500/20 transition-all"
                      >
                        Polymarket <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>

                {/* Stake allocation bar */}
                {isArb && opp.best_yes?.stake && opp.best_no?.stake && (
                  <div className="mt-3 pt-3 border-t border-cyan-900/20">
                    <div className="flex items-center gap-3 text-[10px] font-mono">
                      <span className="text-gray-500">ALLOCATION:</span>
                      <span className="text-cyan-400">{opp.best_yes.provider} ${opp.best_yes.stake?.toFixed(2)}</span>
                      <span className="text-gray-600">|</span>
                      <span className="text-purple-400">{opp.best_no.provider} ${opp.best_no.stake?.toFixed(2)}</span>
                      <span className="text-gray-600">|</span>
                      <span className="text-white">Total ${((opp.best_yes.stake || 0) + (opp.best_no.stake || 0)).toFixed(2)}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-cyan-900/20 flex items-center justify-between">
        <p className="text-[10px] font-mono text-gray-600">
          {sorted.length} of {opportunities.length} opportunities displayed
        </p>
        <p className="text-[10px] font-mono text-gray-600">
          Updated {new Date().toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
