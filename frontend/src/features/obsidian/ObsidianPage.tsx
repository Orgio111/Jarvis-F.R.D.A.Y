import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useObsidian } from './useObsidian';
import { GraphCanvas } from './GraphCanvas';
import { apiClient } from '@/lib/api/client';
import type { GraphNode } from './useObsidian';

const TYPE_COLORS: Record<string, string> = {
  agent:       'bg-blue-500',
  swarm:       'bg-purple-500',
  memory:      'bg-emerald-500',
  task:        'bg-amber-500',
  improvement: 'bg-red-500',
  note:        'bg-gray-500',
};

export const ObsidianPage: React.FC = () => {
  const {
    status,
    files,
    graph,
    fileContent,
    selectedFile,
    loading,
    error,
    fetchGraph,
    readFile,
  } = useObsidian();

  const [tab, setTab] = useState<'graph' | 'files' | 'viewer' | 'memory' | 'fabric' | 'replays'>('graph');
  const [fileSearch, setFileSearch] = useState('');

  // ── Memory entries (Merge: Memory → Obsidian) ──
  const { data: memoryEntries } = useQuery<{ entries: Array<{ id: string; title: string; type: string; timestamp: string; summary: string }> }>({
    queryKey: ['memory', 'entries'],
    queryFn: () => apiClient.get('/memory/entries?limit=20'),
    enabled: tab === 'memory',
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });

  // ── Memory Fabric (Merge: Memory Fabric → Obsidian) ──
  const { data: fabricData } = useQuery<{ status: string; activeThreads: number; totalContexts: number; recentMemories: Array<{ id: string; label: string; type: string }> }>({
    queryKey: ['memory-fabric', 'status'],
    queryFn: () => apiClient.get('/memory-fabric/status'),
    enabled: tab === 'fabric',
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });

  // ── Session Replays (Merge: Session Replay → Obsidian) ──
  const { data: replayData } = useQuery<{ sessions: Array<{ id: string; label: string; messageCount: number; duration: string; timestamp: string }> }>({
    queryKey: ['session-replay', 'list'],
    queryFn: () => apiClient.get('/session-replay/list?limit=20'),
    enabled: tab === 'replays',
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });

  const handleNodeClick = (node: GraphNode) => {
    readFile(node.path);
    setTab('viewer');
  };

  const filteredFiles = files.filter((f) =>
    f.toLowerCase().includes(fileSearch.toLowerCase())
  );

  return (
    <div className="p-6 space-y-4 max-w-6xl mx-auto h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">🧠 Obsidian Vault</h1>
          <p className="text-gray-400 text-xs mt-0.5">
            Jarvis memory brain — live knowledge graph
          </p>
        </div>
        <div className="flex items-center gap-3">
          {status && (
            <div className="flex items-center gap-3 text-xs text-gray-400">
              <span>{status.file_count} notes</span>
              <span>{(status.size_bytes / 1024).toFixed(1)} KB</span>
              <div className={`h-2 w-2 rounded-full ${status.enabled ? 'bg-green-400' : 'bg-gray-500'}`} />
              <span>{status.enabled ? 'active' : 'disabled'}</span>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-xs">
          {error}
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-3 flex-wrap">
        {Object.entries(TYPE_COLORS).map(([type, cls]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div className={`h-2.5 w-2.5 rounded-full ${cls}`} />
            <span className="text-gray-400 text-xs capitalize">{type}</span>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-700 flex-wrap">
        {(['graph', 'files', 'viewer', 'memory', 'fabric', 'replays'] as const).map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              if (t === 'graph' && !graph) fetchGraph();
            }}
            className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors capitalize ${
              tab === t
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            {t === 'graph' ? '🌐 Graph' : t === 'files' ? '📁 Files' : t === 'viewer' ? '📄 Viewer' : t === 'memory' ? '💾 Memory' : t === 'fabric' ? '🧵 Fabric' : '⏪ Replays'}
          </button>
        ))}
        {tab === 'graph' && (
          <button
            onClick={fetchGraph}
            disabled={loading}
            className="ml-auto px-3 py-1.5 text-xs text-gray-400 hover:text-white transition-colors disabled:opacity-50"
          >
            {loading ? 'Loading...' : '↺ Refresh'}
          </button>
        )}
      </div>

      {/* Tab content */}
      <div className="flex-1 min-h-0">
        {/* Graph tab */}
        {tab === 'graph' && (
          <div className="h-full">
            {!graph ? (
              <div className="h-96 flex flex-col items-center justify-center gap-4">
                <p className="text-gray-400 text-sm">
                  Load the knowledge graph to visualise agent memory connections
                </p>
                <button
                  onClick={fetchGraph}
                  disabled={loading}
                  className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
                >
                  {loading ? 'Building graph...' : 'Load Graph'}
                </button>
              </div>
            ) : graph.node_count === 0 ? (
              <div className="h-96 flex items-center justify-center">
                <p className="text-gray-500 text-sm">
                  No notes yet — vault is empty. Start using Jarvis and notes will appear here.
                </p>
              </div>
            ) : (
              <div className="space-y-2 h-full">
                <div className="text-xs text-gray-500">
                  {graph.node_count} nodes · {graph.edge_count} connections
                  {' · '}
                  <span className="text-gray-400">Click a node to read the note</span>
                </div>
                <div className="rounded-xl overflow-hidden border border-gray-700" style={{ height: '480px' }}>
                  <GraphCanvas
                    nodes={graph.nodes}
                    edges={graph.edges}
                    onNodeClick={handleNodeClick}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Files tab */}
        {tab === 'files' && (
          <div className="space-y-3">
            <input
              type="text"
              placeholder="Search files..."
              value={fileSearch}
              onChange={(e) => setFileSearch(e.target.value)}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
            <div className="space-y-1 max-h-[500px] overflow-y-auto">
              {filteredFiles.length === 0 ? (
                <div className="text-gray-500 text-sm text-center py-8">
                  {files.length === 0 ? 'Vault is empty' : 'No files match'}
                </div>
              ) : (
                filteredFiles.map((f) => {
                  const parts = f.split('/');
                  const folder = parts.length > 1 ? parts[0] : '';
                  const name = parts[parts.length - 1].replace('.md', '');
                  return (
                    <button
                      key={f}
                      onClick={() => { readFile(f); setTab('viewer'); }}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left hover:bg-gray-700/60 transition-colors ${
                        selectedFile === f ? 'bg-gray-700/80 border border-gray-600' : ''
                      }`}
                    >
                      <span className="text-lg">📄</span>
                      <div>
                        <div className="text-white text-xs font-medium">{name}</div>
                        {folder && <div className="text-gray-500 text-xs">{folder}/</div>}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* Viewer tab */}
        {tab === 'viewer' && (
          <div className="space-y-3 h-full flex flex-col">
            {selectedFile && (
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span>📄</span>
                <span className="font-mono">{selectedFile}</span>
              </div>
            )}
            {loading ? (
              <div className="text-gray-400 text-sm animate-pulse p-4">Loading...</div>
            ) : fileContent ? (
              <div className="flex-1 overflow-y-auto bg-gray-900/60 border border-gray-700 rounded-xl p-5">
                <pre className="text-gray-200 text-xs font-mono whitespace-pre-wrap leading-relaxed">
                  {fileContent}
                </pre>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
                Select a file from the Files tab or click a graph node
              </div>
            )}
          </div>
        )}

        {/* Memory tab (Merge: Memory → Obsidian) */}
        {tab === 'memory' && (
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {memoryEntries?.entries?.length === 0 && (
              <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
                No memory entries yet
              </div>
            )}
            {memoryEntries?.entries?.map((entry) => (
              <div
                key={entry.id}
                className="flex items-start gap-3 p-3 rounded-lg bg-gray-800/50 border border-gray-700/50 hover:border-blue-500/30 transition-colors"
              >
                <div className={`w-2 h-2 rounded-full mt-1.5 ${
                  entry.type === 'agent' ? 'bg-blue-400' :
                  entry.type === 'task' ? 'bg-amber-400' :
                  entry.type === 'note' ? 'bg-gray-400' : 'bg-emerald-400'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-white text-xs font-medium truncate">{entry.title}</span>
                    <span className="text-[10px] font-mono text-gray-500 capitalize">{entry.type}</span>
                  </div>
                  {entry.summary && (
                    <p className="text-gray-400 text-[11px] mt-0.5 line-clamp-2">{entry.summary}</p>
                  )}
                  {entry.timestamp && (
                    <p className="text-gray-600 text-[10px] mt-1 font-mono">{entry.timestamp}</p>
                  )}
                </div>
              </div>
            ))}
            {!memoryEntries && (
              <div className="text-gray-500 text-sm text-center py-8">Loading memory entries...</div>
            )}
          </div>
        )}

        {/* Fabric tab (Merge: Memory Fabric → Obsidian) */}
        {tab === 'fabric' && (
          <div className="space-y-3 max-h-[500px] overflow-y-auto">
            {fabricData ? (
              <>
                <div className="flex items-center gap-3 flex-wrap">
                  <div className="px-3 py-1.5 rounded-lg bg-gray-800/60 border border-gray-700/50">
                    <p className="text-gray-500 text-[10px] font-mono">Status</p>
                    <p className="text-white text-xs font-mono mt-0.5 capitalize">{fabricData.status}</p>
                  </div>
                  <div className="px-3 py-1.5 rounded-lg bg-gray-800/60 border border-gray-700/50">
                    <p className="text-gray-500 text-[10px] font-mono">Active Threads</p>
                    <p className="text-white text-xs font-mono mt-0.5">{fabricData.activeThreads}</p>
                  </div>
                  <div className="px-3 py-1.5 rounded-lg bg-gray-800/60 border border-gray-700/50">
                    <p className="text-gray-500 text-[10px] font-mono">Total Contexts</p>
                    <p className="text-white text-xs font-mono mt-0.5">{fabricData.totalContexts}</p>
                  </div>
                </div>

                {fabricData.recentMemories?.length > 0 && (
                  <div>
                    <p className="text-gray-400 text-xs font-medium mb-2">Recent Fabric Memories</p>
                    <div className="space-y-1.5">
                      {fabricData.recentMemories.map((m) => (
                        <div key={m.id} className="flex items-center gap-2 p-2.5 rounded-lg bg-gray-800/40 border border-gray-700/30">
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            m.type === 'memory' ? 'bg-emerald-400' :
                            m.type === 'context' ? 'bg-blue-400' : 'bg-gray-400'
                          }`} />
                          <span className="text-gray-300 text-xs font-mono">{m.label}</span>
                          <span className="text-gray-600 text-[10px] font-mono ml-auto">{m.type}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-gray-500 text-sm text-center py-8">Loading fabric data...</div>
            )}
          </div>
        )}

        {/* Replays tab (Merge: Session Replay → Obsidian) */}
        {tab === 'replays' && (
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {replayData?.sessions?.length === 0 && (
              <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
                No recorded sessions yet
              </div>
            )}
            {replayData?.sessions?.map((session) => (
              <div
                key={session.id}
                className="flex items-start gap-3 p-3 rounded-lg bg-gray-800/50 border border-gray-700/50 hover:border-purple-500/30 transition-colors cursor-pointer"
              >
                <div className="w-7 h-7 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center shrink-0">
                  <span className="text-purple-400 text-xs">⏪</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-white text-xs font-medium truncate">{session.label || 'Unnamed Session'}</span>
                    <span className="text-gray-500 text-[10px] font-mono">{session.messageCount} messages</span>
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    {session.duration && (
                      <span className="text-gray-500 text-[10px] font-mono">{session.duration}</span>
                    )}
                    {session.timestamp && (
                      <span className="text-gray-600 text-[10px] font-mono">{session.timestamp}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {!replayData && (
              <div className="text-gray-500 text-sm text-center py-8">Loading sessions...</div>
            )}
          </div>
        )}
      </div>

      {/* Vault path footer */}
      {status?.vault && (
        <div className="text-xs text-gray-600 font-mono truncate">
          Vault: {status.vault}
        </div>
      )}
    </div>
  );
};
