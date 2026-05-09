import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';

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
    staleTime: 30_000,
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
            <button
              key={tool.id}
              onClick={() => selectTool(tool)}
              className={[
                'w-full text-left jarvis-panel p-3 rounded transition-colors',
                selected?.id === tool.id
                  ? 'border-jarvis-cyan/40 bg-jarvis-cyan/5'
                  : 'hover:border-jarvis-border/80',
                !tool.enabled ? 'opacity-40' : '',
              ].join(' ')}
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
            </button>
          ))}
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

              <button
                onClick={handleExecute}
                disabled={!selected.enabled || execMut.isPending}
                className="btn-cockpit-primary px-4 py-2 text-sm"
              >
                {execMut.isPending ? 'Executing…' : 'Execute'}
              </button>

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
