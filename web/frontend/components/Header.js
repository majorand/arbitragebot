import { Activity, AlertTriangle, Power } from 'lucide-react';

export default function Header({ mode, onModeChange, isHealthy, stats }) {
  return (
    <header className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo and Title */}
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600/20 rounded-lg">
              <Activity className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Arbitrage Bot</h1>
              <p className="text-xs text-gray-400">Sports Betting Edge Finder</p>
            </div>
          </div>

          {/* Center Stats */}
          <div className="hidden md:flex items-center gap-8">
            <div className="text-center">
              <p className="text-xs text-gray-400">Total Trades</p>
              <p className="text-lg font-bold text-white">{stats?.total_trades || 0}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-400">Balance</p>
              <p className="text-lg font-bold text-green-400">${(stats?.cash_balance || 0).toFixed(2)}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-400">Open Positions</p>
              <p className="text-lg font-bold text-blue-400">{stats?.open_positions || 0}</p>
            </div>
          </div>

          {/* Right Controls */}
          <div className="flex items-center gap-4">
            {/* Health Indicator */}
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-sm text-gray-300">{isHealthy ? 'Healthy' : 'Error'}</span>
            </div>

            {/* Mode Toggle */}
            <div className="flex items-center gap-2 bg-gray-800 rounded-lg p-1">
              <button
                onClick={() => onModeChange('paper')}
                className={`px-4 py-1.5 rounded font-semibold text-sm transition-all ${
                  mode === 'paper'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                📄 PAPER
              </button>
              <button
                onClick={() => onModeChange('live')}
                className={`px-4 py-1.5 rounded font-semibold text-sm transition-all ${
                  mode === 'live'
                    ? 'bg-red-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                🔴 LIVE
              </button>
            </div>

            {/* Kill Switch */}
            <button className="p-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition-colors"
              title="Kill Switch - Cancel all orders">
              <Power className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
