import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';

interface SearchStatus {
  enabled: boolean;
  deepSearchEnabled: boolean;
  engine: string;
}

interface SearchResult {
  title: string;
  snippet: string;
  url: string;
  source: string;
  type: string;
}

interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  engine: string;
}

export function SearchPanel() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState(5);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [lastQuery, setLastQuery] = useState('');

  const { data: status } = useQuery<SearchStatus>({
    queryKey: ['search-status'],
    queryFn: () => apiClient.get<SearchStatus>('/search/status'),
    enabled: bootstrapReady,
    ...freshness.slowlyChanging,
  });

  const searchMut = useMutation({
    mutationFn: ({ q, n }: { q: string; n: number }) =>
      apiClient.post<SearchResponse>('/search', { query: q, maxResults: n }),
    onSuccess: (res) => {
      setResults(res.results ?? []);
      setLastQuery(res.query);
    },
  });

  const handleSearch = () => {
    if (!query.trim()) return;
    searchMut.mutate({ q: query.trim(), n: maxResults });
  };

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader title="Web Search" subtitle="DuckDuckGo — no API key required" />

      {status && (
        <GlassPanel className="p-4 mt-6 mb-4">
          <div className="flex items-center gap-4 flex-wrap">
            <StatusDot status={status.enabled ? 'online' : 'offline'} label={status.enabled ? 'enabled' : 'disabled'} />
            <span className="text-jarvis-text-dim text-xs font-mono">engine: {status.engine}</span>
            {status.deepSearchEnabled && (
              <span className="text-jarvis-cyan text-xs font-mono border border-jarvis-cyan/30 rounded px-1.5 py-0.5">deep search</span>
            )}
          </div>
        </GlassPanel>
      )}

      <GlassPanel className="p-5 mb-4">
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search the web…"
            className="flex-1 bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-sm font-mono text-jarvis-text-bright placeholder-jarvis-text-dim focus:outline-none focus:border-jarvis-cyan/60"
          />
          <select
            value={maxResults}
            onChange={(e) => setMaxResults(Number(e.target.value))}
            className="bg-jarvis-bg border border-jarvis-border rounded px-2 py-2 text-xs font-mono text-jarvis-text-bright focus:outline-none focus:border-jarvis-cyan/60"
          >
            {[3, 5, 10, 20].map((n) => (
              <option key={n} value={n}>{n} results</option>
            ))}
          </select>
          <button
            className="btn-cockpit-primary px-5 py-2 text-sm"
            onClick={handleSearch}
            disabled={!query.trim() || searchMut.isPending || !status?.enabled}
          >
            {searchMut.isPending ? 'Searching…' : 'Search'}
          </button>
        </div>
        {!status?.enabled && (
          <p className="text-jarvis-red text-xs font-mono">Web search is disabled. Enable it in settings.</p>
        )}
      </GlassPanel>

      {searchMut.isSuccess && results.length > 0 && (
        <div className="space-y-3">
          <p className="text-jarvis-text-dim text-xs font-mono">
            {results.length} result{results.length !== 1 ? 's' : ''} for "{lastQuery}"
          </p>
          {results.map((result, i) => (
            <GlassPanel key={i} className="p-4">
              <div className="flex items-start justify-between gap-2 mb-1">
                <p className="text-jarvis-text-bright text-sm font-mono font-semibold">{result.title}</p>
                <span className="text-xs font-mono text-jarvis-text-dim border border-jarvis-border rounded px-1.5 py-0.5 shrink-0">
                  {result.type}
                </span>
              </div>
              <p className="text-jarvis-text-dim text-xs font-mono mb-2 leading-relaxed">{result.snippet}</p>
              {result.url && (
                <p className="text-jarvis-cyan text-xs font-mono truncate">{result.url}</p>
              )}
              {result.source && (
                <p className="text-jarvis-text-dim text-xs font-mono mt-1">via {result.source}</p>
              )}
            </GlassPanel>
          ))}
        </div>
      )}

      {searchMut.isSuccess && results.length === 0 && (
        <GlassPanel className="p-4">
          <p className="text-jarvis-text-dim text-xs font-mono text-center">No results found for "{lastQuery}".</p>
        </GlassPanel>
      )}

      {searchMut.isError && (
        <GlassPanel className="p-4">
          <p className="text-jarvis-red text-xs font-mono">Search failed. Check that the AI service is running.</p>
        </GlassPanel>
      )}
    </div>
  );
}
