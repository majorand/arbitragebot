import { TrendingUp, ChevronRight } from 'lucide-react';

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
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-green-400">{opportunity.edge?.toFixed(2)}%</div>
          <div className="text-sm text-gray-400">Edge</div>
        </div>
      </div>

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
