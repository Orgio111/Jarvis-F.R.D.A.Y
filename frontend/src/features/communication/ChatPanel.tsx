import { useEffect, useRef, useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { MessageSquare, Trash2, Search, Users, Database, RotateCcw, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useChatStore } from './chatStore';
import { useChat } from './useChat';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { ModelSelector } from './ModelSelector';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { apiClient } from '@/lib/api/client';

export function ChatPanel() {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const { sendMessage } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  // ── Search bar state (Merge: Search → Chat) ──
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const { data: searchResults } = useQuery<{ results: Array<{ title: string; snippet: string; url: string }> }>({
    queryKey: ['chat-search', searchQuery],
    queryFn: () => apiClient.post('/search', { query: searchQuery, limit: 5 }),
    enabled: searchQuery.length > 2,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });

  // ── Agent info (Merge: Multi-Agent → Chat) ──
  const { data: agentStatus } = useQuery<{ activeAgent: string; agentCount: number }>({
    queryKey: ['multi-agent', 'status'],
    queryFn: () => apiClient.get('/multi-agent/status'),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });

  // ── Memory context (Merge: Memory Fabric → Chat) ──
  const { data: fabricContext } = useQuery<{ contextCount: number; recentContext: string[] }>({
    queryKey: ['memory-fabric', 'chat-context'],
    queryFn: () => apiClient.get('/memory-fabric/chat-context?limit=3'),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });

  // ── Session Replay (Merge: Session Replay → Chat) ──
  const { data: recentSessions } = useQuery<{ sessions: Array<{ id: string; label: string; messageCount: number }> }>({
    queryKey: ['session-replay', 'recent'],
    queryFn: () => apiClient.get('/session-replay/recent?limit=5'),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full jarvis-scanlines">
      {/* Header */}
      <div className="jarvis-panel-header shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-jarvis-cyan/10 flex items-center justify-center">
            <MessageSquare size={14} className="text-jarvis-cyan" />
          </div>
          <div>
            <span className="text-jarvis-cyan text-xs font-mono font-semibold tracking-wider">CHAT</span>
            {isStreaming && (
              <m.span
                className="text-jarvis-text-dim/60 text-[10px] font-mono ml-2"
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                — streaming
              </m.span>
            )}
          </div>
          <ModelSelector disabled={isStreaming} />

          {/* Agent badge (Merge 9: Multi-Agent) */}
          {agentStatus && agentStatus.agentCount > 0 && (
            <NeonBadge color="purple" size="sm" label={`${agentStatus.activeAgent ?? 'auto'} · ${agentStatus.agentCount} agents`} />
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* Memory context indicator (Merge 8: Memory Fabric) */}
          {fabricContext && fabricContext.contextCount > 0 && (
            <NeonBadge color="green" size="sm" label={`${fabricContext.contextCount} memories`} />
          )}
          {/* Search button (Merge 5: Search) */}
          <button
            onClick={() => setShowSearch(!showSearch)}
            className={`p-1.5 rounded-lg transition-all duration-200 ${
              showSearch ? 'bg-jarvis-cyan/10 text-jarvis-cyan' : 'text-jarvis-text-dim/50 hover:text-jarvis-cyan/70'
            }`}
            title="Search"
          >
            <Search size={14} />
          </button>
          {/* Session Replay button (Merge 11: Session Replay) */}
          {recentSessions && recentSessions.sessions.length > 0 && (
            <button
              className="p-1.5 rounded-lg text-jarvis-text-dim/50 hover:text-jarvis-yellow/70 transition-all duration-200"
              title="Recent sessions"
            >
              <RotateCcw size={14} />
            </button>
          )}
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="flex items-center gap-1.5 text-jarvis-text-dim/50 text-xs font-mono hover:text-jarvis-red transition-all duration-200 px-2 py-1 rounded hover:bg-jarvis-red/5"
            >
              <Trash2 size={12} />
              clear
            </button>
          )}
        </div>
      </div>

      {/* Search bar (Merge 5: Search → Chat) */}
      <AnimatePresence>
        {showSearch && (
          <m.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-b border-jarvis-border/20"
          >
            <div className="p-3 space-y-2">
              <div className="flex items-center gap-2">
                <div className="flex-1 relative">
                  <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-text-dim/40" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search the web…"
                    className="w-full bg-jarvis-bg border border-jarvis-border/30 rounded-lg pl-8 pr-3 py-2 text-xs font-mono text-jarvis-text-bright placeholder-jarvis-text-dim/40 focus:outline-none focus:border-jarvis-cyan/40"
                    autoFocus
                  />
                </div>
                <button
                  onClick={() => { setShowSearch(false); setSearchQuery(''); }}
                  className="p-1.5 rounded-lg text-jarvis-text-dim/50 hover:text-jarvis-text-dim transition-all"
                >
                  <X size={14} />
                </button>
              </div>
              {searchResults && searchResults.results.length > 0 && (
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {searchResults.results.map((r, i) => (
                    <div key={i} className="p-2 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                      <p className="text-[11px] font-mono text-jarvis-text-bright truncate">{r.title}</p>
                      <p className="text-[9px] font-mono text-jarvis-text-dim/50 line-clamp-1">{r.snippet}</p>
                    </div>
                  ))}
                </div>
              )}
              {searchQuery.length > 0 && searchResults?.results.length === 0 && (
                <p className="text-[10px] font-mono text-jarvis-text-dim/40">No results found</p>
              )}
            </div>
          </m.div>
        )}
      </AnimatePresence>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-1 scrollbar-thin">
        {messages.length === 0 ? (
          <EmptyState onSend={sendMessage} />
        ) : (
          <m.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            {messages.map((msg, i) => (
              <m.div
                key={msg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: i === messages.length - 1 ? 0 : 0 }}
              >
                <MessageBubble message={msg} />
              </m.div>
            ))}
          </m.div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}

function EmptyState({ onSend }: { onSend: (msg: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-8 py-12">
      <m.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="jarvis-panel-glow p-8 text-center max-w-sm"
      >
        {/* JARVIS avatar */}
        <m.div
          className="w-16 h-16 mx-auto mb-5 flex items-center justify-center rounded-2xl bg-gradient-to-br from-jarvis-cyan/20 to-jarvis-blue/10 border border-jarvis-cyan/30"
          animate={{ boxShadow: [
            '0 0 20px rgba(0,212,255,0.1)',
            '0 0 40px rgba(0,212,255,0.2)',
            '0 0 20px rgba(0,212,255,0.1)',
          ]}}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        >
          <span className="text-jarvis-cyan text-3xl font-bold neon-cyan">J</span>
        </m.div>
        <p className="text-jarvis-text-bright text-sm font-mono mb-1 tracking-wide">
          J.A.R.V.I.S. Online
        </p>
        <p className="text-jarvis-text-dim/60 text-xs font-mono leading-relaxed">
          Ask me anything. I can reason, code, search, and remember.
        </p>
        <span className="jarvis-cursor mt-2" />
      </m.div>

      {/* Suggestion pills */}
      <m.div
        className="grid grid-cols-2 gap-2 w-full max-w-sm"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.3 }}
      >
        {SUGGESTIONS.map((s, i) => (
          <m.button
            key={s}
            onClick={() => onSend(s)}
            className="jarvis-panel px-3 py-2.5 text-xs font-mono text-jarvis-text-dim text-center rounded-xl cursor-pointer hover:text-jarvis-cyan hover:border-jarvis-cyan/30 transition-all duration-200"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + i * 0.1, duration: 0.3 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {s}
          </m.button>
        ))}
      </m.div>
    </div>
  );
}

const SUGGESTIONS = [
  'What can you do?',
  'Show GPU status',
  'Write a Python script',
  'Search the web',
];
