import { Save, RotateCcw, Sliders } from 'lucide-react';
import { useState } from 'react';

const PRESET_CONFIGS = {
  conservative: {
    min_edge_pct: 3.0,
    description: 'Only show high-confidence opportunities (3%+ edge)',
  },
  balanced: {
    min_edge_pct: 1.5,
    description: 'Moderate filter - good balance of quality and quantity',
  },
  aggressive: {
    min_edge_pct: 0.5,
    description: 'Show all opportunities including thin edges',
  },
};

export default function ConfigPanel({ onSave }) {
  const [formData, setFormData] = useState({
    min_edge_pct: 0.5,
    refresh_interval: 30,
    notifications: true,
  });

  const [saveStatus, setSaveStatus] = useState(null);
  const [presetApplied, setPresetApplied] = useState(null);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setSaveStatus(null);
  };

  const handleApplyPreset = (presetName) => {
    const preset = PRESET_CONFIGS[presetName];
    setFormData(prev => ({ ...prev, min_edge_pct: preset.min_edge_pct }));
    setPresetApplied(presetName);
    setSaveStatus(null);
  };

  const handleReset = () => {
    setFormData({
      min_edge_pct: 0.5,
      refresh_interval: 30,
      notifications: true,
    });
    setPresetApplied(null);
    setSaveStatus(null);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSave) onSave(formData);
    setSaveStatus('success');
    setTimeout(() => setSaveStatus(null), 3000);
  };

  return (
    <div className="card-dark p-6 animate-fadeInUp">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Sliders className="w-5 h-5 text-cyan-500" />
          <h2 className="text-lg font-bold text-white">Scanner Settings</h2>
        </div>
        {saveStatus === 'success' && (
          <span className="text-xs font-mono text-green-400 flex items-center gap-1 px-2 py-1 rounded bg-green-500/10 border border-green-500/20">
            SAVED
          </span>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Detection Settings */}
        <div className="rounded-xl border border-cyan-900/20 p-5">
          <h3 className="text-[10px] font-mono font-bold text-cyan-500 uppercase tracking-wider mb-4">Detection Filters</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">Minimum Edge (%)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={formData.min_edge_pct}
                onChange={(e) => handleChange('min_edge_pct', parseFloat(e.target.value))}
                className="w-full mt-1.5"
              />
              <p className="text-[10px] text-gray-600 mt-1">Filter out opportunities below this edge</p>
            </div>
            <div>
              <label className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">Refresh Interval (s)</label>
              <input
                type="number"
                min="5"
                step="5"
                value={formData.refresh_interval}
                onChange={(e) => handleChange('refresh_interval', parseFloat(e.target.value))}
                className="w-full mt-1.5"
              />
              <p className="text-[10px] text-gray-600 mt-1">How often to scan for new opportunities</p>
            </div>
          </div>
        </div>

        {/* Presets */}
        <div>
          <h3 className="text-[10px] font-mono font-bold text-cyan-500 uppercase tracking-wider mb-3">Quick Presets</h3>
          <div className="grid grid-cols-3 gap-3">
            {[
              { name: 'conservative', label: 'Conservative', icon: '🛡' },
              { name: 'balanced', label: 'Balanced', icon: '⚖' },
              { name: 'aggressive', label: 'Aggressive', icon: '⚡' },
            ].map(preset => (
              <button
                key={preset.name}
                type="button"
                onClick={() => handleApplyPreset(preset.name)}
                className={`text-left p-4 rounded-xl border-2 transition-all duration-300 ${
                  presetApplied === preset.name
                    ? 'border-cyan-500/50 bg-cyan-500/10 glow-cyan'
                    : 'border-cyan-900/20 bg-[#0d1224]/60 hover:border-cyan-900/40'
                }`}
              >
                <p className="text-sm font-bold text-white">{preset.icon} {preset.label}</p>
                <p className="text-[10px] text-gray-500 mt-1">{PRESET_CONFIGS[preset.name].description}</p>
                <p className="text-[10px] font-mono text-cyan-400 mt-2">Min: {PRESET_CONFIGS[preset.name].min_edge_pct}%</p>
              </button>
            ))}
          </div>
        </div>

        {/* Info */}
        <div className="rounded-xl border border-cyan-900/20 bg-cyan-500/5 p-4">
          <p className="text-xs text-gray-400 leading-relaxed">
            <span className="text-cyan-400 font-bold font-mono">NOTE:</span> This scanner is display-only.
            It shows you where arbitrage opportunities exist across Kalshi and Polymarket.
            Use the links on each opportunity to manually place trades on the respective platforms.
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-4 border-t border-cyan-900/20">
          <button
            type="submit"
            className="button-primary flex items-center justify-center gap-2 flex-1"
          >
            <Save className="w-4 h-4" />
            Save Settings
          </button>
          <button
            type="button"
            onClick={handleReset}
            className="button-secondary flex items-center justify-center gap-2 px-4"
            title="Reset to defaults"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
