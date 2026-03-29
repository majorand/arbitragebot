import { TrendingUp, ExternalLink, Crosshair, ArrowUpRight } from 'lucide-react';

export default function BestOpportunity({ opportunity }) {
  if (!opportunity) {
    return (
      <div className="card-dark p-8 border-dashed border-2 border-cyan-900/30 flex items-center justify-center min-h-48">
        <div className="text-center">
          <Crosshair className="w-12 h-12 text-cyan-900/40 mx-auto mb-3 animate-pulse" />
          <p className="text-gray-500 font-mono text-sm">SCANNING FOR ARBITRAGE...</p>
          <p className="text-xs text-gray-600 mt-1">Monitoring Kalshi & Polymarket in real-time</p>
        </div>
      </div>
    );
  }

  const edgeValue = opportunity.edge?.toFixed(2) || '0.00';
  const isHighEdge = (opportunity.edge || 0) >= 3;

  return (
    <div className={`card-dark p-6 relative overflow-hidden animate-fadeInUp ${isHighEdge ? 'glow-green' : 'glow-cyan'}`}>
      {/* Shimmer overlay */}
      <div className="absolute inset-0 shimmer pointer-events-none" />

      {/* Header row */}
      <div className="relative flex items-start justify-between mb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className={`w-2 h-2 rounded-full ${isHighEdge ? 'bg-green-400' : 'bg-cyan-400'} animate-pulse`} />
            <span className="text-[10px] font-mono text-cyan-500/80 uppercase tracking-[0.15em]">Top Opportunity</span>
          </div>
          <h2 className="text-xl font-bold text-white">{opportunity.event_name || opportunity.event || 'Market'}</h2>
          <p className="text-xs text-cyan-400/60 font-mono mt-1 uppercase tracking-widest">
            {opportunity.providers?.map((p) => p?.toUpperCase()).join(' ↔ ') || 'KALSHI ↔ POLYMARKET'}
          </p>
        </div>
        <div className="text-right">
          <div className={`text-4xl font-black font-mono ${isHighEdge ? 'text-green-400 text-glow-green' : 'text-cyan-400 text-glow-cyan'}`}>
            {edgeValue}%
          </div>
          <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">Edge Detected</div>
        </div>
      </div>

      {/* Legs */}
      {opportunity.legs && opportunity.legs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
          {opportunity.legs.map((leg, index) => {
            const legOdds = leg.decimal_odds ?? 0;
            const legStake = leg.recommended_stake ?? 0;
            const legReturn = leg.expected_return ?? 0;
            const isKalshi = (leg.provider || '').toLowerCase().includes('kalshi');
            return (
              <div key={`${leg.provider}-${index}`} className={`rounded-lg p-4 border ${
                isKalshi
                  ? 'bg-cyan-500/5 border-cyan-500/20'
                  : 'bg-purple-500/5 border-purple-500/20'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-[10px] font-mono uppercase tracking-wider ${
                    isKalshi ? 'text-cyan-400' : 'text-purple-400'
                  }`}>{leg.provider}</span>
                  <span className="text-[10px] font-mono text-gray-500">LEG {index + 1}</span>
                </div>
                <p className="text-sm font-semibold text-white">{leg.selection}</p>
                <div className="flex items-center gap-3 mt-2 text-[11px] font-mono text-gray-400">
                  <span>Odds: <span className="text-white">{legOdds.toFixed(3)}</span></span>
                  <span>Stake: <span className="text-white">${legStake.toFixed(2)}</span></span>
                </div>
                <p className="text-[11px] font-mono text-green-400 mt-1">Return: ${legReturn.toFixed(2)}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Details grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        {[
          { label: 'Market', value: opportunity.market || 'Binary' },
          { label: 'Sport', value: (opportunity.sport || 'Event').toUpperCase() },
          { label: 'Best YES', value: opportunity.best_yes ? `${opportunity.best_yes.provider} @ ${opportunity.best_yes.price?.toFixed(3)}` : '--' },
          { label: 'Best NO', value: opportunity.best_no ? `${opportunity.best_no.provider} @ ${opportunity.best_no.price?.toFixed(3)}` : '--' },
        ].map((item) => (
          <div key={item.label} className="bg-[#0a0e1a]/60 rounded-lg p-3 border border-cyan-900/20">
            <p className="text-[9px] font-mono text-gray-500 uppercase tracking-wider">{item.label}</p>
            <p className="text-sm font-semibold text-white mt-1 truncate">{item.value}</p>
          </div>
        ))}
      </div>

      {/* Recommendation */}
      {opportunity.recommendation && (
        <div className="bg-cyan-500/5 rounded-lg p-4 mb-5 border border-cyan-500/15">
          <p className="text-xs font-mono text-cyan-300">
            <span className="text-cyan-500 font-bold">SIGNAL:</span> {opportunity.recommendation}
          </p>
          {opportunity.reason && (
            <p className="text-[11px] text-gray-500 mt-1">{opportunity.reason}</p>
          )}
        </div>
      )}

      {/* Trade Links - DISPLAY ONLY */}
      <div className="flex flex-wrap gap-3">
        {opportunity.links?.kalshi && (
          <a
            href={opportunity.links.kalshi}
            target="_blank"
            rel="noreferrer"
            className="flex-1 flex items-center justify-center gap-2 px-5 py-3 rounded-lg font-semibold text-sm transition-all duration-300 bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 hover:border-cyan-500/50 hover:shadow-[0_0_20px_rgba(6,182,212,0.2)]"
          >
            <ArrowUpRight className="w-4 h-4" />
            Trade on Kalshi
            <ExternalLink className="w-3.5 h-3.5 opacity-50" />
          </a>
        )}
        {opportunity.links?.polymarket && (
          <a
            href={opportunity.links.polymarket}
            target="_blank"
            rel="noreferrer"
            className="flex-1 flex items-center justify-center gap-2 px-5 py-3 rounded-lg font-semibold text-sm transition-all duration-300 bg-purple-500/10 border border-purple-500/30 text-purple-300 hover:bg-purple-500/20 hover:border-purple-500/50 hover:shadow-[0_0_20px_rgba(139,92,246,0.2)]"
          >
            <ArrowUpRight className="w-4 h-4" />
            Trade on Polymarket
            <ExternalLink className="w-3.5 h-3.5 opacity-50" />
          </a>
        )}
        {!opportunity.links?.kalshi && !opportunity.links?.polymarket && (
          <>
            <a
              href="https://kalshi.com"
              target="_blank"
              rel="noreferrer"
              className="flex-1 flex items-center justify-center gap-2 px-5 py-3 rounded-lg font-semibold text-sm transition-all duration-300 bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20"
            >
              <ArrowUpRight className="w-4 h-4" />
              Open Kalshi
              <ExternalLink className="w-3.5 h-3.5 opacity-50" />
            </a>
            <a
              href="https://polymarket.com"
              target="_blank"
              rel="noreferrer"
              className="flex-1 flex items-center justify-center gap-2 px-5 py-3 rounded-lg font-semibold text-sm transition-all duration-300 bg-purple-500/10 border border-purple-500/30 text-purple-300 hover:bg-purple-500/20"
            >
              <ArrowUpRight className="w-4 h-4" />
              Open Polymarket
              <ExternalLink className="w-3.5 h-3.5 opacity-50" />
            </a>
          </>
        )}
      </div>
    </div>
  );
}
