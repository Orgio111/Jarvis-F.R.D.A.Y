import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';

interface MemoryStatus {
  enabled: boolean;
  faissAvailable: boolean;
  embeddingsAvailable: boolean;
  indexPath: string;
  embeddingsModel: string;
}

interface MemoryResult {
  id: number;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

interface SearchResponse {
  results: MemoryResult[];
  total: number;
}

export function MemoryPanel() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const qc = useQueryClient();

  const { data: status } = useQuery<MemoryStatus>({
    queryKey: ['memory-status'],
    queryFn: () => apiClient.get<MemoryStatus>('/memory/status'),
    enabled: bootstrapReady,
    ...freshness.resourceState,
  });

  const [query, setQuery] = useState('');
  const [storeContent, setStoreContent] = useState('');
  const [results, setResults] = useState<MemoryResult[]>([]);

  const searchMut = useMutation({
    mutationFn: (q: string) =>
      apiClient.post<SearchResponse>('/memory/search', { query: q, topK: 8 }),
    onSuccess: (res) => setResults(res.results ?? []),
  });

  const storeMut = useMutation({
    mutationFn: (content: string) =>
      apiClient.post('/memory/store', { content }),
    onSuccess: () => {
      setStoreContent('');
      qc.invalidateQueries({ queryKey: ['memory-status'] });
    },
  });

  const available = status?.faissAvailable && status?.embeddingsAvailable;

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader title="Memory" subtitle="Long-term vector memory via FAISS" />

      {/* Status */}
      {status && (
        <GlassPanel className="p-4 mt-6 mb-4">
          <div className="flex items-center gap-4 flex-wrap">
            <StatusDot status={available ? 'online' : 'offline'} label={available ? 'ready' : 'dependencies missing'} />
            <span className="text-jarvis-text-dim text-xs font-mono">
              FAISS: {status.faissAvailable ? '✓' : '✗'}
            </span>
            <span className="text-jarvis-text-dim text-xs font-mono">
              Embeddings: {status.embeddingsAvailable ? '✓' : '✗'}
            </span>
            <span className="text-jarvis-text-dim text-xs font-mono truncate">
              {status.embeddingsModel}
            </span>
          </div>
          {!available && (
            <p className="text-jarvis-text-dim text-xs font-mono mt-2">
              Install: <code className="text-jarvis-cyan">pip install jarvis-ai-service[gpu]</code>
            </p>
          )}
        </GlassPanel>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Search */}
        <GlassPanel className="p-5">
          <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">Semantic Search</p>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && query.trim() && searchMut.mutate(query)}
              placeholder="Search memory…"
              className="flex-1 bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-sm font-mono text-jarvis-text-bright placeholder-jarvis-text-dim focus:outline-none focus:border-jarvis-cyan/60"
            />
            <button
              className="btn-cockpit-primary px-4 py-2 text-sm"
              onClick={() => query.trim() && searchMut.mutate(query)}
              disabled={!query.trim() || searchMut.isPending}
            >
              Search
            </button>
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {searchMut.isPending && (
              <p className="text-jarvis-text-dim text-xs font-mono">Searching…</p>
            )}
            {results.map((r) => (
              <div key={r.id} className="bg-jarvis-bg border border-jarvis-border rounded p-3">
                <p className="text-jarvis-text-bright text-xs font-mono">{r.content}</p>
                <p className="text-jarvis-text-dim text-xs font-mono mt-1">
                  score: {r.score.toFixed(3)}
                </p>
              </div>
            ))}
            {results.length === 0 && !searchMut.isPending && query && !searchMut.isIdle && (
              <p className="text-jarvis-text-dim text-xs font-mono">No results found.</p>
            )}
          </div>
        </GlassPanel>

        {/* Store */}
        <GlassPanel className="p-5">
          <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">Store Memory</p>
          <textarea
            value={storeContent}
            onChange={(e) => setStoreContent(e.target.value)}
            rows={6}
            placeholder="Enter content to remember…"
            className="w-full resize-none bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-sm font-mono text-jarvis-text-bright placeholder-jarvis-text-dim focus:outline-none focus:border-jarvis-cyan/60 mb-3"
          />
          <button
            className="btn-cockpit-primary px-4 py-2 text-sm w-full"
            onClick={() => storeContent.trim() && storeMut.mutate(storeContent)}
            disabled={!storeContent.trim() || storeMut.isPending}
          >
            {storeMut.isPending ? 'Storing…' : 'Store'}
          </button>
          {storeMut.isSuccess && (
            <p className="text-jarvis-cyan text-xs font-mono mt-2">Stored successfully.</p>
          )}
          {storeMut.isError && (
            <p className="text-jarvis-red text-xs font-mono mt-2">Store failed.</p>
          )}
        </GlassPanel>
      </div>
    </div>
  );
}
