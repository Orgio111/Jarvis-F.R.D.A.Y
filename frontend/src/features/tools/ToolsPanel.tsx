import { useState } from 'react';
import { m } from 'framer-motion';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';
import { CheckCircle2, XCircle, ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';

interface Tool {
  id: string;
  name: string;
  description: string;
  category: string;
  enabled: boolean;
  parameters: Array<{ name: string; type: string; required: boolean; description: string }>;
}

interface ToolsListResponse {
  tools: Tool[];
  total: number;
  enabled: number;
}

interface ToolResult {
  toolId: string;
  result: unknown;
}

const CATEGORY_COLOR: Record<string, string> = {
  search: 'text-jarvis-cyan border-jarvis-cyan/30',
  execution: 'text-jarvis-blue border-jarvis-blue/30',
  memory: 'text-green-400 border-green-400/30',
  local: 'text-jarvis-text-dim border-jarvis-border',
};

export function ToolsPanel() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const [selected, setSelected] = useState<Tool | null>(null);
  const [params, setParams] = useState<Record<string, string>>({});
  const [execResult, setExecResult] = useState<unknown>(null);

  const { data } = useQuery<ToolsListResponse>({
    queryKey: ['tools'],
    queryFn: () => apiClient.get<ToolsListResponse>('/tools'),
    enabled: bootstrapReady,
    ...freshness.resourceState,
  });

  const execMut = useMutation({
    mutationFn: ({ toolId, params }: { toolId: string; params: Record<string, unknown> }) =>
      apiClient.post<ToolResult>(`/tools/${toolId}/execute`, params),
    onSuccess: (res) => setExecResult(res.result),
  });

  const selectTool = (tool: Tool) => {
    setSelected(tool);
    setParams({});
    setExecResult(null);
  };

  const handleExecute = () => {
    if (!selected) return;
    execMut.mutate({ toolId: selected.id, params });
  };

  const tools = data?.tools ?? [];

  // ── Local Actions (Merge: Local Actions → Tools) ──
  const [showActions, setShowActions] = useState(true);
  const { data: localActions } = useQuery<{ actions: Array<{ id: string; name: string; description: string; type: string; device: string; status: string; approvedAt: string }> }>({
    queryKey: ['local-actions', 'pending'],
    queryFn: () => apiClient.get('/local-actions/pending'),
    enabled: bootstrapReady,
    staleTime: 15_000,
    gcTime: 60_000,
  });
  const approveAction = useMutation({
    mutationFn: (id: string) => apiClient.post(`/local-actions/${id}/approve`, {}),
  });
  const denyAction = useMutation({
    mutationFn: (id: string) => apiClient.post(`/local-actions/${id}/deny`, {}),
  });

  const pendingActions = localActions?.actions?.filter(a => a.status === 'pending') ?? [];

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader
        title="Tools"
        subtitle={data ? `${data.enabled} / ${data.total} enabled` : 'Loading…'}
      />

      <div className="flex gap-4 mt-6 h-full">
        {/* Tool list */}
        <div className="w-64 shrink-0 space-y-2">
          {tools.map((tool) => (
            <m.button
              key={tool.id}
              onClick={() => selectTool(tool)}
              className={[
                'w-full text-left jarvis-panel p-3 rounded',
                selected?.id === tool.id
                  ? 'border-jarvis-cyan/40 bg-jarvis-cyan/5'
                  : '',
                !tool.enabled ? 'opacity-40' : '',
              ].join(' ')}
              whileHover={tool.enabled ? {
                scale: 1.01,
                x: 2,
                transition: { type: 'spring', stiffness: 300, damping: 25 },
              } : undefined}
              whileTap={tool.enabled ? {
                scale: 0.99,
                transition: { type: 'spring', stiffness: 400, damping: 20 },
              } : undefined}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-jarvis-text-bright text-xs font-mono font-semibold">
                  {tool.name}
                </span>
                <span className={`text-xs font-mono border rounded px-1.5 py-0.5 ${CATEGORY_COLOR[tool.category] ?? 'text-jarvis-text-dim border-jarvis-border'}`}>
                  {tool.category}
                </span>
              </div>
              <p className="text-jarvis-text-dim text-xs font-mono line-clamp-2">
                {tool.description}
              </p>
              {!tool.enabled && (
                <p className="text-jarvis-red text-xs font-mono mt-1">disabled</p>
              )}
            </m.button>
          ))}
        </div>

        {/* Local Actions section (Merge: Local Actions → Tools) */}
        <div className="w-56 shrink-0">
          <button
            onClick={() => setShowActions(!showActions)}
            className="flex items-center gap-1.5 w-full mb-2 text-jarvis-text-dim/60 hover:text-jarvis-text transition-colors"
          >
            {showActions ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            <span className="text-[10px] font-mono tracking-wider uppercase">Pending Actions</span>
            {pendingActions.length > 0 && (
              <NeonBadge color="yellow" size="sm" label={`${pendingActions.length}`} />
            )}
          </button>

          {showActions && (
            <div className="space-y-1.5 max-h-64 overflow-y-auto scrollbar-thin pr-1">
              {pendingActions.length === 0 ? (
                <GlassPanel className="p-3">
                  <div className="flex items-center gap-2 text-jarvis-text-dim/50">
                    <CheckCircle2 size={12} className="text-jarvis-green" />
                    <span className="text-[10px] font-mono">No pending actions</span>
                  </div>
                </GlassPanel>
              ) : (
                pendingActions.map((action) => (
                  <GlassPanel key={action.id} className="p-2.5">
                    <div className="flex items-start gap-2">
                      <AlertTriangle size={12} className="text-jarvis-yellow shrink-0 mt-0.5" />
                      <div className="min-w-0 flex-1">
                        <p className="text-[11px] font-mono text-jarvis-text-bright truncate">{action.name}</p>
                        <p className="text-[9px] font-mono text-jarvis-text-dim/60 line-clamp-2">{action.description}</p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <button
                            onClick={() => approveAction.mutate(action.id)}
                            disabled={approveAction.isPending}
                            className="flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-mono bg-jarvis-green/10 border border-jarvis-green/30 text-jarvis-green hover:bg-jarvis-green/20 transition-all disabled:opacity-50"
                          >
                            <CheckCircle2 size={8} />
                            Allow
                          </button>
                          <button
                            onClick={() => denyAction.mutate(action.id)}
                            disabled={denyAction.isPending}
                            className="flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-mono bg-jarvis-red/10 border border-jarvis-red/30 text-jarvis-red hover:bg-jarvis-red/20 transition-all disabled:opacity-50"
                          >
                            <XCircle size={8} />
                            Deny
                          </button>
                          {action.type && (
                            <span className="ml-auto text-[8px] font-mono text-jarvis-text-dim/40 uppercase">{action.type}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </GlassPanel>
                ))
              )}
            </div>
          )}
        </div>

        {/* Tool detail + executor */}
        <div className="flex-1 min-w-0">
          {selected ? (
            <GlassPanel className="p-5">
              <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-1">
                {selected.name}
              </p>
              <p className="text-jarvis-text-dim text-xs font-mono mb-4">
                {selected.description}
              </p>

              <div className="space-y-3 mb-4">
                {selected.parameters.map((p) => (
                  <div key={p.name}>
                    <label className="text-jarvis-text-dim text-xs font-mono block mb-1">
                      {p.name}
                      {p.required && <span className="text-jarvis-red ml-1">*</span>}
                      <span className="ml-1 opacity-50">({p.type})</span>
                    </label>
                    {p.type === 'string' && p.name === 'code' ? (
                      <textarea
                        rows={5}
                        value={params[p.name] ?? ''}
                        onChange={(e) => setParams((prev) => ({ ...prev, [p.name]: e.target.value }))}
                        className="w-full resize-none bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-xs font-mono text-jarvis-text-bright focus:outline-none focus:border-jarvis-cyan/60"
                      />
                    ) : (
                      <input
                        type="text"
                        value={params[p.name] ?? ''}
                        onChange={(e) => setParams((prev) => ({ ...prev, [p.name]: e.target.value }))}
                        placeholder={p.description}
                        className="w-full bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-xs font-mono text-jarvis-text-bright placeholder-jarvis-text-dim focus:outline-none focus:border-jarvis-cyan/60"
                      />
                    )}
                  </div>
                ))}
              </div>

              <m.button
                onClick={handleExecute}
                disabled={!selected.enabled || execMut.isPending}
                className="btn-cockpit-primary px-4 py-2 text-sm"
                whileHover={selected.enabled && !execMut.isPending ? {
                  scale: 1.02,
                  transition: { type: 'spring', stiffness: 400, damping: 20 },
                } : undefined}
                whileTap={selected.enabled && !execMut.isPending ? {
                  scale: 0.98,
                } : undefined}
              >
                {execMut.isPending ? 'Executing…' : 'Execute'}
              </m.button>

              {execResult !== null && (
                <div className="mt-4 bg-jarvis-bg border border-jarvis-border rounded p-3">
                  <p className="text-jarvis-text-dim text-xs font-mono mb-2">Result:</p>
                  <pre className="text-jarvis-text-bright text-xs font-mono whitespace-pre-wrap break-words">
                    {JSON.stringify(execResult, null, 2)}
                  </pre>
                </div>
              )}
            </GlassPanel>
          ) : (
            <div className="flex items-center justify-center h-32 text-jarvis-text-dim text-xs font-mono">
              Select a tool to configure and execute it.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
