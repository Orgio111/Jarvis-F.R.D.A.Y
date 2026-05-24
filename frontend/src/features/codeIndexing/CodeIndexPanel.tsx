import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { m } from 'framer-motion';
import { Code2, FileSearch, GitBranch, Layers, Search, RefreshCw, Trash2, Network, BookOpen, AlertTriangle } from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';

interface IndexStatus {
  vectorCount: number;
  chunksCount: number;
  dimension: number;
  dirty: boolean;
  indexPath: string | null;
  isLoaded: boolean;
}

interface SearchResult {
  chunkId: string;
  filePath: string;
  language: string;
  startLine: number;
  endLine: number;
  signature: string;
  chunkType: string;
  score: number;
  content: string;
  searchMethod?: string;
  symbols?: string[];
  imports?: string[];
}

interface SearchResponse {
  query: string;
  total: number;
  results: SearchResult[];
  methods: Record<string, number>;
}

interface ArchitectureSummary {
  status: string;
  summary: {
    fileCount: number;
    chunkCount: number;
    languages: Record<string, number>;
    chunkTypes: Record<string, number>;
    symbolCount: number;
  };
  languages: string[];
  apiSurface: { name: string; type: string; file: string; language: string }[];
  directoryTree?: unknown;
}

type Tab = 'search' | 'status' | 'architecture' | 'dependencies';

