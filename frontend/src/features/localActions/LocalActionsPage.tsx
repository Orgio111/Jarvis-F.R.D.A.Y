import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';

interface ActionParam {
  name: string;
  type: string;
  required: boolean;
}

interface Action {
  id: string;
  name: string;
  description: string;
  category: string;
  requiresApproval: boolean;
  enabled: boolean;
  parameters?: ActionParam[];
}

interface ActionsResponse {
  actions: Action[];
  total: number;
  enabled: boolean;
  requireApproval: boolean;
}

interface PendingApproval {
  id: string;
  actionId: string;
  actionName: string;
  params: Record<string, unknown>;
  status: string;
}

interface PendingResponse {
  pending: PendingApproval[];
  total: number;
}

const CATEGORY_COLOR: Record<string, string> = {
  system: 'text-jarvis-cyan border-jarvis-cyan/30',
  ui: 'text-jarvis-blue border-jarvis-blue/30',
  shell: 'text-jarvis-red border-jarvis-red/30',
};

export function LocalActionsPage() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Action | null>(null);
  const [params, setParams] = useState<Record<string, string>>({});
  const [execResult, setExecResult] = useState<unknown>(null);

  const { data: actionsData } = useQuery<ActionsResponse>({
    queryKey: ['local-actions'],
    queryFn: () => apiClient.get<ActionsResponse>('/local-actions'),
    enabled: bootstrapReady,
    staleTime: 30_000,
  });

  const { data: pendingData } = useQuery<PendingResponse>({
    queryKey: ['local-actions-pending'],
    queryFn: () => apiClient.get<PendingResponse>('/local-actions/pending'),
    enabled: bootstrapReady,
    refetchInterval: 5000,
  });

  const executeMut = useMutation({
    mutationFn: ({ actionId, params }: { actionId: string; params: Record<string, string> }) =>
      apiClient.post<unknown>(`/local-actions/${actionId}/execute`, params),
    onSuccess: (res) => {
      setExecResult(res);
      qc.invalidateQueries({ queryKey: ['local-actions-pending'] });
    },
  });

  const approveMut = useMutation({
    mutationFn: (id: string) =>
      apiClient.post<unknown>(`/local-actions/approvals/${id}/approve`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['local-actions-pending'] }),
  });

  const denyMut = useMutation({
    mutationFn: (id: string) =>
      apiClient.post<unknown>(`/local-actions/approvals/${id}/deny`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['local-actions-pending'] }),
  });

  const selectAction = (action: Action) => {
    setSelected(action);
    setParams({});
    setExecResult(null);
  };

  const handleExecute = () => {
    if (!selected) return;
    executeMut.mutate({ actionId: selected.id, params });
  };

  const actions = actionsData?.actions ?? [];
  const pending = pendingData?.pending ?? [];

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader title="Local Actions" subtitle="Execute system commands with optional approval gates" />

      {actionsData && (
        <GlassPanel className="p-4 mt-6 mb-4">
          <div className="flex items-center gap-4 flex-wrap">
            <StatusDot status={actionsData.enabled ? 'online' : 'offline'} label={actionsData.enabled ? 'enabled' : 'disabled'} />
            <span className="text-jarvis-text-dim text-xs font-mono">{actionsData.total} actions</span>
            {actionsData.requireApproval && (
              <span className="text-jarvis-cyan text-xs font-mono border border-jarvis-cyan/30 rounded px-1.5 py-0.5">
                approval required
              </span>
            )}
            {pending.length > 0 && (
              <span className="text-yellow-400 text-xs font-mono border border-yellow-400/30 rounded px-1.5 py-0.5">
                {pending.length} pending approval
              </span>
            )}
          </div>
        </GlassPanel>
      )}

      <div className="flex gap-4">
        {/* Action list */}
        <div className="w-56 shrink-0 space-y-2">
          {actions.map((action) => (
            <button
              key={action.id}
              onClick={() => selectAction(action)}
              className={[
                'w-full text-left jarvis-panel p-3 rounded transition-colors',
                selected?.id === action.id
                  ? 'border-jarvis-cyan/40 bg-jarvis-cyan/5'
                  : 'hover:border-jarvis-border/80',
              ].join(' ')}
            >
              <div className="flex items-center justify-between mb-1 gap-1">
                <span className="text-jarvis-text-bright text-xs font-mono font-semibold truncate">
                  {action.name}
                </span>
                <span className={`text-xs font-mono border rounded px-1 py-0.5 shrink-0 ${CATEGORY_COLOR[action.category] ?? 'text-jarvis-text-dim border-jarvis-border'}`}>
                  {action.category}
                </span>
              </div>
              <p className="text-jarvis-text-dim text-xs font-mono line-clamp-2">
                {action.description}
              </p>
              {action.requiresApproval && (
                <p className="text-yellow-400 text-xs font-mono mt-1">⚠ approval</p>
              )}
            </button>
          ))}
        </div>

        {/* Right panel */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Action executor */}
          {selected ? (
            <GlassPanel className="p-5">
              <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-1">{selected.name}</p>
              <p className="text-jarvis-text-dim text-xs font-mono mb-4">{selected.description}</p>

              {selected.parameters && selected.parameters.length > 0 && (
                <div className="space-y-3 mb-4">
                  {selected.parameters.map((p) => (
                    <div key={p.name}>
                      <label className="text-jarvis-text-dim text-xs font-mono block mb-1">
                        {p.name}
                        {p.required && <span className="text-jarvis-red ml-1">*</span>}
                        <span className="ml-1 opacity-50">({p.type})</span>
                      </label>
                      <input
                        type="text"
                        value={params[p.name] ?? ''}
                        onChange={(e) => setParams((prev) => ({ ...prev, [p.name]: e.target.value }))}
                        className="w-full bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-xs font-mono text-jarvis-text-bright focus:outline-none focus:border-jarvis-cyan/60"
                      />
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={handleExecute}
                disabled={executeMut.isPending || !actionsData?.enabled}
                className="btn-cockpit-primary px-4 py-2 text-sm"
              >
                {executeMut.isPending ? 'Executing…' : selected.requiresApproval ? 'Queue for Approval' : 'Execute'}
              </button>

              {executeMut.isSuccess && execResult !== null && (
                <div className="mt-4 bg-jarvis-bg border border-jarvis-border rounded p-3">
                  <pre className="text-jarvis-text-bright text-xs font-mono whitespace-pre-wrap break-words">
                    {JSON.stringify(execResult, null, 2)}
                  </pre>
                </div>
              )}
            </GlassPanel>
          ) : (
            <GlassPanel className="p-5">
              <p className="text-jarvis-text-dim text-xs font-mono text-center py-8">Select an action to execute.</p>
            </GlassPanel>
          )}

          {/* Approval queue */}
          {pending.length > 0 && (
            <div>
              <p className="text-jarvis-text-dim text-xs font-mono mb-2">Approval Queue ({pending.length})</p>
              <div className="space-y-2">
                {pending.map((p) => (
                  <GlassPanel key={p.id} className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-jarvis-text-bright text-xs font-mono font-semibold">{p.actionName}</p>
                      <span className="text-jarvis-text-dim text-xs font-mono">{p.id}</span>
                    </div>
                    {Object.keys(p.params).length > 0 && (
                      <pre className="text-jarvis-text-dim text-xs font-mono mb-3 bg-jarvis-bg rounded p-2">
                        {JSON.stringify(p.params, null, 2)}
                      </pre>
                    )}
                    <div className="flex gap-2">
                      <button
                        onClick={() => approveMut.mutate(p.id)}
                        disabled={approveMut.isPending}
                        className="px-3 py-1.5 text-xs font-mono rounded border border-green-500/40 text-green-400 hover:bg-green-500/10 transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => denyMut.mutate(p.id)}
                        disabled={denyMut.isPending}
                        className="px-3 py-1.5 text-xs font-mono rounded border border-jarvis-red/40 text-jarvis-red hover:bg-jarvis-red/10 transition-colors"
                      >
                        Deny
                      </button>
                    </div>
                  </GlassPanel>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
