import { Save, RotateCcw } from 'lucide-react';
import { useState } from 'react';
import useBotStore from '../store/botStore';

export default function ConfigPanel({ config = {}, onSave }) {
  const mode = useBotStore((state) => state.mode);
  const paperTradingBalance = useBotStore((state) => state.paperTradingBalance);
  const cashBalance = useBotStore((state) => state.metrics.cash_balance);
  
  const [formData, setFormData] = useState({
    maxExposure: config.maxExposure || 5000,
    maxStakePerTrade: config.maxStakePerTrade || 500,
    minEdgePercent: config.minEdgePercent || 2.5,
    minLiquidity: config.minLiquidity || 1000,
    venues: config.venues || ['kalshi', 'draftkings', 'espn'],
    sports: config.sports || ['nfl', 'nba', 'mlb'],
    paperTradingBalance: paperTradingBalance,
    ...config,
  });

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (mode === 'paper' && formData.paperTradingBalance !== paperTradingBalance) {
      useBotStore.setState({ paperTradingBalance: formData.paperTradingBalance });
    }
    onSave(formData);
  };

  return (
    <div className="card-dark p-6">
      <h2 className="text-xl font-bold text-white mb-6">Strategy Configuration</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Trading Balance (Paper Mode Only) */}
        {mode === 'paper' && (
          <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-blue-300 uppercase mb-4">Paper Trading Balance</h3>
            <div>
              <label className="text-sm text-gray-400">Available Cash ($)</label>
              <input
                type="number"
                value={formData.paperTradingBalance}
                onChange={(e) => handleChange('paperTradingBalance', parseFloat(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white mt-1"
                min="0"
                step="100"
              />
              <p className="text-xs text-gray-500 mt-2">Set your starting balance for paper trading</p>
            </div>
          </div>
        )}

        {/* Current Balance Display (Live Mode) */}
        {mode === 'live' && (
          <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-green-300 uppercase mb-2">Live Trading Balance</h3>
            <p className="text-2xl font-bold text-green-400">${cashBalance.toFixed(2)}</p>
            <p className="text-xs text-gray-500 mt-2">Connected to live account - balance updates in real-time</p>
          </div>
        )}

        {/* Risk Controls */}
        <div>
          <h3 className="text-sm font-semibold text-gray-300 uppercase mb-4">Risk Controls</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-400">Max Total Exposure ($)</label>
              <input
                type="number"
                value={formData.maxExposure}
                onChange={(e) => handleChange('maxExposure', parseFloat(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white mt-1"
              />
            </div>
            <div>
              <label className="text-sm text-gray-400">Max Stake Per Trade ($)</label>
              <input
                type="number"
                value={formData.maxStakePerTrade}
                onChange={(e) => handleChange('maxStakePerTrade', parseFloat(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white mt-1"
              />
            </div>
            <div>
              <label className="text-sm text-gray-400">Minimum Edge (%)</label>
              <input
                type="number"
                step="0.1"
                value={formData.minEdgePercent}
                onChange={(e) => handleChange('minEdgePercent', parseFloat(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white mt-1"
              />
            </div>
            <div>
              <label className="text-sm text-gray-400">Minimum Liquidity ($)</label>
              <input
                type="number"
                value={formData.minLiquidity}
                onChange={(e) => handleChange('minLiquidity', parseFloat(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white mt-1"
              />
            </div>
          </div>
        </div>

        {/* Venues Selection */}
        <div>
          <h3 className="text-sm font-semibold text-gray-300 uppercase mb-4">Venues</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {['kalshi', 'draftkings', 'espn', 'fanduel'].map(venue => (
              <label key={venue} className="flex items-center gap-2 p-3 bg-gray-800 rounded border border-gray-700 hover:border-gray-600 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={formData.venues?.includes(venue) || false}
                  onChange={(e) => {
                    const updated = e.target.checked
                      ? [...(formData.venues || []), venue]
                      : (formData.venues || []).filter(v => v !== venue);
                    handleChange('venues', updated);
                  }}
                  className="w-4 h-4"
                />
                <span className="text-sm text-white capitalize">{venue}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Sports Selection */}
        <div>
          <h3 className="text-sm font-semibold text-gray-300 uppercase mb-4">Sports</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {['nfl', 'nba', 'mlb', 'nhl'].map(sport => (
              <label key={sport} className="flex items-center gap-2 p-3 bg-gray-800 rounded border border-gray-700 hover:border-gray-600 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={formData.sports?.includes(sport) || false}
                  onChange={(e) => {
                    const updated = e.target.checked
                      ? [...(formData.sports || []), sport]
                      : (formData.sports || []).filter(s => s !== sport);
                    handleChange('sports', updated);
                  }}
                  className="w-4 h-4"
                />
                <span className="text-sm text-white uppercase">{sport}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Preset Configs */}
        <div>
          <h3 className="text-sm font-semibold text-gray-300 uppercase mb-4">Presets</h3>
          <div className="grid grid-cols-3 gap-3">
            <button type="button" className="button-secondary text-sm">
              🔵 Conservative
            </button>
            <button type="button" className="button-secondary text-sm">
              ⚡ Aggressive
            </button>
            <button type="button" className="button-secondary text-sm">
              📄 Test
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4 border-t border-gray-700">
          <button
            type="submit"
            className="button-primary flex items-center justify-center gap-2 flex-1"
          >
            <Save className="w-4 h-4" />
            Save Configuration
          </button>
          <button
            type="button"
            className="button-secondary flex items-center justify-center gap-2"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
