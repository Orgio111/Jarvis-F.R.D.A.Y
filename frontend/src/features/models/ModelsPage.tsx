import { useState } from 'react';
import { useModels } from './useModels';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import type { Model } from '@/lib/api/types';

export function ModelsPage() {
  const { data, isLoading } = useModels();
  const [filter, setFilter] = useState('');

  const models = data?.models ?? [];
  const filtered = filter
    ? models.filter(
        (m) =>
          m.name.toLowerCase().includes(filter.toLowerCase()) ||
          m.id.toLowerCase().includes(filter.toLowerCase()) ||
          m.providerName.toLowerCase().includes(filter.toLowerCase()),
      )
    : models;

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader
        title="Available Models"
        subtitle={data ? `${data.total} models discovered` : 'Discovering models…'}
      />

      <div className="mt-4 mb-4">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter models…"
          className="w-full max-w-sm bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-sm font-mono text-jarvis-text-bright placeholder-jarvis-text-dim focus:outline-none focus:border-jarvis-cyan/60"
        />
      </div>

      {isLoading ? (
        <div className="text-jarvis-text-dim text-xs font-mono">Loading models…</div>
      ) : filtered.length === 0 ? (
        <NoModels hasProviders={models.length > 0} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((m) => (
            <ModelCard key={`${m.providerId}/${m.id}`} model={m} />
          ))}
        </div>
      )}
    </div>
  );
}

function ModelCard({ model }: { model: Model }) {
  return (
    <GlassPanel className="p-4">
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0">
          <p className="text-jarvis-text-bright text-xs font-mono font-semibold truncate">
            {model.name}
          </p>
          <p className="text-jarvis-text-dim text-xs font-mono truncate opacity-60">
            {model.providerId}
          </p>
        </div>
        {model.isFree && (
          <span className="shrink-0 ml-2 text-xs font-mono text-jarvis-cyan border border-jarvis-cyan/30 rounded px-1.5 py-0.5">
            free
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-1 mb-2">
        {model.groups.slice(0, 3).map((g) => (
          <span key={g} className="text-xs font-mono text-jarvis-text-dim bg-jarvis-bg px-1.5 py-0.5 rounded">
            {g}
          </span>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-1 text-xs font-mono">
        <span className="text-jarvis-text-dim">Context</span>
        <span className="text-jarvis-text-bright">{formatK(model.contextWindow)}</span>
        <span className="text-jarvis-text-dim">Max tokens</span>
        <span className="text-jarvis-text-bright">{formatK(model.maxTokens)}</span>
      </div>

      <div className="flex gap-2 mt-2">
        {model.supportsVision && <Badge label="Vision" color="blue" />}
        {model.supportsTools && <Badge label="Tools" color="cyan" />}
      </div>
    </GlassPanel>
  );
}

function Badge({ label, color }: { label: string; color: 'cyan' | 'blue' }) {
  const cls = color === 'cyan'
    ? 'text-jarvis-cyan border-jarvis-cyan/30'
    : 'text-jarvis-blue border-jarvis-blue/30';
  return (
    <span className={`text-xs font-mono border rounded px-1.5 py-0.5 ${cls}`}>
      {label}
    </span>
  );
}

function NoModels({ hasProviders }: { hasProviders: boolean }) {
  return (
    <GlassPanel className="p-8 text-center max-w-md mt-4">
      <p className="text-jarvis-text-dim text-sm font-mono">
        {hasProviders ? 'No models match your filter.' : 'No models available.'}
      </p>
      {!hasProviders && (
        <p className="text-jarvis-text-dim text-xs font-mono mt-2">
          Configure a provider to discover available models.
        </p>
      )}
    </GlassPanel>
  );
}

function formatK(n: number): string {
  if (n >= 1000) return `${Math.round(n / 1000)}k`;
  return String(n);
}
