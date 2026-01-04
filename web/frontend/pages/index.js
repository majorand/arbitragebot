import { useState } from 'react';
import Header from '../components/Header';
import BestOpportunity from '../components/BestOpportunity';
import OpportunitiesTable from '../components/OpportunitiesTable';
import PositionsView from '../components/PositionsView';
import TradeHistory from '../components/TradeHistory';
import HealthMonitor from '../components/HealthMonitor';
import ConfigPanel from '../components/ConfigPanel';
import useBotStore from '../store/botStore';
import useRealTimeData from '../hooks/useRealTimeData';
import { updateMode, submitTrade } from '../lib/api';
import { AlertCircle, WifiOff } from 'lucide-react';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('opportunities');
  const [error, setError] = useState('');

  // Subscribe to store updates (auto-rerender on changes)
  const mode = useBotStore((state) => state.mode);
  const opportunities = useBotStore((state) => state.opportunities);
  const bestOpportunity = useBotStore((state) => state.bestOpportunity);
  const positions = useBotStore((state) => state.positions);
  const trades = useBotStore((state) => state.trades);
  const metrics = useBotStore((state) => state.metrics);
  const health = useBotStore((state) => state.health);
  const connectionState = useBotStore((state) => state.connectionState);
  const connectionError = useBotStore((state) => state.lastConnectionError);
  const paperTradingBalance = useBotStore((state) => state.paperTradingBalance);

  // Use paper balance if in paper mode, otherwise use live balance
  const displayBalance = mode === 'paper' ? paperTradingBalance : metrics.cash_balance;

  // Initialize real-time data connection
  useRealTimeData();

  const handleModeChange = async (newMode) => {
    if (newMode === 'live') {
      const confirmed = window.confirm(
        '⚠️ WARNING: Switching to LIVE mode will execute real trades!\n\nContinue?'
      );
      if (!confirmed) return;
    }

    try {
      await updateMode(newMode);
      useBotStore.setState({ mode: newMode });
      setError('');
    } catch (err) {
      setError(`Failed to change mode: ${err.message}`);
    }
  };

  const handleTrade = async (opportunity) => {
    const stake = window.prompt(
      `Enter stake amount (Max $${Math.floor(displayBalance || 1000)}):`,
      '100'
    );
    if (!stake) return;

    try {
      await submitTrade({
        market_id: opportunity.market_id,
        side: opportunity.recommended_side || 'yes',
        stake: parseFloat(stake),
        exchange: opportunity.venue || 'kalshi',
      });
      setError('');
      // Store will update via real-time connection
    } catch (err) {
      setError(`Trade failed: ${err.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Connection Status Badge */}
      <div className="fixed top-4 right-4 z-50">
        <div
          className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
            connectionState === 'connected'
              ? 'bg-green-500/20 border border-green-500/50 text-green-300'
              : connectionState === 'connecting'
              ? 'bg-yellow-500/20 border border-yellow-500/50 text-yellow-300'
              : connectionState === 'reconnecting'
              ? 'bg-amber-500/20 border border-amber-500/50 text-amber-300'
              : 'bg-red-500/20 border border-red-500/50 text-red-300'
          }`}
        >
          {connectionState === 'connected' ? (
            <>
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              Live Connected
            </>
          ) : connectionState === 'connecting' ? (
            <>
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
              Connecting...
            </>
          ) : connectionState === 'reconnecting' ? (
            <>
              <div className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
              Reconnecting...
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4" />
              Disconnected
            </>
          )}
        </div>
        {connectionError && (
          <p className="text-xs text-red-400 mt-1 text-right max-w-xs">{connectionError}</p>
        )}
      </div>

      <Header
        mode={mode}
        onModeChange={handleModeChange}
        isHealthy={connectionState === 'connected'}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex gap-3 items-start animate-in">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-red-400 font-semibold">Error</p>
              <p className="text-red-300 text-sm">{error}</p>
            </div>
            <button
              onClick={() => setError('')}
              className="text-red-400 hover:text-red-300 flex-shrink-0"
            >
              ✕
            </button>
          </div>
        )}

        {/* Show content once connected or if we have data */}
        {connectionState === 'connecting' && opportunities.length === 0 ? (
          <div className="flex items-center justify-center min-h-96">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-gray-400">Connecting to live data stream...</p>
              {connectionError && (
                <p className="text-red-400 text-sm mt-2">{connectionError}</p>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Best Opportunity Card */}
            {bestOpportunity ? (
              <BestOpportunity
                opportunity={bestOpportunity}
                onExecute={() => handleTrade(bestOpportunity)}
                isLive={mode === 'live'}
              />
            ) : (
              <div className="p-8 bg-gray-800/30 border border-gray-700 rounded-lg text-center">
                <p className="text-gray-400">
                  {opportunities.length === 0
                    ? 'No opportunities currently available'
                    : 'Waiting for best opportunity...'}
                </p>
              </div>
            )}

            {/* Tab Navigation */}
            <div className="flex gap-4 border-b border-gray-800 overflow-x-auto">
              {[
                { id: 'opportunities', label: '📊 Opportunities' },
                { id: 'positions', label: '💼 Positions' },
                { id: 'history', label: '📜 Trade History' },
                { id: 'health', label: '🏥 Health' },
                { id: 'config', label: '⚙️ Config' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-400'
                      : 'border-transparent text-gray-400 hover:text-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="animate-fadeIn">
              {activeTab === 'opportunities' && (
                <OpportunitiesTable
                  opportunities={opportunities}
                  onTrade={handleTrade}
                  isLive={mode === 'live'}
                />
              )}

              {activeTab === 'positions' && <PositionsView positions={positions} />}

              {activeTab === 'history' && <TradeHistory trades={trades} />}

              {activeTab === 'health' && <HealthMonitor health={health} />}

              {activeTab === 'config' && (
                <ConfigPanel onSave={() => setError('')} />
              )}
            </div>

            {/* Metrics Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8 pt-8 border-t border-gray-800">
              <div className="p-4 bg-gray-800/30 rounded">
                <p className="text-gray-400 text-sm">Total Trades</p>
                <p className="text-2xl font-bold text-blue-400">{metrics.total_trades}</p>
              </div>
              <div className="p-4 bg-gray-800/30 rounded">
                <p className="text-gray-400 text-sm">Win Rate</p>
                <p className="text-2xl font-bold text-green-400">
                  {(metrics.win_rate * 100).toFixed(1)}%
                </p>
              </div>
              <div className={`p-4 rounded ${
                mode === 'paper' 
                  ? 'bg-blue-500/10 border border-blue-500/30' 
                  : 'bg-green-500/10 border border-green-500/30'
              }`}>
                <p className="text-gray-400 text-sm">
                  {mode === 'paper' ? 'Paper' : 'Live'} Balance
                </p>
                <p className="text-2xl font-bold text-amber-400">
                  ${displayBalance.toFixed(2)}
                </p>
              </div>
              <div className="p-4 bg-gray-800/30 rounded">
                <p className="text-gray-400 text-sm">Total PnL</p>
                <p
                  className={`text-2xl font-bold ${
                    metrics.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  ${metrics.total_pnl.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 border-t border-gray-800 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-gray-400 text-sm">
            🤖 Arbitrage Bot • Mode:{' '}
            <span className={mode === 'live' ? 'text-red-400 font-bold' : 'text-blue-400'}>
              {mode.toUpperCase()}
            </span>{' '}
            • Status:{' '}
            <span
              className={
                connectionState === 'connected'
                  ? 'text-green-400'
                  : connectionState === 'connecting'
                  ? 'text-yellow-400'
                  : 'text-red-400'
              }
            >
              {connectionState.toUpperCase()}
            </span>
          </p>
        </div>
      </footer>
    </div>
  );
}
