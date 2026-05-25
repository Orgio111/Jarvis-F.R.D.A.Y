import { useState } from 'react';
import { useMemoryFabricStatus, useMemoryFabricStats, useRecentMemories, useSearchMemory, useStoreMemory, usePruneMemory, useCrossLayerQuery } from './useMemoryFabric';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { CockpitButton } from '@/components/ui/CockpitButton';
import { Database, Search, Plus, Trash2, Layers, Brain, BookOpen, Clock } from 'lucide-react';

const LAYER_ICONS: Record<string, React.ReactNode> = {
  episodic: <Clock size={14} />,
  semantic: <Brain size={14} />,
  procedural: <BookOpen size={14} />,
};

const LAYER_COLORS: Record<string, string> = {
  episodic: 'blue',
  semantic: 'purple',
  procedural: 'green',
};

export function MemoryFabricPanel() {
  const [activeTab, setActiveTab] = useState<'browse' | 'store' | 'search'>('browse');
  const [selectedLayer, setSelectedLayer] = useState<string | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [storeContent, setStoreContent] = useState('');
  const [storeLayer, setStoreLayer] = useState('episodic');
  const [storeTags, setStoreTags] = useState('');

  const { data: status } = useMemoryFabricStatus();
  const { data: stats } = useMemoryFabricStats();
  const { data: recentData } = useRecentMemories(selectedLayer, 20);

  const searchMut = useSearchMemory();
  const storeMut = useStoreMemory();
  const pruneMut = usePruneMemory();
  const crossLayerMut = useCrossLayerQuery();

  const recent = recentData?.results ?? [];
  const entriesByLayer = stats?.entriesByLayer ?? {};
  const totalEntries = stats?.totalEntries ?? status?.totalEntries ?? 0;

  const handleSearch = () => {
    if (!searchQuery.trim()) return;
    searchMut.mutate(
      { query: searchQuery, layer: selectedLayer, limit: 20 },
      { onSuccess: (data: any) => setSearchResults(data.results ?? []) }
    );
  };

  const handleStore = () => {
    if (!storeContent.trim()) return;
    storeMut.mutate({
      content: storeContent,
      layer: storeLayer,
      tags: storeTags,
    });
    setStoreContent('');
    setStoreTags('');
  };

  const handleCrossLayer = (topic: string) => {
    crossLayerMut.mutate(topic);
  };

  const isSearching = searchMut.isPending;
  const isStoring = storeMut.isPending;

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <SectionHeader
            title="Memory Fabric"
            subtitle="Multi-layered cognitive memory — episodic · semantic · procedural"
            icon={Database}
          />
        </div>
        <div className="flex items-center gap-3">
          <NeonBadge color="cyan" label={`${totalEntries} entries`} size="sm" />
          {stats && <NeonBadge color="green" label={`${stats.uniqueTags} tags`} size="sm" />}
        </div>
      </div>

      {/* Layer summary */}
      {stats && (
        <GlassPanel className="p-4">
          <div className="grid grid-cols-3 gap-4">
            {['episodic', 'semantic', 'procedural'].map(layer => (
              <button
                key={layer}
                onClick={() => setSelectedLayer(selectedLayer === layer ? undefined : layer)}
                className={`p-3 rounded-lg border transition-all duration-200 text-left ${
                  selectedLayer === layer
                    ? 'border-jarvis-cyan/40 bg-jarvis-cyan/5'
                    : 'border-jarvis-border/20 bg-jarvis-bg-2/30 hover:border-jarvis-border/40'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  {LAYER_ICONS[layer]}
                  <span className="text-xs font-mono text-jarvis-text-bright capitalize">{layer}</span>
                </div>
                <p className="text-lg font-mono font-bold text-jarvis-text-bright">
                  {entriesByLayer[layer] ?? 0}
                </p>
                <p className="text-[10px] font-mono text-jarvis-text-dim/60">entries</p>
              </button>
            ))}
          </div>
          <div className="flex items-center gap-4 mt-3 pt-3 border-t border-jarvis-border/20 text-[10px] font-mono text-jarvis-text-dim/60">
            <span>Avg Importance: {stats.avgImportance.toFixed(2)}</span>
            <span>Avg Confidence: {stats.avgConfidence.toFixed(2)}</span>
            <div className="flex-1" />
            <CockpitButton icon={<Trash2 size={12} />} onClick={() => pruneMut.mutate()} size="sm" variant="ghost" loading={pruneMut.isPending}>Prune</CockpitButton>
          </div>
        </GlassPanel>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-jarvis-border/20">
        {(['browse', 'store', 'search'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-mono tracking-wider transition-all duration-200 border-b-2 ${
              activeTab === tab
                ? 'text-jarvis-cyan border-jarvis-cyan'
                : 'text-jarvis-text-dim/60 hover:text-jarvis-text border-transparent'
            }`}
          >
            {tab === 'browse' ? 'Browse' : tab === 'store' ? 'Store' : 'Search'}
          </button>
        ))}
      </div>

      {/* Browse tab */}
      {activeTab === 'browse' && (
        <div className="space-y-2">
          {recent.length === 0 && (
            <GlassPanel className="p-8 flex flex-col items-center justify-center gap-3">
              <Database size={32} className="text-jarvis-text-dim/30" />
              <p className="text-jarvis-text-dim text-xs font-mono">No memory entries yet</p>
            </GlassPanel>
          )}
          {recent.map((entry: any) => (
            <GlassPanel key={entry.entryId} className="p-3">
              <div className="flex items-start gap-3">
                <div className="mt-0.5">{LAYER_ICONS[entry.layer]}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono text-jarvis-text-bright leading-relaxed">{entry.content}</p>
                  <div className="flex items-center gap-3 mt-2 text-[10px] font-mono text-jarvis-text-dim/60">
                    <NeonBadge
                      color={(LAYER_COLORS[entry.layer] ?? 'cyan') as any}
                      label={entry.layer}
                      size="sm"
                    />
                    {entry.tags.length > 0 && entry.tags.map((tag: string) => (
                      <span key={tag} className="px-1.5 py-0.5 rounded bg-jarvis-bg-3/60 text-[10px]">#{tag}</span>
                    ))}
                    <span className="ml-auto">R{entry.relevanceScore.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </GlassPanel>
          ))}
        </div>
      )}

      {/* Store tab */}
      {activeTab === 'store' && (
        <GlassPanel className="p-4 space-y-3">
          <p className="text-jarvis-cyan text-xs font-mono font-bold uppercase tracking-wider">Store New Memory</p>
          <div>
            <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Content</label>
            <textarea
              value={storeContent}
              onChange={(e) => setStoreContent(e.target.value)}
              rows={3}
              className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50 resize-none"
              placeholder="Enter memory content..."
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Layer</label>
              <select
                value={storeLayer}
                onChange={(e) => setStoreLayer(e.target.value)}
                className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50"
              >
                <option value="episodic">Episodic (events)</option>
                <option value="semantic">Semantic (concepts)</option>
                <option value="procedural">Procedural (patterns)</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Tags (comma-separated)</label>
              <input
                value={storeTags}
                onChange={(e) => setStoreTags(e.target.value)}
                className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50"
                placeholder="tag1, tag2"
              />
            </div>
          </div>
          <div className="flex justify-end">
            <CockpitButton icon={<Plus size={14} />} onClick={handleStore} size="sm" loading={isStoring}>Store</CockpitButton>
          </div>
        </GlassPanel>
      )}

      {/* Search tab */}
      {activeTab === 'search' && (
        <div className="space-y-3">
          <GlassPanel className="p-4">
            <div className="flex items-center gap-3">
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="flex-1 bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50"
                placeholder="Search memory..."
              />
              <CockpitButton icon={<Search size={14} />} onClick={handleSearch} size="sm" loading={isSearching}>Search</CockpitButton>
              <CockpitButton
                icon={<Layers size={14} />}
                onClick={() => handleCrossLayer(searchQuery)}
                size="sm"
                variant="ghost"
                loading={crossLayerMut.isPending}
              >Cross-Layer</CockpitButton>
            </div>
          </GlassPanel>

          {/* Search results */}
          {searchResults && (
            <div className="space-y-2">
              <p className="text-[10px] font-mono text-jarvis-text-dim/60">{searchResults.length} results</p>
              {searchResults.map((entry: any) => (
                <GlassPanel key={entry.entryId} className="p-3">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{LAYER_ICONS[entry.layer]}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono text-jarvis-text-bright leading-relaxed">{entry.content}</p>
                      <div className="flex items-center gap-2 mt-1.5 text-[10px] font-mono text-jarvis-text-dim/60">
                        <NeonBadge color={(LAYER_COLORS[entry.layer] ?? 'cyan') as any} label={entry.layer} size="sm" />
                        <span>R{entry.relevanceScore.toFixed(2)}</span>
                        <span>I{entry.importance.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                </GlassPanel>
              ))}
            </div>
          )}

          {/* Cross-layer results */}
          {(crossLayerMut.data as any) && (
            <GlassPanel className="p-4">
              <p className="text-jarvis-cyan text-xs font-mono font-bold uppercase tracking-wider mb-3">Cross-Layer Results</p>
              {['episodic', 'semantic', 'procedural'].map(layer => {
                const results = (crossLayerMut.data as any)?.data?.[layer] ?? [];
                return (
                  <div key={layer} className="mb-3 last:mb-0">
                    <div className="flex items-center gap-2 mb-1">
                      {LAYER_ICONS[layer]}
                      <span className="text-xs font-mono text-jarvis-text-bright capitalize">{layer}</span>
                      <span className="text-[10px] font-mono text-jarvis-text-dim/60">({results.length})</span>
                    </div>
                    {results.length === 0 && (
                      <p className="text-[10px] font-mono text-jarvis-text-dim/40 ml-6">No matches</p>
                    )}
                    {results.slice(0, 3).map((entry: any) => (
                      <p key={entry.entryId} className="text-[10px] font-mono text-jarvis-text-dim/80 ml-6 truncate">{entry.content}</p>
                    ))}
                  </div>
                );
              })}
            </GlassPanel>
          )}
        </div>
      )}
    </div>
  );
}
