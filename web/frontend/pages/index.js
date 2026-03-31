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
import { WifiOff, Radar, BarChart3, Clock, Activity, Settings } from 'lucide-react';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('opportunities');

  // Subscribe to store
  const opportunities = useBotStore((state) => state.opportunities);
  const bestOpportunity = useBotStore((state) => state.bestOpportunity);
  const connectionState = useBotStore((state) => state.connectionState);
  const connectionError = useBotStore((state) => state.lastConnectionError);

  // Initialize real-time data connection
  useRealTimeData();

  const arbOpps = opportunities.filter(o => o.is_arbitrage || (o.edge || 0) >= 1.5);
  const avgEdge = arbOpps.length > 0
    ? arbOpps.reduce((sum, o) => sum + (o.edge || 0), 0) / arbOpps.length
    : 0;

  const tabs = [
    { id: 'opportunities', label: 'Opportunities', icon: Radar },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'log', label: 'Detection Log', icon: Clock },
    { id: 'health', label: 'System', icon: Activity },
    { id: 'config', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-white grid-bg scanline">
      {/* Connection Status */}
      <div className="fixed top-4 right-4 z-50">
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono backdrop-blur-xl transition-all ${
            connectionState === 'connected'
              ? 'bg-green-500/10 border border-green-500/30 text-green-400'
              : connectionState === 'connecting'
              ? 'bg-cyan-500/10 border border-cyan-500/30 text-cyan-400'
              : connectionState === 'reconnecting'
              ? 'bg-amber-500/10 border border-amber-500/30 text-amber-400'
              : 'bg-red-500/10 border border-red-500/30 text-red-400'
          }`}
        >
          {connectionState === 'connected' ? (
            <>
              <div className="relative w-2 h-2">
                <div className="absolute inset-0 bg-green-400 rounded-full animate-ping opacity-75" />
                <div className="relative w-2 h-2 bg-green-400 rounded-full" />
              </div>
              LIVE
            </>
          ) : connectionState === 'connecting' ? (
            <>
              <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
              CONNECTING
            </>
          ) : connectionState === 'reconnecting' ? (
            <>
              <div className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
              RECONNECTING
            </>
          ) : (
            <>
              <WifiOff className="w-3 h-3" />
              OFFLINE
            </>
          )}
        </div>
      </div>

      <Header
        isHealthy={connectionState === 'connected'}
        stats={{
          opportunities: arbOpps.length,
          avg_edge: avgEdge,
          total_markets: opportunities.length,
        }}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Loading state */}
        {connectionState === 'connecting' && opportunities.length === 0 ? (
          <div className="flex items-center justify-center min-h-96">
            <div className="text-center">
              <div className="relative w-16 h-16 mx-auto mb-6">
                <div className="absolute inset-0 border-2 border-cyan-500/20 rounded-full" />
                <div className="absolute inset-0 border-2 border-transparent border-t-cyan-400 rounded-full animate-spin" />
                <div className="absolute inset-2 border-2 border-transparent border-t-purple-400 rounded-full animate-spin-slow" style={{ animationDirection: 'reverse' }} />
              </div>
              <p className="text-cyan-500/60 font-mono text-sm">INITIALIZING SCANNER...</p>
              <p className="text-gray-600 text-xs mt-2">Connecting to market feeds</p>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Best Opportunity */}
            <BestOpportunity opportunity={bestOpportunity} />

            {/* Tabs */}
            <div className="flex gap-1 p-1 bg-[#0d1224]/80 rounded-xl border border-cyan-900/20 overflow-x-auto">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium text-sm whitespace-nowrap transition-all duration-300 ${
                      activeTab === tab.id
                        ? 'bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                        : 'text-gray-500 hover:text-gray-300 border border-transparent'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Tab Content */}
            <div>
              {activeTab === 'opportunities' && (
                <OpportunitiesTable opportunities={opportunities} />
              )}
              {activeTab === 'analytics' && (
                <PositionsView opportunities={opportunities} />
              )}
              {activeTab === 'log' && (
                <TradeHistory opportunities={opportunities} />
              )}
              {activeTab === 'health' && <HealthMonitor />}
              {activeTab === 'config' && <ConfigPanel />}
            </div>

            {/* Bottom Stats Bar */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'ACTIVE ARBS', value: arbOpps.length, color: 'cyan' },
                { label: 'AVG EDGE', value: `${avgEdge.toFixed(2)}%`, color: 'green' },
                { label: 'MARKETS SCANNED', value: opportunities.length, color: 'purple' },
                { label: 'DATA FEEDS', value: connectionState === 'connected' ? '2/2' : '0/2', color: connectionState === 'connected' ? 'green' : 'red' },
              ].map((stat) => (
                <div key={stat.label} className={`card-dark p-4 text-center glow-${stat.color}`}>
                  <p className="text-[9px] font-mono text-gray-500 uppercase tracking-wider">{stat.label}</p>
                  <p className={`text-xl font-black font-mono mt-1 text-${stat.color === 'cyan' ? 'cyan' : stat.color === 'green' ? 'green' : stat.color === 'purple' ? 'purple' : stat.color === 'red' ? 'red' : 'amber'}-400`}>
                    {stat.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-cyan-900/15 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-mono text-gray-600">
              ARB SCANNER v1.0 &middot; Kalshi + Polymarket Cross-Platform Detection
            </p>
            <div className="flex items-center gap-2">
              <div className={`w-1.5 h-1.5 rounded-full ${connectionState === 'connected' ? 'bg-green-400' : 'bg-red-400'}`} />
              <p className="text-[10px] font-mono text-gray-600">
                {connectionState.toUpperCase()}
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
