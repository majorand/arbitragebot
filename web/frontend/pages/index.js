import { useEffect, useState, useCallback } from 'react';
import Header from '../components/Header';
import BestOpportunity from '../components/BestOpportunity';
import OpportunitiesTable from '../components/OpportunitiesTable';
import PositionsView from '../components/PositionsView';
import TradeHistory from '../components/TradeHistory';
import HealthMonitor from '../components/HealthMonitor';
import ConfigPanel from '../components/ConfigPanel';
import {
  API_BASE_URL,
  fetchMode,
  fetchOdds,
  fetchPositions,
  fetchTrades,
  fetchMetrics,
  updateMode,
  submitTrade,
} from '../lib/api';
import { AlertCircle } from 'lucide-react';

const REFRESH_INTERVAL = 5000; // 5 seconds

export default function Dashboard() {
  const [mode, setMode] = useState('paper');
  const [opportunities, setOpportunities] = useState([]);
  const [bestOpportunity, setBestOpportunity] = useState(null);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [metrics, setMetrics] = useState({
    total_trades: 0,
    cash_balance: 0,
    open_positions: 0,
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [isHealthy, setIsHealthy] = useState(true);
  const [activeTab, setActiveTab] = useState('opportunities'); // opportunities, positions, health, config

  // Mock best opportunity (in production, this comes from backend)
  const generateBestOpportunity = useCallback((odds) => {
    if (!odds || odds.length === 0) return null;
    const best = odds.reduce((prev, curr) => 
      (curr.edge || 0) > (prev.edge || 0) ? curr : prev
    );
    return best.edge > 0 ? best : null;
  }, []);

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      const [modeRes, oddsRes, tradesRes, positionsRes, metricsRes] = await Promise.all([
        fetchMode().catch(() => ({ mode: 'paper' })),
        fetchOdds().catch(() => []),
        fetchTrades().catch(() => []),
        fetchPositions().catch(() => []),
        fetchMetrics().catch(() => ({})),
      ]);

      setMode(modeRes.mode || 'paper');
      setOpportunities(Array.isArray(oddsRes) ? oddsRes : []);
      setTrades(Array.isArray(tradesRes) ? tradesRes : []);
      setPositions(Array.isArray(positionsRes) ? positionsRes : []);
      setMetrics(metricsRes || {});
      setBestOpportunity(generateBestOpportunity(oddsRes));
      setError('');
      setIsHealthy(true);
    } catch (err) {
      console.error('Dashboard load error:', err);
      setError('Failed to load dashboard data');
      setIsHealthy(false);
    } finally {
      setLoading(false);
    }
  }, [generateBestOpportunity]);

  // Initial load
  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(loadDashboard, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [loadDashboard]);

  const handleModeChange = async (newMode) => {
    if (newMode === 'live') {
      // Confirmation dialog for live mode
      const confirmed = window.confirm(
        '⚠️ WARNING: Switching to LIVE mode will execute real trades!\n\nContinue?'
      );
      if (!confirmed) return;
    }

    try {
      await updateMode(newMode);
      setMode(newMode);
      setError('');
    } catch (err) {
      setError(`Failed to change mode: ${err.message}`);
    }
  };

  const handleTrade = async (opportunity) => {
    const stake = window.prompt(`Enter stake amount (Max $${metrics.cash_balance || 1000}):`, '100');
    if (!stake) return;

    try {
      await submitTrade({
        market_id: opportunity.market_id,
        side: opportunity.recommended_side || 'yes',
        stake: parseFloat(stake),
        exchange: 'kalshi',
      });
      setError('');
      loadDashboard();
    } catch (err) {
      setError(`Trade failed: ${err.message}`);
    }
  };

  const handleExecuteBestOpportunity = async () => {
    if (bestOpportunity) {
      handleTrade(bestOpportunity);
    }
  };

  const handleSkipOpportunity = () => {
    setOpportunities(opp => opp.filter(o => o !== bestOpportunity));
    const remaining = opportunities.filter(o => o !== bestOpportunity);
    setBestOpportunity(generateBestOpportunity(remaining));
  };

  const handleIgnoreOpportunity = () => {
    handleSkipOpportunity();
  };

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <Header 
        mode={mode} 
        onModeChange={handleModeChange}
        isHealthy={isHealthy}
        stats={metrics}
      />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex gap-3 items-start">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-400 font-semibold">Error</p>
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="flex items-center justify-center min-h-96">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Best Opportunity (Always visible) */}
            <BestOpportunity 
              opportunity={bestOpportunity}
              onExecute={handleExecuteBestOpportunity}
              onSkip={handleSkipOpportunity}
              onIgnore={handleIgnoreOpportunity}
              isLive={mode === 'live'}
            />

            {/* Tab Navigation */}
            <div className="flex gap-4 border-b border-gray-800 overflow-x-auto">
              {[
                { id: 'opportunities', label: '🎯 Opportunities' },
                { id: 'positions', label: '💼 Positions & PnL' },
                { id: 'health', label: '🏥 Health Monitor' },
                { id: 'config', label: '⚙️ Configuration' },
              ].map(tab => (
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
            <div className="animate-fade-in">
              {activeTab === 'opportunities' && (
                <OpportunitiesTable 
                  opportunities={opportunities}
                  onTrade={handleTrade}
                  sortBy="edge"
                  filterEdge={2.0}
                />
              )}

              {activeTab === 'positions' && (
                <PositionsView positions={positions} />
              )}

              {activeTab === 'health' && (
                <HealthMonitor health={{ 
                  kalshi: isHealthy ? 'connected' : 'disconnected',
                  espn: 'connected',
                  draftkings: 'connected',
                  supabase: isHealthy ? 'connected' : 'disconnected',
                }} />
              )}

              {activeTab === 'config' && (
                <ConfigPanel 
                  config={{
                    maxExposure: 5000,
                    maxStakePerTrade: 500,
                    minEdgePercent: 2.5,
                    minLiquidity: 1000,
                    venues: ['kalshi', 'draftkings'],
                    sports: ['nfl', 'nba', 'mlb'],
                  }}
                  onSave={(config) => {
                    console.log('Config saved:', config);
                    setError('');
                  }}
                />
              )}
            </div>

            {/* Trade History (always visible at bottom) */}
            <TradeHistory trades={trades} />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 border-t border-gray-800 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-gray-400 text-sm">
            🚀 Arbitrage Bot • Mode: <span className={mode === 'live' ? 'text-red-400' : 'text-blue-400'}>
              {mode.toUpperCase()}
            </span> • Last updated: {new Date().toLocaleTimeString()}
          </p>
        </div>
      </footer>
    </div>
  );
}
