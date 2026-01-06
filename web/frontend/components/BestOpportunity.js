import { TrendingUp, ChevronRight, ExternalLink } from 'lucide-react';

/**
 * @typedef {import('../lib/opportunityTypes').BinaryOpportunity} BinaryOpportunity
 */

export default function BestOpportunity({ opportunity, onExecute, onSkip, onIgnore, isLive }) {
  if (!opportunity) {
    return (
      <div className="card-dark p-6 border-dashed border-2 border-gray-700 flex items-center justify-center min-h-48">
        <div className="text-center">
          <TrendingUp className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No opportunities found</p>
          <p className="text-sm text-gray-500 mt-1">Monitor real-time odds to find arbitrage opportunities</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card-dark p-6 border border-blue-500/30 bg-gradient-to-r from-blue-900/20 to-transparent">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-blue-400" />
            Best Opportunity
          </h2>
          <p className="text-sm text-gray-400 mt-1">Execute in {isLive ? 'LIVE' : 'PAPER'} mode</p>
          <p className="text-xs text-blue-200 mt-1 uppercase tracking-widest">
            {opportunity.providers?.map((p) => p?.toUpperCase()).join(' ↔ ') || 'KALSHI ↔ FANATICS'}
          </p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-green-400">{opportunity.edge?.toFixed(2)}%</div>
          <div className="text-sm text-gray-400">Edge</div>
        </div>
      </div>

      {opportunity.legs && opportunity.legs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
          {opportunity.legs.map((leg, index) => {
            const legOdds = leg.decimal_odds ?? 0;
            const legStake = leg.recommended_stake ?? 0;
            const legReturn = leg.expected_return ?? 0;
            return (
              <div key={`${leg.provider}-${index}`} className="bg-gray-800/60 rounded-lg p-4 border border-gray-700">
                <p className="text-[11px] text-gray-400 uppercase tracking-wide">{leg.provider}</p>
                <p className="text-sm font-semibold text-white mt-1">{leg.selection}</p>
                <p className="text-[11px] text-gray-500 mt-1">
                  Odds: {legOdds.toFixed(3)} · Stake ${legStake.toFixed(2)}
                </p>
                <p className="text-[11px] text-green-300">Return: ${legReturn.toFixed(2)}</p>
              </div>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-800/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 uppercase">Market</p>
          <p className="text-sm font-semibold text-white mt-1">{opportunity.market || 'Market Name'}</p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 uppercase">Event</p>
          <p className="text-sm font-semibold text-white mt-1">{opportunity.event || 'Team vs Team'}</p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 uppercase">Venues</p>
          <p className="text-sm font-semibold text-white mt-1">{opportunity.venues || 'Kalshi, ESPN'}</p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 uppercase">EV (est.)</p>
          <p className="text-sm font-semibold text-green-400 mt-1">${opportunity.ev?.toFixed(2) || '0.00'}</p>
        </div>
      </div>

      <div className="bg-gray-800/30 rounded-lg p-4 mb-6 border border-gray-700">
        <p className="text-sm text-gray-300 mb-2"><span className="font-semibold">Recommendation:</span> {opportunity.recommendation || 'Buy YES on Kalshi'}</p>
        <p className="text-xs text-gray-400">{opportunity.reason || 'Implied probability difference detected'}</p>
      </div>

      {opportunity.links && (opportunity.links.kalshi || opportunity.links.fanatics) && (
        <div className="flex flex-wrap gap-3 text-xs text-gray-300 mb-6">
          {opportunity.links.kalshi && (
            <a
              href={opportunity.links.kalshi}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 text-blue-300 font-semibold"
            >
              Kalshi <ExternalLink className="w-3 h-3" />
            </a>
          )}
          {opportunity.links.fanatics && (
            <a
              href={opportunity.links.fanatics}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 text-purple-300 font-semibold"
            >
              Fanatics <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      )}

      <div className="grid grid-cols-3 gap-3">
        <button
          onClick={onExecute}
          className="button-primary w-full flex items-center justify-center gap-2"
        >
          <span>Execute Trade</span>
          <ChevronRight className="w-4 h-4" />
        </button>
        <button
          onClick={onSkip}
          className="button-secondary w-full"
        >
          Skip
        </button>
        <button
          onClick={onIgnore}
          className="button-secondary w-full"
        >
          Ignore
        </button>
      </div>
    </div>
  );
}
