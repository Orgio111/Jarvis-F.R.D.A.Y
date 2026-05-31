import React, { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api/client';

interface WakeWordStatus {
  enabled: boolean;
  keyword: string;
  threshold: number;
  backend: string;
  listening: boolean;
}

export const WakeWordPanel: React.FC = () => {
  const [status, setStatus] = useState<WakeWordStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Local edits
  const [keyword, setKeyword] = useState('');
  const [threshold, setThreshold] = useState(0.5);
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<WakeWordStatus>('/api/wake-word/status');
      setStatus(data);
      setKeyword(data.keyword);
      setThreshold(data.threshold);
      setEnabled(data.enabled);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load wake word status');
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async () => {
    try {
      setSaving(true);
      if (enabled) {
        await apiClient.post('/api/wake-word/stop', {});
        setEnabled(false);
        setStatus((s) => s ? { ...s, enabled: false, listening: false } : s);
      } else {
        await apiClient.post('/api/wake-word/start', {});
        setEnabled(true);
        setStatus((s) => s ? { ...s, enabled: true, listening: true } : s);
      }
    } catch (e: any) {
      setError(e?.message ?? 'Toggle failed');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveConfig = async () => {
    try {
      setSaving(true);
      await apiClient.post('/api/wake-word/config', { keyword, threshold });
      await fetchStatus();
    } catch (e: any) {
      setError(e?.message ?? 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
        <div className="text-gray-400 text-sm animate-pulse">Loading wake word settings...</div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-white font-semibold text-sm">Wake Word Detection</h3>
          <p className="text-gray-400 text-xs mt-0.5">
            Trigger Jarvis hands-free with a custom keyword
          </p>
        </div>
        <button
          onClick={handleToggle}
          disabled={saving}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
            enabled ? 'bg-blue-600' : 'bg-gray-600'
          } ${saving ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              enabled ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Live status indicator */}
      {status && (
        <div className="flex items-center gap-2">
          <div
            className={`h-2 w-2 rounded-full ${
              status.listening ? 'bg-green-400 animate-pulse' : 'bg-gray-500'
            }`}
          />
          <span className="text-xs text-gray-400">
            {status.listening ? 'Listening...' : 'Not listening'}
          </span>
          <span className="text-xs text-gray-600 ml-auto">Backend: {status.backend}</span>
        </div>
      )}

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-2 text-red-300 text-xs">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Config */}
      <div className="space-y-3 border-t border-gray-700 pt-4">
        <div>
          <label className="text-gray-300 text-xs font-medium block mb-1">Wake Keyword</label>
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="e.g. hey jarvis"
            className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="text-gray-300 text-xs font-medium block mb-1">
            Detection Threshold:{' '}
            <span className="text-blue-400">{threshold.toFixed(2)}</span>
          </label>
          <input
            type="range"
            min={0.1}
            max={0.99}
            step={0.01}
            value={threshold}
            onChange={(e) => setThreshold(parseFloat(e.target.value))}
            className="w-full accent-blue-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-0.5">
            <span>More sensitive</span>
            <span>Less false positives</span>
          </div>
        </div>

        <button
          onClick={handleSaveConfig}
          disabled={saving}
          className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? 'Saving...' : 'Save Config'}
        </button>
      </div>
    </div>
  );
};
