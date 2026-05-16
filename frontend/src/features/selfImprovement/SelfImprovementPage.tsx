import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';

interface SIStatus {
  enabled: boolean;
  requireApproval: boolean;
  versioningEnabled: boolean;
  pendingSuggestions: number;
  appliedCount: number;
}

interface Suggestion {
  id: string;
  context: string;
  suggestion: string;
  status: string;
  createdAt: number;
  requiresApproval: boolean;
}

interface SuggestionsResponse {
  suggestions: Suggestion[];
  total: number;
}

export function SelfImprovementPage() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const qc = useQueryClient();
  const [context, setContext] = useState('');

  const { data: status } = useQuery<SIStatus>({
    queryKey: ['self-improvement-status'],
    queryFn: () => apiClient.get<SIStatus>('/self-improvement/status'),
    enabled: bootstrapReady,
    ...freshness.resourceState,
  });

  const { data: suggestionsData, isLoading } = useQuery<SuggestionsResponse>({
    queryKey: ['si-suggestions'],
    queryFn: () => apiClient.get<SuggestionsResponse>('/self-improvement/suggestions'),
    enabled: bootstrapReady,
    ...freshness.live,
  });

  const suggestMut = useMutation({
    mutationFn: (ctx: string) =>
      apiClient.post<Suggestion>('/self-improvement/suggest', { context: ctx }),
    onSuccess: () => {
      setContext('');
      qc.invalidateQueries({ queryKey: ['si-suggestions'] });
      qc.invalidateQueries({ queryKey: ['si-status'] });
    },
  });

  const approveMut = useMutation({
    mutationFn: (id: string) =>
      apiClient.post(`/self-improvement/suggestions/${id}/approve`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['si-suggestions'] });
      qc.invalidateQueries({ queryKey: ['si-status'] });
    },
  });

  const rejectMut = useMutation({
    mutationFn: (id: string) =>
      apiClient.post(`/self-improvement/suggestions/${id}/reject`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['si-suggestions'] });
      qc.invalidateQueries({ queryKey: ['si-status'] });
    },
  });

  const suggestions = suggestionsData?.suggestions ?? [];

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader title="Self-Improvement" subtitle="AI-generated improvement suggestions with human review" />

      {status && (
        <GlassPanel className="p-4 mt-6 mb-4">
          <div className="flex items-center gap-4 flex-wrap">
            <StatusDot status={status.enabled ? 'online' : 'offline'} label={status.enabled ? 'enabled' : 'disabled'} />
            <span className="text-jarvis-text-dim text-xs font-mono">
              pending: {status.pendingSuggestions}
            </span>
            <span className="text-jarvis-text-dim text-xs font-mono">
              applied: {status.appliedCount}
            </span>
            {status.requireApproval && (
              <span className="text-jarvis-cyan text-xs font-mono border border-jarvis-cyan/30 rounded px-1.5 py-0.5">
                requires approval
              </span>
            )}
            {status.versioningEnabled && (
              <span className="text-green-400 text-xs font-mono border border-green-400/30 rounded px-1.5 py-0.5">
                versioning on
              </span>
            )}
          </div>
        </GlassPanel>
      )}

      {/* Request suggestion */}
      <GlassPanel className="p-5 mb-4">
        <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">Request a Suggestion</p>
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          rows={4}
          placeholder="Describe what you'd like JARVIS to improve or optimize…"
          disabled={!status?.enabled}
          className="w-full resize-none bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-sm font-mono text-jarvis-text-bright placeholder-jarvis-text-dim focus:outline-none focus:border-jarvis-cyan/60 mb-3 disabled:opacity-40"
        />
        <button
          className="btn-cockpit-primary px-5 py-2 text-sm"
          onClick={() => suggestMut.mutate(context.trim())}
          disabled={!context.trim() || suggestMut.isPending || !status?.enabled}
        >
          {suggestMut.isPending ? 'Generating…' : 'Generate Suggestion'}
        </button>
        {suggestMut.isSuccess && (
          <p className="text-jarvis-cyan text-xs font-mono mt-2">Suggestion created and queued for review.</p>
        )}
        {suggestMut.isError && (
          <p className="text-jarvis-red text-xs font-mono mt-2">Failed to generate suggestion.</p>
        )}
      </GlassPanel>

      {/* Pending suggestions */}
      <p className="text-jarvis-text-dim text-xs font-mono mb-2">
        Pending review ({suggestions.length})
      </p>
      {isLoading && (
        <p className="text-jarvis-text-dim text-xs font-mono">Loading…</p>
      )}
      <div className="space-y-3">
        {suggestions.map((s) => (
          <GlassPanel key={s.id} className="p-4">
            <div className="flex items-start justify-between gap-3 mb-2">
              <p className="text-jarvis-text-dim text-xs font-mono truncate">{s.context}</p>
              <span className="text-xs font-mono text-jarvis-text-dim border border-jarvis-border rounded px-1.5 py-0.5 shrink-0">
                {s.id}
              </span>
            </div>
            <p className="text-jarvis-text-bright text-xs font-mono leading-relaxed mb-3">
              {s.suggestion}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => approveMut.mutate(s.id)}
                disabled={approveMut.isPending}
                className="px-3 py-1.5 text-xs font-mono rounded border border-green-500/40 text-green-400 hover:bg-green-500/10 transition-colors"
              >
                Approve
              </button>
              <button
                onClick={() => rejectMut.mutate(s.id)}
                disabled={rejectMut.isPending}
                className="px-3 py-1.5 text-xs font-mono rounded border border-jarvis-red/40 text-jarvis-red hover:bg-jarvis-red/10 transition-colors"
              >
                Reject
              </button>
            </div>
          </GlassPanel>
        ))}
        {!isLoading && suggestions.length === 0 && (
          <GlassPanel className="p-4">
            <p className="text-jarvis-text-dim text-xs font-mono text-center">No pending suggestions.</p>
          </GlassPanel>
        )}
      </div>
    </div>
  );
}