export function CodeIndexPanel() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>('status');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchMeta, setSearchMeta] = useState({ total: 0, methods: {} as Record<string, number> });

  // ─── Status ──────────────────────────────────────────────────────────────
  const { data: status, isLoading: statusLoading } = useQuery<IndexStatus>({
    queryKey: ['code-index-status'],
    queryFn: () => apiClient.get<IndexStatus>('/code-index/status'),
    enabled: bootstrapReady,
    refetchInterval: 10_000,
  });

  // ─── Architecture ─────────────────────────────────────────────────────────
  const { data: architecture, isLoading: archLoading } = useQuery<ArchitectureSummary>({
    queryKey: ['code-index-architecture'],
    queryFn: () => apiClient.get<ArchitectureSummary>('/code-index/analyze'),
    enabled: bootstrapReady && activeTab === 'architecture',
    ...freshness.slowlyChanging,
  });

  // ─── Index Mutation ───────────────────────────────────────────────────────
  const indexMut = useMutation({
    mutationFn: (force?: boolean) =>
      apiClient.post('/code-index/index', { force: force ?? false, maxFiles: 10000 }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['code-index-status'] });
      queryClient.invalidateQueries({ queryKey: ['code-index-architecture'] });
    },
  });

  // ─── Clear Mutation ───────────────────────────────────────────────────────
  const clearMut = useMutation({
    mutationFn: () => apiClient.delete('/code-index/clear'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['code-index-status'] });
      queryClient.invalidateQueries({ queryKey: ['code-index-architecture'] });
    },
  });

  // ─── Search ───────────────────────────────────────────────────────────────
  const searchMut = useMutation({
    mutationFn: (q: string) =>
      apiClient.post<SearchResponse>('/code-index/search', { query: q, topK: 20 }),
    onSuccess: (res) => {
      setSearchResults(res.results ?? []);
      setSearchMeta({ total: res.total, methods: res.methods });
    },
  });

  const handleSearch = useCallback(() => {
    if (!searchQuery.trim()) return;
    searchMut.mutate(searchQuery.trim());
  }, [searchQuery, searchMut]);

  // ─── Tabs ─────────────────────────────────────────────────────────────────
  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'status', label: 'Status', icon: <Layers size={14} /> },
    { id: 'search', label: 'Code Search', icon: <Search size={14} /> },
    { id: 'architecture', label: 'Architecture', icon: <GitBranch size={14} /> },
    { id: 'dependencies', label: 'Dependencies', icon: <Network size={14} /> },
  ];

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader
        title="Code Intelligence"
        subtitle="Semantic code indexing, search, and architecture analysis"
        action={
          <div className="flex gap-2">
            <button
              className="btn-cockpit-ghost px-3 py-1.5 text-xs flex items-center gap-1.5"
              onClick={() => indexMut.mutate(false)}
              disabled={indexMut.isPending}
            >
              <RefreshCw size={12} className={indexMut.isPending ? 'animate-spin' : ''} />
              {indexMut.isPending ? 'Indexing…' : 'Index'}
            </button>
            <button
              className="btn-cockpit-ghost px-3 py-1.5 text-xs flex items-center gap-1.5 text-jarvis-red/70 hover:text-jarvis-red"
              onClick={() => clearMut.mutate()}
              disabled={clearMut.isPending}
            >
              <Trash2 size={12} />
              Clear
            </button>
          </div>
        }
      />

      {/* Tab bar */}
      <div className="flex gap-1 mb-5 border-b border-jarvis-border/20 pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono flex items-center gap-1.5 transition-all ${
              activeTab === tab.id
                ? 'bg-jarvis-cyan/10 text-jarvis-cyan border border-jarvis-cyan/30'
                : 'text-jarvis-text-dim hover:text-jarvis-text-bright hover:bg-jarvis-bg-2/50'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* ─── Status Tab ─────────────────────────────────────────────────── */}
      {activeTab === 'status' && (
        <div className="space-y-4">
          {statusLoading ? (
            <GlassPanel className="p-8 flex items-center justify-center">
              <p className="text-jarvis-text-dim text-sm font-mono animate-pulse">Loading index status…</p>
            </GlassPanel>
          ) : status ? (
            <>
              <GlassPanel className="p-5" hover glow>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Code2 size={16} className="text-jarvis-cyan" />
                    <span className="text-jarvis-text-bright text-sm font-mono">Vector Index</span>
                  </div>
                  <NeonBadge
                    color={status.isLoaded && status.vectorCount > 0 ? 'green' : 'dim'}
                    label={status.isLoaded ? (status.vectorCount > 0 ? 'ACTIVE' : 'EMPTY') : 'NOT LOADED'}
                    pulse={status.vectorCount > 0}
                    size="sm"
                  />
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard label="Vectors" value={status.vectorCount.toLocaleString()} />
                  <StatCard label="Chunks" value={status.chunksCount.toLocaleString()} />
                  <StatCard label="Dimension" value={status.dimension.toString()} />
                  <StatCard label="Dirty" value={status.dirty ? 'Yes' : 'No'} pulse={status.dirty} />
                </div>
              </GlassPanel>

              <GlassPanel className="p-5">
                <SectionHeader title="Quick Actions" />
                <div className="flex flex-wrap gap-3">
                  <button
                    className="btn-cockpit-primary px-4 py-2 text-xs"
                    onClick={() => indexMut.mutate(false)}
                    disabled={indexMut.isPending}
                  >
                    <RefreshCw size={12} className="inline mr-1.5" />
                    Index Repo
                  </button>
                  <button
                    className="btn-cockpit-ghost px-4 py-2 text-xs"
                    onClick={() => indexMut.mutate(true)}
                    disabled={indexMut.isPending}
                  >
                    Force Rebuild
                  </button>
                  <button
                    className="btn-cockpit-ghost px-4 py-2 text-xs text-jarvis-red/70 hover:text-jarvis-red"
                    onClick={() => clearMut.mutate()}
                    disabled={clearMut.isPending}
                  >
                    <Trash2 size={12} className="inline mr-1.5" />
                    Clear Index
                  </button>
                </div>
              </GlassPanel>

              {indexMut.isPending && (
                <GlassPanel className="p-4">
                  <div className="flex items-center gap-3">
                    <RefreshCw size={18} className="text-jarvis-cyan animate-spin" />
                    <div>
                      <p className="text-jarvis-text-bright text-sm font-mono">Indexing in progress…</p>
                      <p className="text-jarvis-text-dim text-xs font-mono">
                        Walking repo, chunking files, embedding vectors. This may take a moment.
                      </p>
                    </div>
                  </div>
                </GlassPanel>
              )}

              {indexMut.isSuccess && (
                <GlassPanel className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-jarvis-green/10 border border-jarvis-green/30 flex items-center justify-center">
                      <div className="w-2 h-2 rounded-full bg-jarvis-green" />
                    </div>
                    <div>
                      <p className="text-jarvis-text-bright text-sm font-mono">Indexing complete</p>
                      <p className="text-jarvis-text-dim text-xs font-mono">
                        Files processed: {indexMut.data?.filesProcessed ?? '?'} | Chunks indexed: {indexMut.data?.chunksIndexed ?? '?'}
                      </p>
                    </div>
                  </div>
                </GlassPanel>
              )}
            </>
          ) : (
            <GlassPanel className="p-8 flex items-center justify-center">
              <div className="text-center">
                <Code2 size={32} className="mx-auto mb-3 text-jarvis-text-dim/30" />
                <p className="text-jarvis-text-dim text-sm font-mono">Code indexing service not available</p>
                <p className="text-jarvis-text-dim text-xs font-mono mt-1">Ensure the AI service is running with code indexing enabled.</p>
              </div>
            </GlassPanel>
          )}
        </div>
      )}

      {/* ─── Search Tab ──────────────────────────────────────────────────── */}
      {activeTab === 'search' && (
        <div className="space-y-4">
          <GlassPanel className="p-5">
            <div className="flex gap-2 mb-3">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-text-dim" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder='Search code… e.g. "authentication middleware" or "UserService"'
                  className="w-full bg-jarvis-bg border border-jarvis-border rounded pl-9 pr-3 py-2 text-sm font-mono text-jarvis-text-bright placeholder-jarvis-text-dim focus:outline-none focus:border-jarvis-cyan/60"
                />
              </div>
              <button
                className="btn-cockpit-primary px-5 py-2 text-sm"
                onClick={handleSearch}
                disabled={!searchQuery.trim() || searchMut.isPending}
              >
                {searchMut.isPending ? (
                  <RefreshCw size={14} className="animate-spin" />
                ) : (
                  <FileSearch size={14} />
                )}
              </button>
            </div>
            {status && status.vectorCount === 0 && (
              <p className="text-jarvis-yellow text-xs font-mono flex items-center gap-1.5">
                <AlertTriangle size={12} />
                No code indexed yet. Go to Status tab and click "Index" first.
              </p>
            )}
          </GlassPanel>

          {searchMut.isSuccess && (
            <>
              <p className="text-jarvis-text-dim text-xs font-mono">
                {searchMeta.total} result{searchMeta.total !== 1 ? 's' : ''}
                {Object.entries(searchMeta.methods).map(([k, v]) => (
                  <span key={k} className="ml-2 opacity-60">· {k}: {v}</span>
                ))}
              </p>

              {searchResults.map((result, i) => (
                <GlassPanel key={result.chunkId || i} className="p-4" hover>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-jarvis-text-bright text-xs font-mono font-semibold truncate">
                        {result.signature}
                      </p>
                      <p className="text-jarvis-cyan text-[10px] font-mono truncate mt-0.5">
                        {result.filePath}:{result.startLine}-{result.endLine}
                      </p>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      <NeonBadge label={result.language} color="blue" size="sm" />
                      <NeonBadge label={result.chunkType} color="purple" size="sm" />
                      {result.searchMethod && (
                        <NeonBadge label={result.searchMethod} color="cyan" size="sm" />
                      )}
                    </div>
                  </div>
                  <pre className="text-jarvis-text-dim text-[10px] font-mono leading-relaxed max-h-24 overflow-hidden bg-jarvis-bg/50 rounded-lg p-3 border border-jarvis-border/10">
                    {result.content.slice(0, 500)}
                  </pre>
                  <div className="flex items-center gap-2 mt-2">
                    {result.symbols && result.symbols.length > 0 && (
                      <span className="text-[10px] font-mono text-jarvis-text-dim bg-jarvis-bg-2/50 px-2 py-0.5 rounded">
                        symbols: {result.symbols.join(', ')}
                      </span>
                    )}
                    <span className="text-[10px] font-mono text-jarvis-text-dim/60">
                      score: {result.score.toFixed(3)}
                    </span>
                  </div>
                </GlassPanel>
              ))}

              {searchResults.length === 0 && (
                <GlassPanel className="p-6 text-center">
                  <FileSearch size={24} className="mx-auto mb-2 text-jarvis-text-dim/30" />
                  <p className="text-jarvis-text-dim text-xs font-mono">No results found</p>
                </GlassPanel>
              )}
            </>
          )}
        </div>
      )}

      {/* ─── Architecture Tab ────────────────────────────────────────────── */}
      {activeTab === 'architecture' && (
        <div className="space-y-4">
          {archLoading ? (
            <GlassPanel className="p-8 flex items-center justify-center">
              <p className="text-jarvis-text-dim text-sm font-mono animate-pulse">Analyzing architecture…</p>
            </GlassPanel>
          ) : architecture ? (
            <>
              <GlassPanel className="p-5" hover glow>
                <div className="flex items-center gap-2 mb-4">
                  <GitBranch size={16} className="text-jarvis-green" />
                  <span className="text-jarvis-text-bright text-sm font-mono">Architecture Summary</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard label="Files" value={architecture.summary.fileCount.toLocaleString()} />
                  <StatCard label="Chunks" value={architecture.summary.chunkCount.toLocaleString()} />
                  <StatCard label="Symbols" value={architecture.summary.symbolCount.toLocaleString()} />
                  <StatCard label="Languages" value={architecture.languages.length.toString()} />
                </div>
              </GlassPanel>

              <GlassPanel className="p-5">
                <SectionHeader title="Languages" />
                <div className="space-y-2">
                  {Object.entries(architecture.summary.languages).map(([lang, count]) => (
                    <div key={lang} className="flex items-center justify-between">
                      <span className="text-jarvis-text text-xs font-mono">{lang}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-32 h-1.5 bg-jarvis-bg-3/50 rounded-full overflow-hidden">
                          <m.div
                            className="h-full rounded-full bg-jarvis-cyan"
                            initial={{ width: 0 }}
                            animate={{
                              width: `${(count / architecture.summary.fileCount) * 100}%`,
                            }}
                            transition={{ duration: 0.5 }}
                          />
                        </div>
                        <span className="text-jarvis-text-dim text-[10px] font-mono w-12 text-right">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </GlassPanel>

              <GlassPanel className="p-5">
                <SectionHeader
                  title="API Surface"
                  subtitle={`${architecture.apiSurface.length} exported symbols`}
                />
                <div className="max-h-64 overflow-y-auto space-y-1">
                  {architecture.apiSurface.slice(0, 30).map((item, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 p-2 rounded-lg bg-jarvis-bg/30 border border-jarvis-border/10 text-xs font-mono"
                    >
                      <span className={`w-3 h-3 rounded-full ${
                        item.type === 'class' ? 'bg-jarvis-green' : 'bg-jarvis-cyan'
                      }`} />
                      <span className="text-jarvis-text-bright">{item.name}</span>
                      <span className="text-jarvis-text-dim text-[10px]">{item.type}</span>
                      <span className="text-jarvis-text-dim/50 ml-auto truncate max-w-[200px]">{item.file}</span>
                    </div>
                  ))}
                </div>
              </GlassPanel>
            </>
          ) : (
            <GlassPanel className="p-8 flex items-center justify-center">
              <p className="text-jarvis-text-dim text-sm font-mono">Index the repo first to view architecture analysis.</p>
            </GlassPanel>
          )}
        </div>
      )}

      {/* ─── Dependencies Tab ────────────────────────────────────────────── */}
      {activeTab === 'dependencies' && (
        <GlassPanel className="p-8 flex items-center justify-center">
          <div className="text-center">
            <Network size={32} className="mx-auto mb-3 text-jarvis-text-dim/30" />
            <p className="text-jarvis-text-dim text-sm font-mono">Dependency Graph</p>
            <p className="text-jarvis-text-dim text-xs font-mono mt-1">Index the repo to view dependency relationships.</p>
          </div>
        </GlassPanel>
      )}
    </div>
  );
}

function StatCard({ label, value, pulse = false }: { label: string; value: string; pulse?: boolean }) {
  return (
    <div className="p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
      <p className="text-jarvis-text-dim text-[10px] font-mono mb-1">{label}</p>
      <p className={`text-jarvis-text-bright text-lg font-mono font-semibold ${pulse ? 'animate-pulse' : ''}`}>
        {value}
      </p>
    </div>
  );
}

export default CodeIndexPanel;
