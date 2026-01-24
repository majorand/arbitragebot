import { Save, RotateCcw, AlertCircle } from 'lucide-react';
import { useState, useEffect } from 'react';
import useBotStore from '../store/botStore';

const PRESET_CONFIGS = {
  conservative: {
    min_edge_pct: 2.0,
    max_stake: 25,
    max_exposure_per_market: 50,
    per_day_loss_limit: 200,
  },
  balanced: {
    min_edge_pct: 1.0,
    max_stake: 50,
    max_exposure_per_market: 100,
    per_day_loss_limit: 500,
  },
  aggressive: {
    min_edge_pct: 0.5,
    max_stake: 100,
    max_exposure_per_market: 250,
    per_day_loss_limit: 1000,
  },
};

export default function ConfigPanel({ onSave }) {
  const mode = useBotStore((state) => state.mode);
  const paperTradingBalance = useBotStore((state) => state.paperTradingBalance);
  const cashBalance = useBotStore((state) => state.metrics.cash_balance);
  
  const [formData, setFormData] = useState({
    min_edge_pct: 0.5,
    max_stake: 50,
    max_exposure_per_market: 100,
    per_day_loss_limit: 500,
    per_book_limit: {
      kalshi: 250,
      polymarket: 250,
    },
    paperTradingBalance: paperTradingBalance,
  });

  const [saveStatus, setSaveStatus] = useState(null);
  const [presetApplied, setPresetApplied] = useState(null);

  useEffect(() => {
    setFormData(prev => ({ ...prev, paperTradingBalance }));
  }, [paperTradingBalance]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setSaveStatus(null);
  };

  const handleBookLimitChange = (book, value) => {
    setFormData(prev => ({
      ...prev,
      per_book_limit: {
        ...prev.per_book_limit,
        [book]: value,
      },
    }));
    setSaveStatus(null);
  };

  const handleApplyPreset = (presetName) => {
    const preset = PRESET_CONFIGS[presetName];
    setFormData(prev => ({ ...prev, ...preset }));
    setPresetApplied(presetName);
    setSaveStatus(null);
  };

  const handleReset = () => {
    setFormData({
      min_edge_pct: 0.5,
      max_stake: 50,
      max_exposure_per_market: 100,
      per_day_loss_limit: 500,
      per_book_limit: {
        kalshi: 250,
        polymarket: 250,
      },
      paperTradingBalance: paperTradingBalance,
    });
    setPresetApplied(null);
    setSaveStatus(null);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Update paper trading balance in store if changed
    if (mode === 'paper' && formData.paperTradingBalance !== paperTradingBalance) {
      useBotStore.setState({ paperTradingBalance: formData.paperTradingBalance });
    }
    
    // Prepare config data for backend
    const configData = {
      min_edge_pct: formData.min_edge_pct,
      max_stake: formData.max_stake,
      max_exposure_per_market: formData.max_exposure_per_market,
      per_day_loss_limit: formData.per_day_loss_limit,
      per_book_limit: formData.per_book_limit,
    };
    
    // Call parent callback if provided
    if (onSave) {
      onSave(configData);
    }
    
    setSaveStatus('success');
    setTimeout(() => setSaveStatus(null), 3000);
  };

  return (
    <div className="card-dark p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white">Strategy Configuration</h2>
        {saveStatus === 'success' && (
          <span className="text-sm text-green-400 flex items-center gap-1">
            ✓ Saved successfully
          </span>
        )}
      </div>

      {/* Warning for mode */}
      {mode === 'live' && (
        <div className="bg-amber-900/30 border border-amber-600/50 rounded-lg p-4 mb-6 flex gap-3">
          <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-300">Live Mode Active</p>
            <p className="text-xs text-amber-200 mt-1">Configuration changes will affect real trading immediately.</p>
          </div>
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Trading Balance Section */}
        {mode === 'paper' && (
          <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-blue-300 uppercase mb-4">Paper Trading Balance</h3>
            <div>
              <label className="text-sm text-gray-400">Starting Cash ($)</label>
              <input
                type="number"
                value={formData.paperTradingBalance}
                onChange={(e) => handleChange('paperTradingBalance', parseFloat(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white mt-1 focus:outline-none focus:border-blue-500"
                min="0"
                step="100"
              />
              <p className="text-xs text-gray-500 mt-2">Virtual balance for paper trading</p>
            </div>
          </div>
        )}

        {mode === 'live' && (
          <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-green-300 uppercase mb-2">Live Trading Balance</h3>
            <p className="text-2xl font-bold text-green-400">${cashBalance.toFixed(2)}</p>
            <p className="text-xs text-gray-500 mt-2">Current connected balance</p>
          </div>
        )}

        {/* Arbitrage Detection Settings */}
        <div className="border border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-300 uppercase mb-4">Arbitrage Detection</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-400">Minimum Edge (%)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={formData.min_edge_pct}
                onChange={(e) => handleChange('min_edge_pct', parseFloat(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white mt-1 focus:outline-none focus:border-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">Only trade opportunities with at least this edge</p>
            </div>
          </div>
        </div>

        {/* Position Sizing */}
        <div className="border border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-300 uppercase mb-4">Position Sizing</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-400">Max Stake Per Trade ($)</label>
              <input
                type="number"
                value={formData.max_stake}
                onChange={(e) => handleChange('max_stake', parseFloat(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white mt-1 focus:outline-none focus:border-blue-500"
                min="1"
                step="10"
              />
              <p className="text-xs text-gray-500 mt-1">Maximum size per individual trade</p>
            </div>
            <div>
              <label className="text-sm text-gray-400">Max Exposure Per Market ($)</label>
              <input
                type="number"
                value={formData.max_exposure_per_market}
                onChange={(e) => handleChange('max_exposure_per_market', parseFloat(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white mt-1 focus:outline-none focus:border-blue-500"
                min="1"
                step="25"
              />
              <p className="text-xs text-gray-500 mt-1">Max total exposure per event</p>
            </div>
          </div>
        </div>

        {/* Risk Limits */}
        <div className="border border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-300 uppercase mb-4">Risk Limits</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-400">Daily Loss Limit ($)</label>
              <input
                type="number"
                value={formData.per_day_loss_limit}
                onChange={(e) => handleChange('per_day_loss_limit', parseFloat(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white mt-1 focus:outline-none focus:border-blue-500"
                min="0"
                step="50"
              />
              <p className="text-xs text-gray-500 mt-1">Stop trading if daily loss exceeds this amount</p>
            </div>
            <div>
              <label className="text-sm text-gray-400">DraftKings Exposure Limit ($)</label>
              <input
                type="number"
                value={formData.per_book_limit.draftkings}
                onChange={(e) => handleBookLimitChange('draftkings', parseFloat(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white mt-1 focus:outline-none focus:border-blue-500"
                min="0"
                step="25"
              />
              <p className="text-xs text-gray-500 mt-1">Max exposure on this venue</p>
            </div>
          </div>
        </div>

        {/* Preset Configurations */}
        <div>
          <h3 className="text-sm font-semibold text-gray-300 uppercase mb-3">Quick Presets</h3>
          <div className="grid grid-cols-3 gap-3">
            {[
              { name: 'conservative', label: '🛡️ Conservative', desc: 'Lower risk, higher edge requirement' },
              { name: 'balanced', label: '⚖️ Balanced', desc: 'Moderate risk and edge' },
              { name: 'aggressive', label: '⚡ Aggressive', desc: 'Higher volume, lower edge requirement' },
            ].map(preset => (
              <button
                key={preset.name}
                type="button"
                onClick={() => handleApplyPreset(preset.name)}
                className={`text-left p-3 rounded border-2 transition-all ${
                  presetApplied === preset.name
                    ? 'border-blue-500 bg-blue-900/30'
                    : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                }`}
              >
                <p className="text-sm font-semibold text-white">{preset.label}</p>
                <p className="text-xs text-gray-400 mt-1">{preset.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4 border-t border-gray-700">
          <button
            type="submit"
            className="button-primary flex items-center justify-center gap-2 flex-1 hover:bg-blue-600 transition-colors"
          >
            <Save className="w-4 h-4" />
            Save Configuration
          </button>
          <button
            type="button"
            onClick={handleReset}
            className="button-secondary flex items-center justify-center gap-2 px-4 hover:bg-gray-700 transition-colors"
            title="Reset to defaults"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
