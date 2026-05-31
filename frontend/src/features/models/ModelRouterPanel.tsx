import React, { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api/client';

interface ModelEntry {
  id: string;
  name: string;
  provider: string;
  enabled: boolean;
  priority: number;
  max_tokens?: number;
  cost_per_1k?: number;
  tags?: string[];
}

interface FallbackChain {
  task_type: string;
  chain: string[];
}

interface RouterConfig {
  strategy: 'priority' | 'round_robin' | 'least_latency' | 'cheapest';
  models: ModelEntry[];
  fallback_chains: FallbackChain[];
  default_model: string;
}

const STRATEGY_LABELS: Record<string, string> = {
  priority: 'Priority',
  round_robin: 'Round Robin',
  least_latency: 'Least Latency',
  cheapest: 'Cheapest First',
};

export const ModelRouterPanel: React.FC = () => {
  const [config, setConfig] = useState<RouterConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'models' | 'fallback'>('models');

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<RouterConfig>('/api/models/router-config');
      setConfig(data);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load model config');
    } finally {
      setLoading(false);
    }
  };

  const handleStrategyChange = (strategy: RouterConfig['strategy']) => {
    if (!config) return;
    setConfig({ ...config, strategy });
  };

  const handleToggleModel = (id: string) => {
    if (!config) return;
    setConfig({
      ...config,
      models: config.models.map((m) =>
        m.id === id ? { ...m, enabled: !m.enabled } : m
      ),
    });
  };

  const handlePriorityChange = (id: string, priority: number) => {
    if (!config) return;
    setConfig({
      ...config,
      models: config.models.map((m) =>
        m.id === id ? { ...m, priority } : m
      ),
    });
  };

  const handleSave = async () => {
    if (!config) return;
    try {
      setSaving(true);
      await apiClient.post('/api/models/router-config', config);
    } catch (e: any) {
      setError(e?.message ?? 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
        <div className="text-gray-400 text-sm animate-pulse">Loading model router...</div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
        <div className="text-red-400 text-sm">{error ?? 'No config'}</div>
      </div>
    );
  }

  const sortedModels = [...config.models].sort((a, b) => a.priority - b.priority);

  return (
    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-white font-semibold text-sm">Model Router</h3>
          <p className="text-gray-400 text-xs mt-0.5">
            Configure routing strategy &amp; fallback chains
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-xs font-medium disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-2 text-red-300 text-xs">
          {error}
        </div>
      )}

      {/* Strategy picker */}
      <div>
        <label className="text-gray-300 text-xs font-medium block mb-2">Routing Strategy</label>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(STRATEGY_LABELS).map(([key, label]) => (
            <button
              key={key}
              onClick={() => handleStrategyChange(key as RouterConfig['strategy'])}
              className={`py-2 px-3 rounded-lg text-xs font-medium border transition-colors ${
                config.strategy === key
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : 'bg-gray-700 border-gray-600 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-700">
        {(['models', 'fallback'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            {tab === 'models' ? 'Models' : 'Fallback Chains'}
          </button>
        ))}
      </div>

      {activeTab === 'models' && (
        <div className="space-y-2">
          {sortedModels.map((model) => (
            <div
              key={model.id}
              className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${
                model.enabled
                  ? 'bg-gray-700/60 border-gray-600'
                  : 'bg-gray-900/40 border-gray-700 opacity-60'
              }`}
            >
              {/* Toggle */}
              <button
                onClick={() => handleToggleModel(model.id)}
                className={`shrink-0 relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  model.enabled ? 'bg-blue-600' : 'bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                    model.enabled ? 'translate-x-5' : 'translate-x-1'
                  }`}
                />
              </button>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-white text-xs font-medium truncate">{model.name}</span>
                  <span className="text-gray-500 text-xs">{model.provider}</span>
                </div>
                {model.tags && model.tags.length > 0 && (
                  <div className="flex gap-1 mt-0.5">
                    {model.tags.map((tag) => (
                      <span key={tag} className="text-xs text-gray-500 bg-gray-800 px-1.5 rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Cost */}
              {model.cost_per_1k !== undefined && (
                <span className="shrink-0 text-xs text-gray-400">
                  ${model.cost_per_1k}/1k
                </span>
              )}

              {/* Priority */}
              <div className="shrink-0 flex items-center gap-1">
                <span className="text-gray-500 text-xs">P</span>
                <input
                  type="number"
                  min={1}
                  max={99}
                  value={model.priority}
                  onChange={(e) => handlePriorityChange(model.id, parseInt(e.target.value) || 1)}
                  className="w-10 bg-gray-800 border border-gray-600 rounded px-1 py-0.5 text-xs text-white text-center focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'fallback' && (
        <div className="space-y-3">
          {config.fallback_chains.length === 0 ? (
            <div className="text-gray-500 text-xs text-center py-4">No fallback chains configured</div>
          ) : (
            config.fallback_chains.map((chain, idx) => (
              <div key={idx} className="bg-gray-700/40 border border-gray-600 rounded-lg p-3 space-y-2">
                <div className="text-gray-300 text-xs font-medium">{chain.task_type}</div>
                <div className="flex items-center gap-2 flex-wrap">
                  {chain.chain.map((modelId, i) => (
                    <React.Fragment key={modelId}>
                      <span className="px-2 py-1 bg-gray-800 text-gray-200 rounded text-xs font-mono">
                        {modelId}
                      </span>
                      {i < chain.chain.length - 1 && (
                        <span className="text-gray-500 text-xs">→</span>
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      <div className="border-t border-gray-700 pt-3 flex items-center justify-between">
        <span className="text-gray-500 text-xs">
          Default: <span className="text-gray-300 font-mono">{config.default_model}</span>
        </span>
        <span className="text-gray-500 text-xs">
          {config.models.filter((m) => m.enabled).length}/{config.models.length} enabled
        </span>
      </div>
    </div>
  );
};
